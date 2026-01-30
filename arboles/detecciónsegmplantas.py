import os
import cv2
import numpy as np
import requests
from flask import Flask, request, jsonify
from roboflow import Roboflow
from dotenv import load_dotenv

# --- CONFIGURACIÓN GENERAL ---
load_dotenv()
app = Flask(__name__)

# =========================
# 🔹 CONFIG PLANTNET
# =========================

PLANTNET_KEY = os.getenv("PLANTNET_KEY")
PN_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}&lang=es"

# =========================
# 🔹 CONFIG ROBOFLOW
# =========================

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not ROBOFLOW_API_KEY:
    raise ValueError("❌ Falta ROBOFLOW_API_KEY en .env")

print("🚀 Cargando modelo Roboflow en memoria...")
rf = Roboflow(api_key=ROBOFLOW_API_KEY)
project = rf.workspace("agridrone-pblcc").project("agridetect")
model = project.version(3).model
print("✅ Modelo listo.")

LABELS = {
    "sky":   ["sky", "cielo", "cloud"],
    "crop":  ["agriculture-land", "trees", "crop", "plant", "vegetation"],
    "soil":  ["field-soil", "unused-land", "soil", "dirt", "ground"]
}

CLASES_PROHIBIDAS = [
    "person", "human", "man", "woman", "people",
    "car", "vehicle", "truck", "bus", "bike", "motorcycle",
    "animal", "dog", "cow", "sheep"
]

# =========================
# 🔹 FUNCIÓN AUXILIAR
# =========================

def obtener_mejor_punto(detections, target_labels, zona):

    best_det = None
    max_conf = 0

    for det in detections:
        clase = det.get("class", "")
        conf = det.get("confidence", 0)
        x = det.get("x", 0)
        y = det.get("y", 0)

        if clase in CLASES_PROHIBIDAS:
            continue

        if clase not in target_labels:
            continue

        if not (zona["x_start"] <= x <= zona["x_end"] and zona["y_start"] <= y <= zona["y_end"]):
            continue

        if conf > max_conf:
            max_conf = conf
            best_det = det

    if best_det:
        return {
            "x": int(best_det["x"]),
            "y": int(best_det["y"]),
            "metodo": "IA",
            "confianza": float(best_det["confidence"]),
            "clase": best_det["class"]
        }

    x_fallback = int((zona["x_start"] + zona["x_end"]) / 2)
    y_fallback = int((zona["y_start"] + zona["y_end"]) / 2)

    return {
        "x": x_fallback,
        "y": y_fallback,
        "metodo": "FALLBACK",
        "confianza": 0.0,
        "clase": "heuristica"
    }

# =========================
# 🔹 ENDPOINT PLANTNET
# =========================

@app.route('/identificar', methods=['POST'])
def identificar_planta():

    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400

    file = request.files['image']

    try:
        files = [('images', (file.filename, file.read()))]
        data = {'organs': ['auto']}

        res_pn = requests.post(PN_URL, files=files, data=data)

        if res_pn.status_code == 200:
            json_data = res_pn.json()
            best_match = json_data['results'][0]
            species = best_match['species']

            scientific_name = species.get('scientificNameWithoutAuthor')
            common_names = species.get('commonNames', [])

            return jsonify({
                "status": "success",
                "nombre_cientifico": scientific_name,
                "nombre_comun": common_names[0] if common_names else "No disponible",
                "otros_nombres": common_names[1:4],
                "precision": f"{round(best_match.get('score', 0) * 100, 2)}%"
            })

        else:
            return jsonify({"error": "Error de Pl@ntNet", "codigo": res_pn.status_code}), res_pn.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# 🔹 ENDPOINT ROBOFLOW
# =========================

@app.route('/analizar', methods=['POST'])
def analizar_imagen():

    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400

    file = request.files['image']

    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "El archivo no es una imagen válida"}), 400

        height, width, _ = img.shape

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        prediction = model.predict(img_rgb, confidence=5).json()

        if isinstance(prediction, dict) and "predictions" in prediction:
            detections = prediction["predictions"]
        elif isinstance(prediction, list):
            detections = prediction
        else:
            detections = []

        rect_sky = {
            "x_start": int(width * 0.15),
            "x_end":   int(width * 0.85),
            "y_start": 0,
            "y_end":   int(height * 0.30)
        }

        rect_crop = {
            "x_start": int(width * 0.15),
            "x_end":   int(width * 0.85),
            "y_start": int(height * 0.30),
            "y_end":   int(height * 0.65)
        }

        rect_soil = {
            "x_start": int(width * 0.15),
            "x_end":   int(width * 0.85),
            "y_start": int(height * 0.65),
            "y_end":   height
        }

        personas = []
        for det in detections:
            if det.get("class") in ["person", "human"]:
                personas.append({
                    "x": int(det["x"]),
                    "y": int(det["y"]),
                    "confianza": float(det["confidence"])
                })

        punto_cielo = obtener_mejor_punto(detections, LABELS["sky"], rect_sky)
        punto_cultivo = obtener_mejor_punto(detections, LABELS["crop"], rect_crop)
        punto_suelo = obtener_mejor_punto(detections, LABELS["soil"], rect_soil)

        result = {
            "status": "success",
            "dimensiones": {
                "width": width,
                "height": height
            },
            "personas_detectadas": len(personas),
            "personas": personas,
            "puntos": {
                "cielo": punto_cielo,
                "cultivo": punto_cultivo,
                "suelo": punto_suelo
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# 🔹 ARRANQUE
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
