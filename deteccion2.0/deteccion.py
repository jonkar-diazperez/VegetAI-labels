import torch
import torch.nn.functional as F
import numpy as np
import cv2
import py360convert
import os
import traceback
from flask import Flask, request, jsonify
from skimage.feature import peak_local_max
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

app = Flask(__name__)

# CONFIGURACIÓN DIRECTA
MODEL_ID = "nvidia/segformer-b0-finetuned-ade-512-512"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"--- Cargando modelo en: {DEVICE} ---")
processor = SegformerImageProcessor.from_pretrained(MODEL_ID)
model = SegformerForSemanticSegmentation.from_pretrained(MODEL_ID).to(DEVICE)
model.eval()

# Clases ADE20K: Cielo(2), Suelo(6,13,94), Cultivo/Planta(12,17,66), Persona(15)
CLASSES = {
    "veg": [12, 17, 66],
    "sky": [2],
    "floor": [6, 13, 94],
    "person": [15]
}

@app.route('/analizar', methods=['POST'])
def analizar():
    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No image provided"}), 400

    temp_path = os.path.join(os.getcwd(), f"temp_{file.filename}")
    file.save(temp_path)

    try:
        img_bgr = cv2.imread(temp_path)
        if img_bgr is None: return jsonify({"error": "Invalid image"}), 400
        
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]
        
        # Procesar 360 a Cubemap
        fw = 512 
        cube = py360convert.e2c(img_rgb, face_w=fw)
        cube_h, cube_w = cube.shape[:2]
        cube_maps = np.zeros((4, cube_h, cube_w), dtype=np.float32)

        faces = [(fw,2*fw, 2*fw,3*fw), (fw,2*fw, 0,fw), (0,fw, fw,2*fw), 
                 (2*fw,3*fw, fw,2*fw), (fw,2*fw, fw,2*fw), (fw,2*fw, 3*fw,4*fw)]
        
        for (y0, y1, x0, x1) in faces:
            face = cube[y0:y1, x0:x1]
            inputs = processor(images=face, return_tensors="pt").to(DEVICE)
            with torch.no_grad():
                outputs = model(**inputs)
                logits = F.interpolate(outputs.logits, size=(fw, fw), mode='bilinear', align_corners=False)
                probs = F.softmax(logits, dim=1).squeeze().cpu().numpy()
            
            for i, cat in enumerate(["veg", "sky", "floor", "person"]):
                valid_ids = [idx for idx in CLASSES[cat] if idx < probs.shape[0]]
                if valid_ids:
                    cube_maps[i, y0:y1, x0:x1] = np.sum(probs[valid_ids], axis=0)

        res = {"puntos": {}}
        p_mask = py360convert.c2e(np.stack([cube_maps[3]]*3, axis=-1), h, w)[:,:,0] > 0.3

        for i, (cat, key) in enumerate([("veg", "cultivo"), ("sky", "cielo"), ("floor", "suelo")]):
            m = py360convert.c2e(np.stack([cube_maps[i]]*3, axis=-1), h, w)[:,:,0]
            final_m = np.zeros_like(m)
            
            if cat == "sky": final_m[:int(h*0.5), :] = m[:int(h*0.5), :]
            elif cat == "veg": final_m[int(h*0.3):int(h*0.8), :] = m[int(h*0.3):int(h*0.8), :]
            elif cat == "floor": final_m[int(h*0.6):, :] = m[int(h*0.6):, :]
            
            final_m[p_mask] = 0
            coords = peak_local_max(final_m, min_distance=w//15, threshold_abs=0.1, num_peaks=5)
            res["puntos"][key] = [{"x": int(c[1]), "y": int(c[0]), "conf": round(float(final_m[c[0],c[1]]), 4)} for c in coords]

        return jsonify(res)
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Internal error"}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)