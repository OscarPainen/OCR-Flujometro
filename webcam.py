import cv2

camara = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Usa índice 1 para la webcam externa (ajusta si es necesario) // CAP_DSHOW estable en windows

if not camara.isOpened():
    print("❌ No se pudo abrir la cámara")
    exit()

print("✅ Cámara abierta. Presiona 'q' para salir.")

# ─────────────────────────────────────────────
# ① DEFINIR EL RECUADRO (ROI)                 ← NUEVO
# ─────────────────────────────────────────────
# Estas 4 variables definen el rectángulo:
#   x, y       → esquina superior izquierda (en píxeles)
#   ancho, alto → tamaño del recuadro
#
# Empieza con estos valores y los ajustas
# moviendo el medidor frente a la cámara.

roi_x     = 150   # distancia desde el borde izquierdo
roi_y     = 100   # distancia desde el borde superior
roi_ancho = 340   # ancho del recuadro
roi_alto  = 180   # alto del recuadro

while True:
    ok, frame = camara.read()

    if not ok:
        print("❌ Error leyendo frame")
        break

    # ─────────────────────────────────────────
    # ② DIBUJAR EL RECTÁNGULO sobre el frame  ← NUEVO
    # ─────────────────────────────────────────
    # Parámetros: imagen, esquina_sup_izq, esquina_inf_der, color_BGR, grosor
    cv2.rectangle(
        frame,
        (roi_x, roi_y),                          # esquina superior izquierda
        (roi_x + roi_ancho, roi_y + roi_alto),   # esquina inferior derecha
        (0, 255, 0),                             # color verde (B=0, G=255, R=0)
        2                                        # grosor del borde en píxeles
    )

    # Etiqueta encima del recuadro                ← NUEVO
    cv2.putText(
        frame,
        "ZONA MEDIDOR",           # texto
        (roi_x, roi_y - 10),      # posición (encima del recuadro)
        cv2.FONT_HERSHEY_SIMPLEX, # fuente
        0.6,                      # tamaño
        (0, 255, 0),              # color verde
        2                         # grosor
    )

    # ─────────────────────────────────────────
    # ③ RECORTAR LA ZONA ROI del frame         ← NUEVO
    # ─────────────────────────────────────────
    # Esto extrae solo los píxeles dentro del recuadro.
    # Sintaxis: frame[fila_inicio:fila_fin, col_inicio:col_fin]
    roi_recortada = frame[roi_y : roi_y + roi_alto,
                          roi_x : roi_x + roi_ancho]

    # ─────────────────────────────────────────
    # ④ MOSTRAR LA ROI en ventana separada     ← NUEVO
    # ─────────────────────────────────────────
    # Así ves exactamente qué "ve" el OCR más adelante
    cv2.imshow("Zona OCR", roi_recortada)

    # Ventana principal (igual que Etapa 1)
    cv2.imshow("Webcam", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camara.release()
cv2.destroyAllWindows()
print("👋 Cámara cerrada.")