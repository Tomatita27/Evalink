"""
Mejoras a futuro:
- Que todos los procesos sean flexibles (no dependientes en valores fijos)
    - Recortes
    - Máscaras (el open en procesar bolitas)
    - Etc.

"""

import tkinter as tk 
from tkinter import filedialog, Label
from PIL import Image, ImageTk
import cv2
import numpy as np
import os

path_referencia = None
path_evaluar = None
img_referencia = None
img_evaluar = None

# Función para verificar si hay imágenes en ambos canvas
def verificar_imagenes():
    if hasattr(canvas_referencia, 'image') and hasattr(canvas_evaluar, 'image'):
        boton_evaluar.grid(row=0, column=0, padx=10)  # Mostrar botón Evaluar
        boton_borrar.grid(row=1, column=0, padx=10)   # Mostrar botón Borrar
    else:
        boton_evaluar.grid_remove()  # Ocultar botón Evaluar
        boton_borrar.grid_remove()   # Ocultar botón Borrar

# Selección de imágenes
def seleccionar_imagen(canvas_widget, tipo_examen):
    global path_referencia, path_evaluar, img_referencia, img_evaluar, debug
    debug = False

    ruta_archivo = filedialog.askopenfilename(
        title="Seleccionar " + tipo_examen,
        filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp")],
        initialdir="Examenes"
    )

    if ruta_archivo:
        try:
            # Leer imagen con OpenCV y ajustar perspectiva
            img_cv = cv2.imread(ruta_archivo)
            imagen_perspectiva = ajustar_perspectiva(img_cv, ruta_archivo, debug)

            # Convertir de BGR a RGB para tkinter
            imagen_rgb = cv2.cvtColor(imagen_perspectiva, cv2.COLOR_BGR2RGB)
            imagen_pil = Image.fromarray(imagen_rgb)
            imagen_pil = imagen_pil.resize((300, 450))
            img_tk = ImageTk.PhotoImage(imagen_pil)

            # Mostrar en el canvas
            canvas_widget.delete("all")
            canvas_widget.image = img_tk
            canvas_widget.create_image(0, 0, anchor=tk.NW, image=img_tk)

            # Guardar referencia
            archivofoto = os.path.splitext(os.path.basename(ruta_archivo))[0]
            if canvas_widget == canvas_referencia:
                label_referencia.config(text=archivofoto)
                img_referencia = img_cv
            elif canvas_widget == canvas_evaluar:
                label_evaluar.config(text=archivofoto)
                img_evaluar = img_cv

            verificar_imagenes()

        except Exception as e:
            print(f"Error al cargar la imagen: {e}")

# Función para borrar las imágenes
def borrar_imagenes():
    canvas_referencia.delete("all")
    if hasattr(canvas_referencia, 'image'):
        del canvas_referencia.image

    canvas_evaluar.delete("all")
    if hasattr(canvas_evaluar, 'image'):
        del canvas_evaluar.image

    label_aciertos.config(text="Aciertos: -/60")
    label_calificacion.config(text="Calificación: -%")

    label_referencia.config(text="Examen de Referencia")
    label_evaluar.config(text="Examen a Evaluar")

    # Reiniciar los labels de respuestas identificadas
    for j in range(3):  # 3 columnas
        for i in range(20):  # 20 preguntas
            labels_identificados[j][i].config(text=f"{i+1}-", fg="black")

    verificar_imagenes()

# --- Procesamiento de imágenes ---
def ajustar_perspectiva_antigua(imagen, ruta_imagen):
    def ordenar_puntos(puntos):
        puntos = puntos.reshape(4, 2)
        suma = puntos.sum(axis=1)
        resta = np.diff(puntos, axis=1)

        ordenados = np.zeros((4, 2), dtype="float32")
        ordenados[0] = puntos[np.argmin(suma)]     # arriba-izquierda
        ordenados[2] = puntos[np.argmax(suma)]     # abajo-derecha
        ordenados[1] = puntos[np.argmin(resta)]    # arriba-derecha
        ordenados[3] = puntos[np.argmax(resta)]    # abajo-izquierda
        return ordenados
    
    # Preprocesamiento más robusto
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    masksize = int(imagen.shape[1] / 150) | 1
    gris = cv2.GaussianBlur(gris,(masksize, masksize), 0) # Suavizado
    gridsize = int(imagen.shape[1]/30)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(gridsize, gridsize))
    gris = clahe.apply(gris)

    # Umbral adaptativo (mejor para iluminación irregular)
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, masksize, 12)

    canny = cv2.Canny(gris, 50, 100)
    bincanny = cv2.bitwise_or(binaria, canny)

    # Detección de contornos
    contornos, _ = cv2.findContours(bincanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)

    encontrado = False
    for c in contornos:
        area = cv2.contourArea(c)
        if area < int(imagen.shape[0]*imagen.shape[1] / 30):  # No tomar contornos pequeños
            continue

        perimetro = cv2.arcLength(c, True)
        aproximado = cv2.approxPolyDP(c, 0.02 * perimetro, True)

        if len(aproximado) == 4:
            puntos = ordenar_puntos(aproximado)
            encontrado = True
            break
    
    if encontrado:
        alto = 1333
        ancho = int(imagen.shape[1] * (1333 / imagen.shape[0]))
        
        destino = np.float32([[0, 0], [ancho, 0], [ancho, alto], [0, alto]])
        M = cv2.getPerspectiveTransform(puntos, destino)
        dst = cv2.warpPerspective(imagen, M, (ancho,alto))

        if debug:
            cv2.imshow("img perspectiva - " + str(ruta_imagen), cv2.resize(dst, (500, 750)))
            cv2.moveWindow("img perspectiva- " + str(ruta_imagen), 0, 0)         # Arriba-izquierda

        return dst

    print(f"No se encontró una forma con 4 lados.")
    return None

def ajustar_perspectiva_nueva(imagen, ruta_imagen, debug):
    # Redimensionar (ancho fijo = 1000 px)
    scale = 1000 / imagen.shape[1]
    imagen_resized = cv2.resize(imagen, (1000, int(imagen.shape[0] * scale)))
    
    # Preprocesamiento más robusto
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

    masksize = int(imagen.shape[1] / 100) | 1
    gris = cv2.GaussianBlur(gris,(masksize, masksize), 0) # Suavizado
    gridsize = int(imagen.shape[1]/30)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(gridsize, gridsize))
    gris = clahe.apply(gris)

    # Umbral adaptativo (mejor para iluminación irregular)
    binaria = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, masksize, 12)
    canny = cv2.Canny(gris, 50, 100)
    bincanny = cv2.bitwise_or(binaria, canny)
    
    # Buscar contornos externos
    contornos, _ = cv2.findContours(bincanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        # Segundo intento (Mecanísmo de Proa):
        gray = cv2.cvtColor(imagen_resized, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0) # Escala de grises y suavizado

        thresh = cv2.adaptiveThreshold( # Umbral para detectar la hoja completa
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5) 
        
        contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            print("No se encontraron contornos.")

            if debug:
                print("ERROR: " + str(ruta_imagen))
                cv2.imshow("img - " + str(ruta_imagen), cv2.resize(imagen, (500, 750)))
                cv2.imshow("gris - " + str(ruta_imagen), cv2.resize(gris, (500, 750)))
                cv2.imshow("binaria - " + str(ruta_imagen), cv2.resize(binaria, (500, 750)))
                cv2.imshow("canny - " + str(ruta_imagen), cv2.resize(canny, (500, 750)))
                cv2.imshow("bincanny - " + str(ruta_imagen), cv2.resize(bincanny, (500, 750)))
                cv2.imshow("gray - " + str(ruta_imagen), cv2.resize(gray, (500, 750)))
                cv2.imshow("thresh - " + str(ruta_imagen), cv2.resize(thresh, (500, 750)))
            
            return None

    # Ordenar por área
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)

    def ordenar_puntos(pts):
        pts = pts.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # sup izq
        rect[2] = pts[np.argmax(s)]  # inf der

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # sup der
        rect[3] = pts[np.argmax(diff)]  # inf izq

        return rect

    for c in contornos:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:  # Encontramos hoja
            rect = ordenar_puntos(approx)
            (tl, tr, br, bl) = rect

            # Tamaño destino
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            maxWidth = max(int(widthA), int(widthB))

            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)
            maxHeight = max(int(heightA), int(heightB))

            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            perspectiva = cv2.warpPerspective(imagen, M, (maxWidth, maxHeight))

            if debug:
                cv2.drawContours(imagen, [approx.astype(int)], -1, (0, 255, 0), 3)
                cv2.imshow("img - " + str(ruta_imagen), cv2.resize(imagen, (500, 750)))
                cv2.moveWindow("img - " + str(ruta_imagen), 0, 0)         # Arriba-izquierda

            return perspectiva
        else:
            return None

def ajustar_perspectiva(imagen, ruta_imagen, debug):
    perspectiva = ajustar_perspectiva_nueva(imagen, ruta_imagen, debug)
    if perspectiva is None:
        perspectiva = ajustar_perspectiva_antigua(imagen, ruta_imagen)
        if perspectiva is None:
            return None
    return perspectiva

def procesar_bolitas(perspectiva, ruta_imagen, debug):
    # Recortar margen superior
    perspectiva = perspectiva[int(perspectiva.shape[0]*0.07):, :] # Recortar 7% del tamaño para eliminar títulos
    perspectiva = cv2.resize(perspectiva, (500, 700))  # ancho=500, alto=700

    # Escala de grises + CLAHE + Otsu
    bin = cv2.cvtColor(perspectiva, cv2.COLOR_BGR2GRAY)
    gridsize = int(bin.shape[1]/30)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(gridsize, gridsize))
    bin = clahe.apply(bin)
    _, bin = cv2.threshold(bin, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Operaciones Morfológicas
    kernel_close = np.ones((2, 2), np.uint8) 
    morph = cv2.morphologyEx(bin, cv2.MORPH_CLOSE, kernel_close)
    kernel_open = np.ones((3, 3), np.uint8) 
    morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_open)
    
    def limpiado_contornos(hoja, valor_min):
        # Buscar contornos (posibles burbujas)
        contornos, _ = cv2.findContours(hoja, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Imagen salida (solo bolitas rellenas)
        hoja_bolitas = np.zeros_like(hoja)

        for c in contornos:
            area = cv2.contourArea(c)
            if valor_min < area < 1200:  # rango del área de burbujas
                x, y, w, h = cv2.boundingRect(c)
                roi = hoja[y:y+h, x:x+w]

                # % de pixeles blancos dentro de la burbuja
                filled_ratio = cv2.countNonZero(roi) / (w * h)

                # Si está suficientemente rellena es respuesta
                if filled_ratio > 0.5: 
                    cv2.drawContours(hoja_bolitas, [c], -1, 255, -1)

        kernel_dilatacion = np.ones((5,5))
        cv2.dilate(hoja_bolitas, kernel_dilatacion)
        return hoja_bolitas
    
    # Bolitas
    bolitas = limpiado_contornos(morph, 100)
    kernel_close1 = np.ones((5, 5), np.uint8)
    bolitas = cv2.morphologyEx(bolitas, cv2.MORPH_CLOSE, kernel_close1)
    kernel_dilatacion1 = np.ones((13, 13), np.uint8)
    bolitas = cv2.dilate(bolitas, kernel_dilatacion1)

    # Ajustadora:
    kernel_close2 = np.ones((7, 7), np.uint8)
    ajustadora = cv2.morphologyEx(bin, cv2.MORPH_CLOSE, kernel_close2)

    if debug:
        #cv2.imshow("bin - " + str(ruta_imagen), cv2.resize(bin, (500, 750)))
        #cv2.imshow("morph - " + str(ruta_imagen), cv2.resize(bin, (500, 750)))
        cv2.imshow("bol - " + str(ruta_imagen), cv2.resize(bolitas, (500, 750)))
        cv2.moveWindow("bol - " + str(ruta_imagen), 500, 0)
        cv2.imshow("ajustadora - " + str(ruta_imagen), cv2.resize(ajustadora, (500, 750)))
        cv2.moveWindow("ajustadora - " + str(ruta_imagen), 1000, 0)

    return bolitas, ajustadora

def identificar_respuestas(bolitas, ajustadora, ruta_imagen, debug):
    y_coord_1 = 16
    y_coord_20 = 670

    # 6 coordenadas base (A1 y D20 en cada columna)
    A1_col1, D20_col1 = (58, y_coord_1), (140, y_coord_20)
    A1_col2, D20_col2 = (231, y_coord_1), (311, y_coord_20)
    A1_col3, D20_col3 = (393, y_coord_1), (478, y_coord_20)

    columnas = [
        ("col1", A1_col1, D20_col1),
        ("col2", A1_col2, D20_col2),
        ("col3", A1_col3, D20_col3)
    ]

    todas_coord = {}

    # --- Ajustar automáticamente las 6 coordenadas iniciales ---
    def encontrar_bolita_cercana(ajustadora, x, y, x_default, y_default, ventana=20):
        # Busca una bolita cerca de (x,y). Si no encuentra, regresa la coordenada default original.
        h, w = ajustadora.shape
        x1, y1 = max(0, x-ventana), max(0, y-ventana)
        x2, y2 = min(w, x+ventana), min(h, y+ventana)

        roi = ajustadora[y1:y2, x1:x2]
        contornos, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contornos:
            # Tomar el contorno más grande dentro del área
            c = max(contornos, key=cv2.contourArea)
            area = cv2.contourArea(c)

            # Filtrar ruido: descartar contornos demasiado chicos o grandes
            if 20 < area < 2000:
                # Usar el círculo mínimo que encierra el contorno
                (cx, cy), radio = cv2.minEnclosingCircle(c)
                return (int(cx) + x1, int(cy) + y1)

        # Si no encontró nada válido -> usa la coordenada default
        return (x_default, y_default)

    coords_ajustadas = []
    for nombre_col, A1, D20 in columnas:
        A1_ajustada = encontrar_bolita_cercana(ajustadora, *A1, *A1)   # pasa también los defaults
        D20_ajustada = encontrar_bolita_cercana(ajustadora, *D20, *D20)
        coords_ajustadas.append((nombre_col, A1_ajustada, D20_ajustada))

    # --- Generar el resto de puntos ---
    for nombre_col, (xa, ya), (xd, yd) in coords_ajustadas:
        ancho_col = xd - xa
        step_x = ancho_col / 3
        xA, xB, xC, xD = int(xa), int(xa + step_x), int(xa + 2*step_x), int(xd)

        y_vals = np.linspace(ya, yd, 20, dtype=int)

        todas_coord[f"a_{nombre_col}"] = [(int(xA), y) for y in y_vals]
        todas_coord[f"b_{nombre_col}"] = [(int(xB), y) for y in y_vals]
        todas_coord[f"c_{nombre_col}"] = [(int(xC), y) for y in y_vals]
        todas_coord[f"d_{nombre_col}"] = [(int(xD), y) for y in y_vals]

    respuestas = np.empty((3, 20), dtype=object)

    # Recorremos por columnas
    for j, nombre_col in enumerate(["col1", "col2", "col3"]):
        # Sacar las 20 coordenadas para cada opción
        coords_A = todas_coord[f"a_{nombre_col}"]
        coords_B = todas_coord[f"b_{nombre_col}"]
        coords_C = todas_coord[f"c_{nombre_col}"]
        coords_D = todas_coord[f"d_{nombre_col}"]

        # Recorremos las 20 preguntas
        for i in range(20):
            marcadas = []
            opciones = {"A": coords_A[i], "B": coords_B[i],
                        "C": coords_C[i], "D": coords_D[i]}

            for letra, (x, y) in opciones.items():
                # Revisar si ese píxel tiene tinta (no es negro)
                if bolitas[y, x] != 0:
                    marcadas.append(letra)

            # Guardar la respuesta
            if len(marcadas) == 1:
                respuestas[j, i] = marcadas[0]
            else:
                respuestas[j, i] = ""

    if debug:
        bolitas_color = cv2.cvtColor(bolitas, cv2.COLOR_GRAY2BGR)

        for nombre_col, lista in todas_coord.items():
            for i, (x, y_val) in enumerate(lista):
                valor = bolitas[y_val, x]
                if valor != 0:
                    cv2.circle(bolitas_color, (x, y_val), 4, (0, 150, 0), -1)
                    print(f"{nombre_col}[{i+1}] -> Pixel en ({x},{y_val}) = 1")
                else:
                    cv2.circle(bolitas_color, (x, y_val), 4, (0, 0, 150), -1)

        cv2.imshow("bolitas_color - " + str(ruta_imagen), cv2.resize(bolitas_color, (500, 750)))
        cv2.moveWindow("bolitas_color - " + str(ruta_imagen), 1000, 0)
    
    return respuestas

def procesar_todo(examen, ruta_examen): # Pipeline de procesamiento
    if debug:
        print(ruta_examen)

    perspectiva = ajustar_perspectiva(examen, ruta_examen, debug)
    if perspectiva is not None:
        bolitas, ajustadora = procesar_bolitas(perspectiva, ruta_examen, debug)
        respuestas = identificar_respuestas(bolitas, ajustadora, ruta_examen, debug)
    return respuestas

# --- Evaluación ---
def evaluar():
    res_ref = procesar_todo(img_referencia, path_referencia)
    res_eva = procesar_todo(img_evaluar, path_evaluar)
    
    for j in range(3):  # para cada sección
        for i in range(20):  # para cada pregunta
            respuesta_ref = res_ref[j][i]
            respuesta_eva = res_eva[j][i]

            texto = f"{i+1}- {respuesta_eva}"

            if respuesta_eva not in {'A', 'B', 'C', 'D'}:
                color = "#A1A1A1"  # No marcada o inválida
            elif respuesta_eva == respuesta_ref:
                color = "#175200"  # Correcta
            else:
                color = "#FF4F4F"  # Incorrecta

            labels_identificados[j][i].config(text=texto, fg=color)

    def comp_resp(ref_s, eva_s):
        aciertos = 0
        for i in range(20):
            resp_ref = str(ref_s[i])
            resp_eva = str(eva_s[i])
            
            if resp_ref in {'A', 'B', 'C', 'D'} and resp_eva in {'A', 'B', 'C', 'D'} and resp_ref == resp_eva:
                aciertos += 1

        return aciertos

    ref_s1 = res_ref[:][0]
    ref_s2 = res_ref[:][1]
    ref_s3 = res_ref[:][2]
    eva_s1 = res_eva[:][0]
    eva_s2 = res_eva[:][1]
    eva_s3 = res_eva[:][2]

    aciertos_s1 = comp_resp(ref_s1, eva_s1)
    aciertos_s2 = comp_resp(ref_s2, eva_s2)
    aciertos_s3 = comp_resp(ref_s3, eva_s3)

    aciertos = aciertos_s1 + aciertos_s2 + aciertos_s3
    calificacion = aciertos / 60 * 100

    aciertos_text = "Aciertos: " + str(aciertos) + "/60"
    calificacion_text = "Calificación: " + str(round(calificacion,1)) + "%"

    label_aciertos.config(text=aciertos_text)
    label_calificacion.config(text=calificacion_text)

    return aciertos, ref_s1, ref_s2, ref_s3, eva_s1, eva_s2, eva_s3

# --- GUI ---
# Ventana principal
root = tk.Tk()
root.title("Evaluador Automático de Hoja de Respuestas de Exámenes")
root.geometry("1050x770")

# Título en la parte superior
titulo = tk.Label(root, text="Evalink",
                  font=("Arial", 24, "bold", "italic"), fg="#0f3257")
titulo.pack(pady=20)

# Frame para centrar para las imágenes o inputs
frame_central = tk.Frame(root)
frame_central.pack(pady=5, anchor="center")

# Etiquetas debajo de los recuadros
label_referencia = Label(frame_central, text="Examen de Referencia", font=("Arial", 14, "italic"))
label_referencia.grid(row=0, column=0)

label_evaluar = Label(frame_central, text="Examen a Evaluar", font=("Arial", 14, "italic"))
label_evaluar.grid(row=0, column=1)

# Frame para  el examen referencia
frame_examen_ref = tk.Frame(frame_central)
frame_examen_ref.grid(row=1, column=0, pady=20, padx=30)

# Canvas para el examen referencia
canvas_referencia = tk.Canvas(frame_examen_ref, width=300, height=450, bg="gray")
canvas_referencia.grid(row=0)

# Botón para seleccionar examen referencia
boton_examenref = tk.Button(frame_examen_ref, text="Seleccionar referencia", bg="#87ceeb",
                            command=lambda: seleccionar_imagen(canvas_referencia, "Examen de Referencia"),
                            font=("Arial", 13, "bold"), width=20)
boton_examenref.grid(row=1, pady=20)

# Frame para  el examen a evaluar
frame_examen_eva = tk.Frame(frame_central)
frame_examen_eva.grid(row=1, column=1, pady=20, padx=40)

# Canvas para el examen a evaluar
canvas_evaluar = tk.Canvas(frame_examen_eva, width=300, height=450, bg="gray")
canvas_evaluar.grid(row=0)

# Botón para seleccionar examen a evaluar
boton_exameneva = tk.Button(frame_examen_eva, text="Examen a Evaluar", bg="#ffb368",
                            command=lambda: seleccionar_imagen(canvas_evaluar, "Examen a Evaluar"),
                            font=("Arial", 13, "bold"), width=20)
boton_exameneva.grid(row=1, pady=20)

# Frame para mostrar respuestas identificadas
frame_resultados = tk.Frame(frame_central)
frame_resultados.grid(row=1, column=2)
label_resultados = tk.Label(frame_central, text="Evaluación del Examen", font=("Arial", 14, "italic"))
label_resultados.grid(row=0, column=2)

# Crear subframes por sección
labels_identificados = [[], [], []]  # Tres listas para guardar los labels

for j in range(3):
    subframe = tk.Frame(frame_resultados)
    subframe.pack(side="left", padx=10)
    
    for i in range(1, 21):
        lbl = tk.Label(subframe, text=f"{i}- ", font=("Arial", 13, "bold"))
        lbl.pack(anchor="w")
        labels_identificados[j].append(lbl)

# Frame para aciertos, calificación y botones en la misma fila
frame_abajo = tk.Frame(frame_central)
frame_abajo.grid(row=2, column=1)

# Botón Evaluar
boton_evaluar = tk.Button(frame_abajo, text="Evaluar", command=evaluar, bg="#0cc945", fg="white", width=10, height=1, font=("Arial", 13, "bold"))
boton_evaluar.grid(row=0, column=0, padx=10)
boton_evaluar.grid_remove()  # Ocultar inicialmente

# Botón Borrar
boton_borrar = tk.Button(frame_abajo, text="Borrar", command=borrar_imagenes, bg="#c90c0c", fg="white", width=10, height=1, font=("Arial", 13, "bold"))
boton_borrar.grid(row=1, column=0, padx=10)
boton_borrar.grid_remove()  # Ocultar inicialmente

# Etiqueta Aciertos
label_aciertos = tk.Label(frame_abajo, text="Aciertos: -/60", font=("Arial", 14))
label_aciertos.grid(row=0, column=1, padx=10)

# Etiqueta Calificación
label_calificacion = tk.Label(frame_abajo, text="Calificación: -%", font=("Arial", 14))
label_calificacion.grid(row=1, column=1, padx=10)

root.mainloop()