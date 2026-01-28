import torch
import torch.nn.functional as F
import numpy as np
import cv2
import py360convert
import json
import os
import traceback
from flask import Flask, request, jsonify
from skimage.feature import peak_local_max
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

app = Flask(__name__)

# 1. CARGA DE MODELO
device = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_ID = "nvidia/segformer-b0-finetuned-ade-512-512"
print(f"--- Cargando modelo en: {device} ---")

processor = SegformerImageProcessor.from_pretrained(MODEL_ID)
model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID).to(device)
model.eval()

# Mapeo de Clases: Vegetación, Cielo, Suelo, Personas
CLASSES = {"veg": [4, 12, 17], "sky": [2], "floor": [6, 9, 13, 29, 94], "person": [15]}

@app.route('/analizar', methods=['POST'])
def analizar():
    # RECIBIR IMAGEN
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No se recibió el archivo 'imagen'"}), 400

    # Ruta temporal universal (funciona en local y AWS)
    temp_path = os.path.join(os.getcwd(), f"temp_{file.filename}")
    file.save(temp_path)

    try:
        # LEER IMAGEN
        img_bgr = cv2.imread(temp_path)
        if img_bgr is None:
            return jsonify({"error": "Error al leer el archivo de imagen"}), 400
            
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]
        
        # PROCESAMIENTO CUBEMAP
        fw = 512 
        cube = py360convert.e2c(img_rgb, face_w=fw)
        cube_maps = np.zeros((4, 3*fw, 4*fw), dtype=np.float32)

        # Caras del Cubemap
        faces = [(fw,2*fw,2*fw,3*fw),(fw,2*fw,0,fw),(0,fw,fw,2*fw),(2*fw,3*fw,fw,2*fw),(fw,2*fw,fw,2*fw),(fw,2*fw,3*fw,4*fw)]
        
        for idx, (y0, y1, x0, x1) in enumerate(faces):
            face = cube[y0:y1, x0:x1]
            inputs = processor(images=face, return_tensors="pt").to(device)
            
            with torch.no_grad():
                outputs = model(**inputs)
                logits = F.interpolate(outputs.logits, size=(fw, fw), mode='bilinear', align_corners=False)
                probs = F.softmax(logits, dim=1).squeeze().cpu().numpy()
            
            for i, cat in enumerate(["veg", "sky", "floor", "person"]):
                cube_maps[i, y0:y1, x0:x1] = np.sum(probs[CLASSES[cat]], axis=0)

        # RECONSTRUCCIÓN Y FILTROS POR ALTURA (Y)
        res = {"puntos": {}}
        
        # Máscara de personas para limpieza
        p_cube = np.repeat(cube_maps[3][:, :, np.newaxis], 3, axis=2)
        person_map = py360convert.c2e(p_cube, h, w)[:, :, 0]
        p_mask = person_map > 0.3

        for i, cat in enumerate(["veg", "sky", "floor"]):
            c_cube = np.repeat(cube_maps[i][:, :, np.newaxis], 3, axis=2)
            m = py360convert.c2e(c_cube, h, w)[:, :, 0]
            
            final_m = np.zeros_like(m)
            # Aplicamos tus reglas de altura parametrizadas
            if cat == "sky":
                final_m[:min(500, h), :] = m[:min(500, h), :]
            elif cat == "veg" and h > 1000:
                final_m[1000:min(1300, h), :] = m[1000:min(1300, h), :]
            elif cat == "floor" and h > 1900:
                final_m[1900:, :] = m[1900:, :]
            
            # Bloqueo de puntos sobre personas
            final_m[p_mask] = 0
            
            # Extracción de coordenadas
            coords = peak_local_max(final_m, min_distance=w//20, threshold_abs=0.01, num_peaks=5)
            key_name = "cultivo" if cat == "veg" else ("cielo" if cat == "sky" else "suelo")
            res["puntos"][key_name] = [{"x": int(c[1]), "y": int(c[0]), "conf": round(float(final_m[c[0],c[1]]), 4)} for c in coords]

        return jsonify(res)

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Error interno durante el análisis"}), 500
    finally:
        # Limpieza del archivo temporal
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    # Puerto actualizado a 5002
    app.run(host='0.0.0.0', port=5002, debug=True)