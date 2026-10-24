from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import numpy as np
import cv2
from .omr_service import extract_answers, compare_answers

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend de OMR funcionando correctamente ✅"}

@app.post("/grade")
async def grade(teacher: UploadFile = File(...), student: UploadFile = File(...)):
    teacher_bytes = np.frombuffer(await teacher.read(), np.uint8)
    student_bytes = np.frombuffer(await student.read(), np.uint8)

    teacher_img = cv2.imdecode(teacher_bytes, cv2.IMREAD_COLOR)
    student_img = cv2.imdecode(student_bytes, cv2.IMREAD_COLOR)

    teacher_ans = extract_answers(teacher_img, save_tag="profesor")
    student_ans = extract_answers(student_img, save_tag="alumno")

    result = compare_answers(teacher_ans, student_ans)
    return JSONResponse(result)