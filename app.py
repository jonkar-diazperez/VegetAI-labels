import requests
import json
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Caché en memoria para clima
weather_cache = {}

def load_plague_rules():
    """Carga las reglas desde el archivo externo JSON"""
    try:
        with open('plagues_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró el archivo plagues_config.json")
        return {}

def calculate_gdd_sensitive(tmax, tmin, Tbase):
    """Cálculo de Grados Día Desarrollo (GDD)"""
    if tmax > Tbase:
        daily_avg = (tmax + tmin) / 2
        gdd = max(0, daily_avg - Tbase)
        if gdd == 0 and tmax > (Tbase + 2):
            return 0.5
        return gdd
    return 0

def get_risk_analysis(gdd_acum, rule, precip_max, humidity_avg):
    """Lógica de evaluación de riesgo"""
    gdd_ratio = min(gdd_acum / rule["GDD_max"], 1)
    precip_factor = 1 if precip_max >= rule["precip_threshold"] or humidity_avg > 85 else 0
    
    risk_score = (gdd_ratio * 0.7) + (precip_factor * 0.3)
    risk_percent = round(risk_score * 100, 1)
    
    level = "bajo"
    if risk_percent >= 70: level = "alto"
    elif risk_percent >= 40: level = "medio"
    
    return {
        "pest": rule["pest"],
        "risk_percent": risk_percent,
        "risk_level": level,
        "gdd_7_dias": round(gdd_acum, 1),
        "status": f"Monitoreo {'CRÍTICO' if level == 'alto' else 'preventivo'} recomendado."
    }

@app.route('/', methods=['GET'])
def index():
    return 'API de Alerta de Plagas'

@app.route('/plagas', methods=['GET', 'POST'])
def get_crop_risk():
    # Aceptar parámetros de múltiples fuentes (URL query, form-data, JSON)
    lat = request.args.get('lat') or request.form.get('lat') or (request.json or {}).get('lat')
    lon = request.args.get('lon') or request.form.get('lon') or (request.json or {}).get('lon')
    crop = request.args.get('fruta') or request.form.get('fruta') or (request.json or {}).get('fruta')
    
    # Convertir a tipos correctos
    try:
        lat = float(lat) if lat else None
        lon = float(lon) if lon else None
    except (ValueError, TypeError):
        return jsonify({"error": "Latitud y longitud deben ser números válidos"}), 400

    if not all([lat, lon, crop]):
        return jsonify({
            "error": "Faltan parámetros: latitud, longitud, fruta",
            "recibido": {"lat": lat, "lon": lon, "fruta": crop}
        }), 400

    # ESCALABILIDAD: Cargamos las reglas del JSON externo
    all_rules = load_plague_rules()
    crop_key = crop.lower()
    
    if crop_key not in all_rules:
        return jsonify({"error": f"Fruta no registrada. Disponibles: {list(all_rules.keys())}"}), 400

    # Gestión de Clima (Caché e Ingesta)
    cache_key = f"{lat}_{lon}"
    w_data = None
    if cache_key in weather_cache:
        data, ts = weather_cache[cache_key]
        if datetime.now() - ts < timedelta(hours=1):
            w_data = data

    if w_data is None:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_max"
               f"&timezone=auto")
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            w_data = res.json()["daily"]
            weather_cache[cache_key] = (w_data, datetime.now())
        except Exception as e:
            return jsonify({"error": "Error consultando clima", "detail": str(e)}), 502

    # Procesamiento con las reglas cargadas
    try:
        avg_hum = sum(w_data["relative_humidity_2m_max"]) / len(w_data["relative_humidity_2m_max"])
        max_precip = max(w_data["precipitation_sum"])
        
        results = []
        for rule in all_rules[crop_key]:
            gdd_total = sum([calculate_gdd_sensitive(mx, mn, rule["Tbase"]) 
                            for mx, mn in zip(w_data["temperature_2m_max"], w_data["temperature_2m_min"])])
            results.append(get_risk_analysis(gdd_total, rule, max_precip, avg_hum))

        return jsonify({
            "config": {"fruta": crop_key, "lat": lat, "lon": lon},
            "alertas": results,
        })
    except Exception as e:
        return jsonify({"error": "Error procesando datos", "detail": str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860, debug=True)