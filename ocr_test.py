import argparse
import re
import sys
import time
from dataclasses import dataclass
from collections import deque
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import pytesseract
except ImportError as e:
    raise SystemExit("Falta pytesseract. Instala con: pip install pytesseract") from e


@dataclass(frozen=True)
class AppConfig:
    # Fuente de video
    camera_index: int = 0
    rtsp_url: Optional[str] = None

    # OCR / rendimiento
    ocr_every_sec: float = 0.25          # OCR cada 250ms aprox (ajusta según CPU)
    min_tess_conf: int = 40              # 0-100; filtra textos con baja confianza

    # ROI (región de interés) en coordenadas relativas [0..1]
    # (x, y, w, h) relativo al tamaño del frame. None = frame completo.
    roi_rel: Optional[Tuple[float, float, float, float]] = None

    # Preprocesamiento
    upscale: float = 2.0                 # agranda para mejorar OCR de números pequeños
    threshold: str = "otsu"              # "otsu" o "adaptive"

    # Salida
    print_only_on_change: bool = True
    stabilization_window: int = 5        # suaviza lecturas usando últimas N lecturas

    # Debug UI
    show_window: bool = True
    window_name: str = "OCR Digits (press q to quit)"

    # Ruta tesseract (opcional)
    tesseract_cmd: Optional[str] = None


class FrameSource:
    """Fuente de frames escalable: webcam o RTSP (IP cam)."""
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.cap = None

    def open(self):
        src = self.cfg.rtsp_url if self.cfg.rtsp_url else self.cfg.camera_index
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de video: {src}")

        # Sugerencias (no siempre aplican según cámara/driver)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self):
        if self.cap is None:
            self.open()
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("No se pudo leer frame de la cámara.")
        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def crop_roi(frame: np.ndarray, roi_rel: Optional[Tuple[float, float, float, float]]):
    if roi_rel is None:
        return frame, (0, 0, frame.shape[1], frame.shape[0])

    h, w = frame.shape[:2]
    x_rel, y_rel, ww_rel, hh_rel = roi_rel
    x = int(max(0, min(1, x_rel)) * w)
    y = int(max(0, min(1, y_rel)) * h)
    ww = int(max(0, min(1, ww_rel)) * w)
    hh = int(max(0, min(1, hh_rel)) * h)

    # Asegura mínimo válido
    ww = max(1, min(w - x, ww))
    hh = max(1, min(h - y, hh))

    return frame[y:y + hh, x:x + ww], (x, y, ww, hh)


def preprocess_for_digits(img_bgr: np.ndarray, cfg: AppConfig) -> np.ndarray:
    """Preprocesamiento robusto para OCR de dígitos."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    if cfg.upscale and cfg.upscale != 1.0:
        gray = cv2.resize(gray, None, fx=cfg.upscale, fy=cfg.upscale, interpolation=cv2.INTER_CUBIC)

    # Reduce ruido pero mantiene bordes
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    if cfg.threshold == "adaptive":
        thr = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7
        )
    else:
        # Otsu suele ir bien para dígitos con buen contraste
        _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morfología suave para “cerrar” cortes en segmentos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=1)

    return thr


def ocr_digits_tesseract(img_bin: np.ndarray, cfg: AppConfig) -> Tuple[str, int]:
    """
    Devuelve (digits, best_conf).
    - img_bin: imagen binaria (0/255) ideal para Tesseract.
    """
    # psm 7: una sola línea; psm 6: bloque de texto uniforme
    # whitelist limita a dígitos para subir precisión
    custom_config = r'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789'

    data = pytesseract.image_to_data(img_bin, config=custom_config, output_type=pytesseract.Output.DICT)

    best_conf = -1
    pieces = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        conf_str = data["conf"][i]
        try:
            conf = int(float(conf_str))
        except Exception:
            conf = -1

        if conf < cfg.min_tess_conf:
            continue

        # Extrae solo dígitos por seguridad
        digits = re.sub(r"\D+", "", txt)
        if digits:
            pieces.append(digits)
            best_conf = max(best_conf, conf)

    # Une piezas (por si Tesseract separa grupos)
    joined = "".join(pieces)
    return joined, best_conf


class Stabilizer:
    """Suaviza lecturas: elige el valor más frecuente en una ventana reciente."""
    def __init__(self, window: int):
        self.window = max(1, window)
        self.buf = deque(maxlen=self.window)

    def push(self, value: str) -> str:
        self.buf.append(value)
        # modo: valor más común
        counts = {}
        for v in self.buf:
            counts[v] = counts.get(v, 0) + 1
        # desempate: el más reciente
        best = max(counts.items(), key=lambda kv: (kv[1], list(self.buf)[::-1].index(kv[0]) * -1))[0]
        return best


def draw_overlay(frame: np.ndarray, roi_xywh, text: str, conf: int):
    x, y, w, h = roi_xywh
    cv2.rectangle(frame, (x, y), (x + w, y + h), (60, 180, 60), 2)
    label = f"OCR: {text or '-'}  conf:{conf if conf >= 0 else '-'}"
    cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description="OCR de dígitos en tiempo real desde webcam/IP cam (RTSP).")
    ap.add_argument("--camera", type=int, default=0, help="Índice de cámara (default 0).")
    ap.add_argument("--rtsp", type=str, default=None, help="URL RTSP para IP cam (si se usa, ignora --camera).")
    ap.add_argument("--ocr-every", type=float, default=0.25, help="Intervalo OCR en segundos (default 0.25).")
    ap.add_argument("--roi-rel", type=float, nargs=4, default=None,
                    metavar=("X", "Y", "W", "H"),
                    help="ROI relativa [0..1] ej: --roi-rel 0.25 0.35 0.5 0.25")
    ap.add_argument("--threshold", type=str, choices=["otsu", "adaptive"], default="otsu", help="Método de umbral.")
    ap.add_argument("--upscale", type=float, default=2.0, help="Factor de escala para OCR (default 2.0).")
    ap.add_argument("--min-conf", type=int, default=40, help="Conf mínima de Tesseract (default 40).")
    ap.add_argument("--stable", type=int, default=5, help="Ventana de estabilización (default 5).")
    ap.add_argument("--print-all", action="store_true", help="Imprime en cada OCR (no solo cuando cambia).")
    ap.add_argument("--no-show", action="store_true", help="No mostrar ventana (modo servidor/headless).")
    ap.add_argument("--tesseract-cmd", type=str, default=None, help="Ruta al ejecutable de tesseract (Windows).")
    args = ap.parse_args()

    cfg = AppConfig(
        camera_index=args.camera,
        rtsp_url=args.rtsp,
        ocr_every_sec=args.ocr_every,
        roi_rel=tuple(args.roi_rel) if args.roi_rel else None,
        threshold=args.threshold,
        upscale=args.upscale,
        min_tess_conf=args.min_conf,
        stabilization_window=args.stable,
        print_only_on_change=not args.print_all,
        show_window=not args.no_show,
        tesseract_cmd=args.tesseract_cmd,
    )

    if cfg.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = cfg.tesseract_cmd

    src = FrameSource(cfg)
    stabilizer = Stabilizer(cfg.stabilization_window)

    last_printed = None
    last_ocr_time = 0.0
    last_result = ("", -1)

    try:
        src.open()
        while True:
            frame = src.read()

            now = time.time()
            do_ocr = (now - last_ocr_time) >= cfg.ocr_every_sec

            if do_ocr:
                roi_img, roi_xywh = crop_roi(frame, cfg.roi_rel)
                pre = preprocess_for_digits(roi_img, cfg)
                digits, conf = ocr_digits_tesseract(pre, cfg)
                digits_stable = stabilizer.push(digits)

                last_result = (digits_stable, conf)
                last_ocr_time = now

                if (not cfg.print_only_on_change) or (digits_stable != last_printed):
                    # imprime solo números (o '-' si vacío)
                    print(digits_stable if digits_stable else "-")
                    sys.stdout.flush()
                    last_printed = digits_stable

            if cfg.show_window:
                # Dibuja overlay usando último resultado
                roi_img, roi_xywh = crop_roi(frame, cfg.roi_rel)
                text, conf = last_result
                draw_overlay(frame, roi_xywh, text, conf)
                cv2.imshow(cfg.window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

    finally:
        src.release()
        if cfg.show_window:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()