from flask import Flask, request, jsonify, send_file
from pathlib import Path
import os
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

_model = None
_model_loading = False

def load_model_background():
    """Cargar modelo en background al iniciar"""
    global _model, _model_loading
    _model_loading = True
    print("🔄 Pre-cargando modelo en background...")
    try:
        from ultralytics import YOLO
        if Path("best.pt").exists() and Path("best.pt").stat().st_size > 1_000_000:
            print("✅ Cargando best.pt")
            _model = YOLO('best.pt')
            print("✅ best.pt cargado correctamente")
        else:
            print("⚠️ best.pt no encontrado, usando yolov8n.pt")
            _model = YOLO('yolov8n.pt')
            print("✅ yolov8n.pt cargado")
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        _model = None
    _model_loading = False

def get_model():
    """Obtener modelo, esperar si está cargando"""
    global _model
    if _model is None:
        if not _model_loading:
            load_model_background()
        # Esperar a que termine de cargar
        while _model_loading:
            import time
            time.sleep(0.5)
    return _model

# Pre-cargar modelo en thread separado al iniciar
print("⏳ Iniciando pre-carga de modelo...")
threading.Thread(target=load_model_background, daemon=True).start()

@app.route("/")
def home():
    return jsonify({"status": "ok"})

@app.route("/health")  
def health():
    return "OK", 200

@app.route("/status")
def status():
    """Ver estado de carga del modelo"""
    return jsonify({
        "modelo_cargado": _model is not None,
        "cargando": _model_loading
    })

@app.route("/detect", methods=["POST"])
def detect_plagas():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file"}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "Invalid file"}), 400
        
        # Extraer solo el nombre del archivo (sin paths)
        clean_filename = secure_filename(Path(file.filename).name)
        if not clean_filename:
            clean_filename = "image.jpg"
        
        print(f"Archivo recibido: {file.filename} → Guardando como: {clean_filename}")
        model = get_model()
        
        img_path = UPLOAD_FOLDER / clean_filename
        print(f"Guardando en: {img_path}")
        file.save(img_path)
        
        print("Prediciendo...")
        results = model.predict(source=str(img_path), save=True, conf=0.25)
        print("Predicción hecha")
        
        detections = []
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])
            detections.append({
                "plaga": cls_name, 
                "confianza": round(conf, 2)
            })
        
        return jsonify({
            "detecciones": detections,
            "total": len(detections),
            "imagen_resultado": f"/imagen/{clean_filename}"
        })
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/imagen/<filename>")
def get_imagen(filename):
    try:
        img_path = Path("runs/detect/predict") / filename
        if not img_path.exists():
            return jsonify({"error": "Not found"}), 404
        return send_file(img_path, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Usar puerto 7860 para Hugging Face
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Servidor en puerto {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)