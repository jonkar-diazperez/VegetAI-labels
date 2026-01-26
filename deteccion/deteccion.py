import os
import cv2
import numpy as np
import json
from flask import Flask, request, jsonify
from roboflow import Roboflow
from dotenv import load_dotenv

# --- CONFIGURACIÓN GENERAL ---
load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not API_KEY:
    raise ValueError("❌ Falta ROBOFLOW_API_KEY en .env")

# --- INICIALIZAR ROBOFLOW UNA SOLA VEZ ---
print("🚀 Cargando modelo Roboflow en memoria...")
rf = Roboflow(api_key=API_KEY)
project = rf.workspace("agridrone-pblcc").project("agridetect")
model = project.version(3).model
print("✅ Modelo listo.")

# --- DEFINICIÓN DE CLASES ---

LABELS = {
    "sky":   ["sky", "cielo", "cloud"],
    "crop":  ["agriculture-land", "trees", "crop", "plant", "vegetation"],
    "soil":  ["field-soil", "unused-land", "soil", "dirt", "ground"]
}

# Clases que nunca deben usarse para cielo/suelo/cultivo
CLASES_PROHIBIDAS = [
    "person", "human", "man", "woman", "people",
    "car", "vehicle", "truck", "bus", "bike", "motorcycle",
    "animal", "dog", "cow", "sheep"
]

# --- FUNCIÓN PRINCIPAL DE SELECCIÓN DE PUNTO ---

def obtener_mejor_punto(detections, target_labels, zona):
    """
    zona = dict con:
        x_start, x_end, y_start, y_end
    """

    best_det = None
    max_conf = 0

    for det in detections:
        clase = det.get("class", "")
        conf = det.get("confidence", 0)
        x = det.get("x", 0)
        y = det.get("y", 0)

        # 🚫 Ignorar clases prohibidas
        if clase in CLASES_PROHIBIDAS:
            continue

        # Solo clases objetivo
        if clase not in target_labels:
            continue

        # 📐 Regla geométrica: debe caer dentro de su zona
        if not (zona["x_start"] <= x <= zona["x_end"] and zona["y_start"] <= y <= zona["y_end"]):
            continue

        # Elegir la de mayor confianza
        if conf > max_conf:
            max_conf = conf
            best_det = det

    # --- Si encontramos detección válida por IA ---
    if best_det:
        return {
            "x": int(best_det["x"]),
            "y": int(best_det["y"]),
            "metodo": "IA",
            "confianza": float(best_det["confidence"]),
            "clase": best_det["class"]
        }

    # --- Fallback geométrico (centro de la zona) ---
    x_fallback = int((zona["x_start"] + zona["x_end"]) / 2)
    y_fallback = int((zona["y_start"] + zona["y_end"]) / 2)

    return {
        "x": x_fallback,
        "y": y_fallback,
        "metodo": "FALLBACK",
        "confianza": 0.0,
        "clase": "heuristica"
    }

# --- ENDPOINT PRINCIPAL ---

@app.route('/analizar', methods=['POST'])
def analizar_imagen():

    # 1. Validar archivo
    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400

    file = request.files['image']

    try:
        # 2. Leer imagen (funciona para .jpg, .png, .insp si es jpg disfrazado)
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "El archivo no es una imagen válida"}), 400

        height, width, _ = img.shape

        # 3. Inferencia
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        prediction = model.predict(img_rgb, confidence=5).json()

        if isinstance(prediction, dict) and "predictions" in prediction:
            detections = prediction["predictions"]
        elif isinstance(prediction, list):
            detections = prediction
        else:
            detections = []

        # 4. Definir zonas geométricas dinámicas

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

        # 5. Extra: detectar personas aparte
        personas = []
        for det in detections:
            if det.get("class") in ["person", "human"]:
                personas.append({
                    "x": int(det["x"]),
                    "y": int(det["y"]),
                    "confianza": float(det["confidence"])
                })

        # 6. Calcular puntos finales
        punto_cielo = obtener_mejor_punto(detections, LABELS["sky"], rect_sky)
        punto_cultivo = obtener_mejor_punto(detections, LABELS["crop"], rect_crop)
        punto_suelo = obtener_mejor_punto(detections, LABELS["soil"], rect_soil)

        # 7. Construir respuesta
        result = {
            "status": "success",
            "dimensiones": {
                "width": width,
                "height": height
            },
            "personas_detectadas": len(personas),
            "personas": personas,  # puedes quitar esto si no lo quieres
            "puntos": {
                "cielo": punto_cielo,
                "cultivo": punto_cultivo,
                "suelo": punto_suelo
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ARRANQUE DEL SERVIDOR ---

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
