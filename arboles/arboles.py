import os
import io
import cv2
import json
import numpy as np
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from roboflow import Roboflow
from dotenv import load_dotenv

# =========================
# 🔹 CONFIGURACIÓN GENERAL
# =========================

load_dotenv()
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CROPS_DIR = os.path.join(DATA_DIR, "crops")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

os.makedirs(CROPS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ---- PLANTNET ----
PLANTNET_KEY = os.getenv("PLANTNET_KEY")
PN_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}&lang=es"

if not PLANTNET_KEY:
    raise ValueError("❌ Falta PLANTNET_KEY en .env")

# ---- ROBOFLOW ----
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not ROBOFLOW_API_KEY:
    raise ValueError("❌ Falta ROBOFLOW_API_KEY en .env")

print("🚀 Cargando modelo Roboflow en memoria...")
rf = Roboflow(api_key=ROBOFLOW_API_KEY)
project = rf.workspace("agridrone-pblcc").project("agridetect")
model = project.version(3).model
print("✅ Modelo listo.")

# =========================
# 🔹 CLASES DE INTERÉS
# =========================

CLASES_INTERES = ["crop", "trees", "tree", "plant", "vegetation"]

# =========================
# 🔹 FUNCIONES AUXILIARES
# =========================

def dibujar_detecciones(img, detections):
    img_draw = img.copy()

    for det in detections:
        clase = det.get("class", "")
        if clase not in CLASES_INTERES:
            continue

        x = int(det["x"])
        y = int(det["y"])
        w = int(det["width"])
        h = int(det["height"])
        conf = det.get("confidence", 0)

        x1 = int(x - w / 2)
        y1 = int(y - h / 2)
        x2 = int(x + w / 2)
        y2 = int(y + h / 2)

        color = (0, 255, 0)  # verde

        cv2.rectangle(img_draw, (x1, y1), (x2, y2), color, 2)

        label = f"{clase} {conf:.2f}"
        cv2.putText(img_draw, label, (x1, max(0, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return img_draw


def dibujar_punto(img, x, y, texto="Planta seleccionada"):
    img_draw = img.copy()
    cv2.circle(img_draw, (x, y), 6, (0, 255, 255), -1)  # amarillo
    cv2.putText(img_draw, texto, (x + 10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    return img_draw


def recortar_bbox(img, det):
    h_img, w_img, _ = img.shape

    x = int(det["x"])
    y = int(det["y"])
    w = int(det["width"])
    h = int(det["height"])

    x1 = max(0, int(x - w / 2))
    y1 = max(0, int(y - h / 2))
    x2 = min(w_img, int(x + w / 2))
    y2 = min(h_img, int(y + h / 2))

    return img[y1:y2, x1:x2]


def generar_nombre_unico(prefijo, extension):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    return f"{timestamp}_{prefijo}.{extension}"


# =========================
# 🔹 ENDPOINT PRINCIPAL
# =========================

@app.route('/analizar_y_clasificar', methods=['POST'])
def analizar_y_clasificar():

    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400

    file = request.files['image']

    try:
        # 1. Leer imagen
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "El archivo no es una imagen válida"}), 400

        height, width, _ = img.shape

        # 2. Inferencia Roboflow
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        prediction = model.predict(img_rgb, confidence=5).json()

        if isinstance(prediction, dict) and "predictions" in prediction:
            detections = prediction["predictions"]
        elif isinstance(prediction, list):
            detections = prediction
        else:
            detections = []

        # 3. Filtrar solo crop y tree
        detections_filtradas = [
            d for d in detections
            if d.get("class") in CLASES_INTERES
        ]

        if not detections_filtradas:
            return jsonify({
                "status": "no_detections",
                "mensaje": "No se detectaron plantas o árboles"
            }), 200

        # 4. Elegir la mejor detección (mayor área)
        detections_ordenadas = sorted(
            detections_filtradas,
            key=lambda d: d["width"] * d["height"],
            reverse=True
        )

        mejor_det = detections_ordenadas[0]

        x_sel = int(mejor_det["x"])
        y_sel = int(mejor_det["y"])

        # 5. Dibujar bounding boxes y punto
        img_boxes = dibujar_detecciones(img, detections_filtradas)
        img_final = dibujar_punto(img_boxes, x_sel, y_sel)

        # 6. Recortar región exacta
        crop_img = recortar_bbox(img, mejor_det)

        if crop_img.size == 0:
            return jsonify({"error": "No se pudo recortar la región de la planta"}), 400

        # 7. Guardar recorte en disco
        nombre_crop = generar_nombre_unico("crop", "jpg")
        ruta_crop = os.path.join(CROPS_DIR, nombre_crop)
        cv2.imwrite(ruta_crop, crop_img)

        # 8. Enviar recorte a Pl@ntNet
        _, buffer = cv2.imencode(".jpg", crop_img)
        crop_bytes = buffer.tobytes()

        files = [('images', (nombre_crop, crop_bytes))]
        data = {'organs': ['auto']}

        res_pn = requests.post(PN_URL, files=files, data=data, timeout=20)

        plantnet_raw = None
        plantnet_result = None

        if res_pn.status_code == 200:
            plantnet_raw = res_pn.json()

            if plantnet_raw.get("results"):
                best_match = plantnet_raw["results"][0]
                species = best_match["species"]

                plantnet_result = {
                    "nombre_cientifico": species.get("scientificNameWithoutAuthor"),
                    "nombre_comun": species.get("commonNames", [None])[0],
                    "otros_nombres": species.get("commonNames", [])[1:4],
                    "precision": round(best_match.get("score", 0) * 100, 2)
                }
            else:
                plantnet_result = {
                    "mensaje": "Pl@ntNet no encontró coincidencias"
                }
        else:
            plantnet_result = {
                "error": "Error de Pl@ntNet",
                "codigo": res_pn.status_code
            }

        # 9. Construir JSON completo a guardar
        resultado_json = {
            "timestamp": datetime.now().isoformat(),
            "imagen_original": {
                "width": width,
                "height": height
            },
            "deteccion_seleccionada": {
                "x": x_sel,
                "y": y_sel,
                "width": float(mejor_det["width"]),
                "height": float(mejor_det["height"]),
                "clase": mejor_det.get("class"),
                "confianza": float(mejor_det.get("confidence")),
                "area": float(mejor_det["width"] * mejor_det["height"])
            },
            "ruta_crop": ruta_crop,
            "plantnet_resumen": plantnet_result,
            "plantnet_raw": plantnet_raw  # respuesta completa de Pl@ntNet
        }

        # 10. Guardar JSON en disco
        nombre_json = generar_nombre_unico("result", "json")
        ruta_json = os.path.join(RESULTS_DIR, nombre_json)

        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(resultado_json, f, indent=2, ensure_ascii=False)

        # 11. Codificar imagen final para devolver
        _, buffer_final = cv2.imencode(".jpg", img_final)
        img_final_bytes = buffer_final.tobytes()

        # 12. Respuesta al cliente
        return jsonify({
            "status": "success",
            "ruta_crop_guardado": ruta_crop,
            "ruta_json_guardado": ruta_json,
            "clasificacion_plantnet": plantnet_result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 🔹 ARRANQUE
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

