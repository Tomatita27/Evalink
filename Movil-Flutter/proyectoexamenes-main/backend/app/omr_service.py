# ============================================================
# omr_service.py (versión calibrada para tu hoja OMR)
# ============================================================

import cv2
import numpy as np
import os
from typing import List, Dict, Tuple, Optional

TARGET_W, TARGET_H = 1000, 1400
COLUMNS = 3
QUESTIONS_PER_COLUMN = 20
CHOICES_PER_QUESTION = 4  # A-D

ADAPTIVE_BLOCK_SIZE = 21
ADAPTIVE_C = 10

DEBUG_SAVE = False
DEBUG_DIR = "debug_omr"

def _ensure_debug_dir():
    if DEBUG_SAVE and not os.path.exists(DEBUG_DIR):
        os.makedirs(DEBUG_DIR, exist_ok=True)

def _preprocess(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    th = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C
    )
    return th

def _order_corners(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect = np.zeros((4,2), dtype=np.float32)
    rect[0] = pts[np.argmin(s)]       # TL
    rect[2] = pts[np.argmax(s)]       # BR
    rect[1] = pts[np.argmin(diff)]    # TR
    rect[3] = pts[np.argmax(diff)]    # BL
    return rect

def _warp_to_standard(img_bgr: np.ndarray, th_bin: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    cnts, _ = cv2.findContours(th_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return (cv2.resize(img_bgr, (TARGET_W, TARGET_H)),
                cv2.resize(th_bin, (TARGET_W, TARGET_H)))
    cnt = max(cnts, key=cv2.contourArea)
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    if len(approx) == 4:
        pts = approx.reshape(4,2).astype(np.float32)
        rect = _order_corners(pts)
        dst = np.array([[0,0],[TARGET_W-1,0],[TARGET_W-1,TARGET_H-1],[0,TARGET_H-1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(rect, dst)
        img_w = cv2.warpPerspective(img_bgr, M, (TARGET_W, TARGET_H))
        th_w = cv2.warpPerspective(th_bin, M, (TARGET_W, TARGET_H))
        return img_w, th_w
    else:
        return (cv2.resize(img_bgr, (TARGET_W, TARGET_H)),
                cv2.resize(th_bin, (TARGET_W, TARGET_H)))

def _split_columns(th_bin: np.ndarray, ncols: int = COLUMNS) -> List[np.ndarray]:
    h, w = th_bin.shape
    col_w = w // ncols
    return [th_bin[:, i*col_w:(i+1)*col_w] for i in range(ncols)]

def _density_in_roi(img_bin: np.ndarray, cx: float, cy: float, w: float, h: float) -> float:
    w = int(max(8, w)); h = int(max(8, h))
    x0, x1 = int(cx - w/2), int(cx + w/2)
    y0, y1 = int(cy - h/2), int(cy + h/2)
    H, W = img_bin.shape
    x0, x1 = max(0,x0), min(W, x1)
    y0, y1 = max(0,y0), min(H, y1)
    roi = img_bin[y0:y1, x0:x1]
    if roi.size == 0: return 0
    return np.count_nonzero(roi) / roi.size

def extract_answers(img_bgr: np.ndarray,
                    choices_per_q: int = CHOICES_PER_QUESTION,
                    save_tag: Optional[str] = None) -> List[int]:

    _ensure_debug_dir()

    th0 = _preprocess(img_bgr)
    img_w, th_w = _warp_to_standard(img_bgr, th0)

    if DEBUG_SAVE and save_tag:
        cv2.imwrite(os.path.join(DEBUG_DIR, f"{save_tag}_warped_bin.jpg"), th_w)

    cols = _split_columns(th_w, COLUMNS)
    answers: List[int] = []

    # calibración horizontal (A,B,C,D) relativa al ancho de columna
    # ajustado manualmente según tus hojas (valores proporcionales 0-1)
    x_ratios = [0.15, 0.37, 0.60, 0.83]  # <-- más real según separación visual

    for ci, col_bin in enumerate(cols):
        h, w = col_bin.shape
        row_height = h / QUESTIONS_PER_COLUMN
        roi_w = w * 0.12  # ancho relativo
        roi_h = row_height * 0.6

        for i in range(QUESTIONS_PER_COLUMN):
            cy = (i + 0.5) * row_height
            densities = []
            for xr in x_ratios:
                cx = w * xr
                dens = _density_in_roi(col_bin, cx, cy, roi_w, roi_h)
                densities.append(dens)
            answers.append(int(np.argmax(densities)))

    # asegurar 60
    total_expected = COLUMNS * QUESTIONS_PER_COLUMN
    if len(answers) > total_expected:
        answers = answers[:total_expected]
    elif len(answers) < total_expected:
        answers.extend([0] * (total_expected - len(answers)))

    return answers

def compare_answers(teacher: List[int], student: List[int]) -> Dict:
    n = min(len(teacher), len(student))
    choices_map = "ABCD"
    correct = 0
    detail = []
    for i in range(n):
        ok = (teacher[i] == student[i])
        correct += 1 if ok else 0
        detail.append({
            "pregunta": i+1,
            "correcta": choices_map[teacher[i]] if teacher[i] < len(choices_map) else "?",
            "alumno": choices_map[student[i]] if student[i] < len(choices_map) else "?",
            "acierto": ok
        })
    return {
        "total": n,
        "aciertos": correct,
        "porcentaje": round(100.0 * correct / max(n,1), 2),
        "detalle": detail
    }