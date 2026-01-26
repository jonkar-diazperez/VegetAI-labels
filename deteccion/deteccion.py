import os
import cv2
import numpy as np
import json
from flask import Flask, request, jsonify
from roboflow import Roboflow
from dotenv import load_dotenv

# --- CONFIGURACIÓN ---
load_dotenv()
app = Flask(__name__)

API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not API_KEY:
    raise ValueError("❌ Falta ROBOFLOW_API_KEY en .env")

# --- INICIALIZAR ROBOFLOW (Una sola vez al arrancar) ---
print("🚀 Cargando modelo Roboflow en memoria...")
rf = Roboflow(api_key=API_KEY)
project = rf.workspace("agridrone-pblcc").project("agridetect")
model = project.version(3).model
print("✅ Modelo listo.")

# --- LISTAS DE ETIQUETAS ---
LABELS = {
    "sky": ["sky", "cielo", "cloud"],
    "soil": ["field-soil", "unused-land", "soil", "dirt", "ground"],
    "crop": ["agriculture-land", "trees", "crop", "plant", "vegetation"]
}

def obtener_mejor_punto(detections, target_labels, heuristic_rect):
    """Lógica auxiliar para encontrar el mejor punto o usar fallback"""
    best_det = None
    max_conf = 0

    # 1. Buscar en detecciones de IA
    for det in detections:
        if det['class'] in target_labels:
            if det['confidence'] > max_conf:
                max_conf = det['confidence']
                best_det = det
    
    if best_det:
        return {
            "x": int(best_det['x']),
            "y": int(best_det['y']),
            "metodo": "IA",
            "confianza": float(best_det['confidence'])
        }
    
    # 2. Fallback Heurístico (Centro del rectángulo)
    x_fallback = int((heuristic_rect['x_start'] + heuristic_rect['x_end']) / 2)
    y_fallback = int((heuristic_rect['y_start'] + heuristic_rect['y_end']) / 2)
    
    return {
        "x": x_fallback,
        "y": y_fallback,
        "metodo": "FALLBACK",
        "confianza": 0.0
    }

@app.route('/analizar', methods=['POST'])
def analizar_imagen():
    # 1. Validar que llegó un archivo
    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400
    
    file = request.files['image']
    
    # 2. Leer la imagen en memoria (Funciona para .jpg y .insp)
    # .insp es un JPG, así que cv2 lo decodifica directo sin cambiar extensión
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "El archivo no es una imagen válida"}), 400

        height, width, _ = img.shape
        
        # 3. Inferencia
        # Convertir a RGB para Roboflow
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Predecir
        prediction = model.predict(img_rgb, confidence=5).json()
        
        detections = []
        if isinstance(prediction, dict) and 'predictions' in prediction:
            detections = prediction['predictions']
        elif isinstance(prediction, list):
            detections = prediction

        # 4. Calcular Puntos (Lógica Híbrida)
        
        # Rectángulos heurísticos (ajustados dinámicamente al tamaño de imagen)
        rect_sky  = {'x_start': int(width*0.2), 'x_end': int(width*0.8), 'y_start': 0, 'y_end': int(height*0.3)}
        rect_crop = {'x_start': int(width*0.2), 'x_end': int(width*0.8), 'y_start': int(height*0.4), 'y_end': int(height*0.7)}
        rect_soil = {'x_start': int(width*0.2), 'x_end': int(width*0.8), 'y_start': int(height*0.7), 'y_end': height}

        result = {
            "status": "success",
            "dimensiones": {"width": width, "height": height},
            "puntos": {
                "cielo": obtener_mejor_punto(detections, LABELS["sky"], rect_sky),
                "cultivo": obtener_mejor_punto(detections, LABELS["crop"], rect_crop),
                "suelo": obtener_mejor_punto(detections, LABELS["soil"], rect_soil)
            }
        }
        
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ejecutar en puerto 5002
    app.run(host='0.0.0.0', port=5002, debug=True)