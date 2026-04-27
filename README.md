# OCR-Flujometro

Sistema de lectura óptica de caracteres (OCR) especializado en la captura y estabilización de lecturas numéricas desde medidores y flujómetros digitales utilizando cámaras web.

## 📋 Descripción

Este proyecto implementa un pipeline de OCR robusto que:

- **Captura video en tiempo real** desde cámaras web o cámaras IP (RTSP)
- **Extrae números** de pantallas de medidores usando Tesseract OCR
- **Estabiliza lecturas** mediante votación para filtrar ruido y fluctuaciones
- **Registra datos** en archivo CSV con timestamps
- **Preprocesa imágenes** con filtros avanzados para mejorar precisión del OCR
- **Visualiza en vivo** la región de interés y el resultado del preprocesamiento


## 🔧 Requisitos previos

### Sistema operativo
- Windows 10+ (recomendado para CAP_DSHOW en OpenCV)
- Linux o macOS (con ajustes menores)

### Dependencias del sistema
1. **Tesseract OCR** - Motor de reconocimiento de caracteres
   - Descargar desde: https://github.com/UB-Mannheim/tesseract/wiki
   - Instalar en: `C:\Program Files\Tesseract-OCR\`
   - Verificar instalación: `tesseract --version`

2. **Python 3.9+**

### Dependencias Python
Se instalan automáticamente con `requirements.txt`:
- `opencv-python` - Procesamiento de video y imágenes
- `numpy` - Operaciones numéricas
- `pytesseract` - Interfaz Python para Tesseract
- `Pillow` - Manipulación de imágenes

### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Verificar Tesseract
Asegúrate de que Tesseract está instalado en la ruta esperada. Si está en otra ubicación, edita el archivo Python y ajusta:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\ruta\a\tesseract.exe"
```

## 🚀 Uso

### Script test principal - `ocrtest.py`
Versión completa con estabilización, UI visual y registro en CSV.

```bash
python ocrtest.py
```

**Controles:**
- `q` - Salir de la aplicación
- La región ROI se muestra con un rectángulo verde
- Se muestran dos lecturas: cruda y estabilizada

**Salida:**
- Ventana de video con overlay de capturas
- Archivo `lecturas.csv` con timestamps y valores leídos
- Impresión en consola cada 10 segundos

**Configuración available (editar en el archivo):**
```python
CAMARA_INDEX    = 1           # Índice de la cámara (0=webcam integrada, 1=webcam externa)
CSV_ARCHIVO     = "lecturas.csv"
INTERVALO_PRINT = 10          # Segundos entre impresiones en terminal
INTERVALO_OCR   = 0.3         # Segundos entre ejecuciones de OCR
roi_x, roi_y    = 80, 80      # Posición superior izquierda del ROI (píxeles)
roi_ancho, roi_alto = 500, 220 # Ancho y alto del ROI
```

Permite visualizar dónde se capturará la región sin procesamiento OCR pesado.

## 📊 Estructura de salida CSV

El archivo `lecturas.csv` contiene:
```
timestamp,valor
2026-04-27 14:30:45,12345
2026-04-27 14:31:02,12346
2026-04-27 14:31:45,12347
```

- **timestamp**: Fecha y hora exacta de la lectura estable
- **valor**: Número de dígitos capturados por OCR

## 🔍 Cómo ajustar el ROI

1. Ejecutar `webcam.py` para ver el rectángulo en vivo
2. Editar variables `roi_x`, `roi_y`, `roi_ancho`, `roi_alto` en el script
3. Asegurarse de que el rectángulo verde cubre completamente la pantalla del medidor
4. No incluir marcos, bordes u otros elementos fuera del display de dígitos

**Recomendaciones:**
- Dejar 5-10 píxeles de margen alrededor de los dígitos
- Excluir completamente etiquetas, decimales o caracteres especiales
- Probar en diferentes ángulos y distancias de la cámara


## 🔗 Referencias

- [OpenCV Documentation](https://docs.opencv.org/)
- [Tesseract OCR wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- [PyTesseract docs](https://pytesseract.readthedocs.io/)
- [RTSP streaming cameras](https://www.generic-camera.com/manual/rtsp.html)

## Autor

**Oscar Andrés Painen Briones**   
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Oscar%20Painen-blue?logo=linkedin)](https://www.linkedin.com/in/oscarpainenbriones/)

---

**Última actualización:** Abril 2026
