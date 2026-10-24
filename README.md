# Evalink
Proyecto para innovatec, de evaluación automática de exámenes de opción múltiple

Evalink es un sistema de evaluación de exámenes de opción múltiple a partir de fotografías o imágenes de hojas de respuestas. Compara las respuestas detectadas en un examen con una hoja de referencia y presenta los aciertos y la calificación.

El repositorio contiene dos implementaciones: una aplicación de escritorio y una aplicación móvil conectada a un servicio de procesamiento.

Tecnologías:
Escritorio: Python y librerías Tkinter, OpenCV, NumPy.
Aplicación móvil: Flutter y Dart.

Funcionalidades
- Selección de una hoja de referencia y una hoja de respuestas para evaluar.
- Procesamiento de imágenes para identificar las respuestas marcadas.
- Comparación de respuestas y cálculo de aciertos y porcentaje de calificación.
- Interfaz de escritorio para visualizar resultados.
- Interfaz móvil para capturar o seleccionar imágenes y enviarlas al servicio de evaluación.
Alcance: Las implementaciones compartidas están adaptadas a hojas de 60 preguntas (3 columnas de 20), con opciones A, B, C y D. La calidad del reconocimiento depende de la imagen y del formato del examen.

Ejecución de la aplicación de escritorio

Desde la raíz del repositorio, en PowerShell:
cd Escritorio_Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install opencv-python numpy pillow
python Innovatec_RegionalV2.py
Si PowerShell impide activar el entorno virtual, puedes ejecutar directamente .\.venv\Scripts\python.exe -m pip install opencv-python numpy pillow y .\.venv\Scripts\python.exe Innovatec_RegionalV2.py sin activarlo.

Tkinter normalmente se incluye con la instalación estándar de Python para Windows. Para evaluar, selecciona la imagen de referencia, selecciona la del examen y presiona Evaluar. Las imágenes de ejemplo están en ../Examenes/ desde esta carpeta; puedes localizarlas con el selector de archivos.

Ejecución de la aplicación móvil
Opción A: ejecutar Flutter con el backend configurado
Requisitos: Flutter instalado, Android Studio o un dispositivo Android configurado.
cd Movil-Flutter\proyectoexamenes-main\frontend
flutter doctor
flutter pub get
flutter run
Selecciona el dispositivo correspondiente cuando Flutter lo solicite. Para calificar exámenes desde la app es necesario que el servidor configurado responda correctamente.
Opción B: ejecutar también el backend de manera local
Abre una terminal en la raíz del repositorio:
cd Movil-Flutter\proyectoexamenes-main\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
En el navegador de la computadora, comprueba la API en http://127.0.0.1:8000/docs.

Para conectar Flutter al backend local, cambia temporalmente la URL de getBaseUrl() en frontend/lib/services/api_service.dart:
- Emulador Android: http://10.0.2.2:8000.
- Teléfono Android físico: http://IP_LOCAL_DE_TU_PC:8000, con el teléfono y la PC en la misma red.

Luego, desde otra terminal:
cd Movil-Flutter\proyectoexamenes-main\frontend
flutter pub get
flutter run
La API expone GET / para comprobación básica y POST /grade para enviar imágenes en los campos teacher y student.

