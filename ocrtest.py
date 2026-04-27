import cv2
import numpy as np
import pytesseract
import csv
import time
import re
import os
from datetime import datetime
from collections import deque

# ── Windows: descomenta y ajusta tu ruta ──────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────
CAMARA_INDEX    = 1
CSV_ARCHIVO     = "lecturas.csv"
INTERVALO_PRINT = 10
INTERVALO_OCR   = 0.3       # más frecuente para alimentar mejor el estabilizador

# ROI — ampliada para no cortar dígitos en los bordes
roi_x     = 80
roi_y     = 80
roi_ancho = 500
roi_alto  = 220

# ─────────────────────────────────────────────────────────────
# ESTABILIZADOR POR VOTACIÓN
# ─────────────────────────────────────────────────────────────
class Estabilizador:
    """Devuelve el valor más frecuente en las últimas N lecturas."""
    def __init__(self, ventana=7):
        self.buf = deque(maxlen=ventana)

    def agregar(self, valor):
        if valor:
            self.buf.append(valor)

    def mejor_valor(self):
        if not self.buf:
            return ""
        conteo = {}
        for v in self.buf:
            conteo[v] = conteo.get(v, 0) + 1
        return max(conteo, key=conteo.get)

# ─────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────
def inicializar_csv(archivo):
    existe = os.path.isfile(archivo)
    with open(archivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["timestamp", "valor"])
    print(f"📄 CSV listo: {archivo}")

def guardar_csv(archivo, valor):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(archivo, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, valor])

# ─────────────────────────────────────────────────────────────
# ① PREPROCESAMIENTO
# ─────────────────────────────────────────────────────────────
def preprocesar(roi_bgr):
    gris    = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    grande  = cv2.resize(gris, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    suave   = cv2.bilateralFilter(grande, d=7, sigmaColor=50, sigmaSpace=50)
    _, bin_ = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    limpia  = cv2.morphologyEx(bin_, cv2.MORPH_CLOSE, kernel)
    return limpia

# ─────────────────────────────────────────────────────────────
# ② OCR — psm 6 (más tolerante que psm 7)
# ─────────────────────────────────────────────────────────────
def leer_digitos(img_pre):
    config      = r'--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789'
    texto       = pytesseract.image_to_string(img_pre, config=config)
    solo_digitos = re.sub(r"\D+", "", texto)
    return solo_digitos

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    inicializar_csv(CSV_ARCHIVO)

    camara = cv2.VideoCapture(CAMARA_INDEX,cv2.CAP_DSHOW)  # CAP_DSHOW recomendado en Windows para evitar retrasos
    if not camara.isOpened():
        print("❌ No se pudo abrir la cámara")
        return

    print("✅ Cámara abierta. Presiona 'q' para salir.")
    print(f"📊 Imprimiendo en terminal cada {INTERVALO_PRINT}s\n")

    estabilizador = Estabilizador(ventana=7)
    ultimo_ocr    = 0
    ultimo_print  = 0
    ultimo_valor  = ""

    while True:
        ok, frame = camara.read()
        if not ok:
            print("❌ Error leyendo frame")
            break

        # Recuadro ROI
        cv2.rectangle(frame,
                      (roi_x, roi_y),
                      (roi_x + roi_ancho, roi_y + roi_alto),
                      (0, 255, 0), 2)
        cv2.putText(frame, "ZONA MEDIDOR", (roi_x, roi_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        roi_recortada = frame[roi_y : roi_y + roi_alto,
                              roi_x : roi_x + roi_ancho]
        ahora = time.time()

        if ahora - ultimo_ocr >= INTERVALO_OCR:
            ultimo_ocr = ahora

            img_pre = preprocesar(roi_recortada)
            valor   = leer_digitos(img_pre)

            # Alimenta el estabilizador
            estabilizador.agregar(valor)
            valor_estable = estabilizador.mejor_valor()

            # Muestra lectura cruda vs estable en ventana
            cv2.putText(frame, f"Crudo: {valor}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            cv2.putText(frame, f"Estable: {valor_estable}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 100), 2)

            if valor_estable:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if valor_estable != ultimo_valor:
                    guardar_csv(CSV_ARCHIVO, valor_estable)
                    ultimo_valor = valor_estable

                if ahora - ultimo_print >= INTERVALO_PRINT:
                    ultimo_print = ahora
                    print(f"[{ts}]  Lectura estable: {valor_estable}  (crudo: {valor})")

            cv2.imshow("Preprocesada (OCR ve esto)", img_pre)

        cv2.imshow("Webcam", frame)
        cv2.imshow("Zona OCR", roi_recortada)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camara.release()
    cv2.destroyAllWindows()
    print(f"\n👋 Listo. Lecturas en: {CSV_ARCHIVO}")

if __name__ == "__main__":
    main()