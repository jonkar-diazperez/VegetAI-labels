import io
import psutil
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- CONFIGURACIÓN DE RUTAS ---
MODEL_PATH = r"C:\Users\Administrador\Desktop\repositorios_agc\repo_agc\repo_vegetAIbles\VegetAI-labels\runs\detect\wheat_fast_v1\weights\best.pt"

# Estadísticas de sesión
stats = {
    "peticiones_totales": 0,
    "inicio_servicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

print("🌾 Cargando cerebro de VegetAI con filtro de saturación...")
try:
    model = YOLO(MODEL_PATH)
    model_loaded = True
    print("✅ Modelo cargado correctamente.")
except Exception as e:
    print(f"❌ Error al cargar el modelo: {e}")
    model_loaded = False

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online" if model_loaded else "offline",
        "sistema": {
            "cpu": f"{psutil.cpu_percent()}%",
            "ram": f"{psutil.virtual_memory().percent}%"
        },
        "stats": stats
    })

@app.route('/predict', methods=['POST'])
def predict():
    if not model_loaded:
        return jsonify({"error": "Modelo no disponible"}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "No se subió ninguna imagen"}), 400

    file = request.files['file']
    img_bytes = file.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Inferencia de YOLO
    results = model(img, conf=0.25, verbose=False)
    
    verdes, intermedios, doradas = 0, 0, 0
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = img[y1:y2, x1:x2]
            if crop.size == 0: continue
            
            # --- NUEVA LÓGICA DE FILTRADO DE COLOR ---
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            
            # Creamos una máscara para capturar solo colores "vivos"
            # S > 40: Elimina blancos, grises y el cielo claro
            # V > 40: Elimina sombras muy oscuras
            lower_vibrant = np.array([0, 40, 40])
            upper_vibrant = np.array([180, 255, 255])
            mask = cv2.inRange(hsv, lower_vibrant, upper_vibrant)
            
            # Extraemos los píxeles que pasaron el filtro
            pixels_validos = hsv[mask > 0]

            if pixels_validos.size > 0:
                hue_final = np.mean(pixels_validos[:, 0])
            else:
                # Si no hay píxeles vibrantes, usamos el promedio total como último recurso
                hue_final = np.mean(hsv[:, :, 0])
            
            # Umbrales ajustados tras ver tu imagen:
            # Verde: > 38 | Intermedio (Amarillento): 25-38 | Dorado: < 25
            if hue_final > 38:
                verdes += 1
            elif 25 <= hue_final <= 38:
                intermedios += 1
            else:
                doradas += 1

    # Lógica Agronómica (Promedio ponderado)
    total = verdes + intermedios + doradas
    p_madurez = ((doradas + (intermedios * 0.5)) / total * 100) if total > 0 else 0
    
    if p_madurez < 25:
        estado = "CRECIMIENTO ACTIVO (VERDE)"
    elif 25 <= p_madurez < 50:
        estado = "MADURACIÓN INICIAL (LECHOSO)"
    elif 50 <= p_madurez < 85:
        estado = "MADURACIÓN AVANZADA (PASTOSO)"
    else:
        estado = "LISTO PARA COSECHAR (SECADO FINAL)"

    stats["peticiones_totales"] += 1

    return jsonify({
        "metadata": {
            "total_espigas": total,
            "timestamp": datetime.now().isoformat()
        },
        "analisis": {
            "indice_madurez": f"{round(p_madurez, 2)}%",
            "estado_campo": estado,
            "conteo": {
                "verdes": verdes,
                "intermedios": intermedios,
                "dorados": doradas
            }
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)