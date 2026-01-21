import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuración de Plagas con rangos de alerta semanal ajustados
# GDD_max representa el acumulado necesario en 7 días para considerar riesgo crítico
PLAGUE_RULES = {
    "manzana": [
        {"pest": "pulgón", "Tbase": 5, "GDD_max": 60, "precip_threshold": 3},
        {"pest": "moteado", "Tbase": 7, "GDD_max": 50, "precip_threshold": 10},
        {"pest": "carpocapsa", "Tbase": 10, "GDD_max": 40, "precip_threshold": 2}
    ],
    "uva": [
        {"pest": "mosca de la fruta", "Tbase": 10, "GDD_max": 50, "precip_threshold": 5},
        {"pest": "botrytis", "Tbase": 12, "GDD_max": 40, "precip_threshold": 15},
        {"pest": "oidio", "Tbase": 10, "GDD_max": 45, "precip_threshold": 8}
    ],
    "kiwi": [
        {"pest": "araña roja", "Tbase": 7, "GDD_max": 55, "precip_threshold": 4},
        {"pest": "botrytis", "Tbase": 10, "GDD_max": 40, "precip_threshold": 12}
    ],
    "naranja": [
        {"pest": "pulgón", "Tbase": 12, "GDD_max": 35, "precip_threshold": 3},
        {"pest": "cochinilla", "Tbase": 13, "GDD_max": 30, "precip_threshold": 2}
    ],
    "limón": [
        {"pest": "pulgón", "Tbase": 12, "GDD_max": 30, "precip_threshold": 2},
        {"pest": "minador", "Tbase": 15, "GDD_max": 25, "precip_threshold": 1}
    ]
}

def calculate_gdd_sensitive(tmax, tmin, Tbase):
    """
    Método de corte: Si la temperatura máxima supera la base, 
    hay actividad biológica aunque el promedio sea bajo.
    """
    if tmax > Tbase:
        # Calculamos el aporte de calor efectivo sobre la base
        # Se usa el promedio diario ajustado a la base
        daily_avg = (tmax + tmin) / 2
        gdd = max(0, daily_avg - Tbase)
        
        # Si el promedio es bajo pero la máxima fue alta, 
        # aseguramos un mínimo de progreso biológico (0.5 GDD)
        if gdd == 0 and tmax > (Tbase + 2):
            return 0.5
        return gdd
    return 0

def get_risk_analysis(gdd_acum, rule, precip_max, humidity_avg):
    # Proporción de calor acumulado
    gdd_ratio = min(gdd_acum / rule["GDD_max"], 1)
    
    # Factor humedad: La lluvia o humedad alta (>85%) aumenta el riesgo base
    precip_factor = 1 if precip_max >= rule["precip_threshold"] or humidity_avg > 85 else 0
    
    # Cálculo ponderado: 70% calor, 30% condiciones de humedad
    risk_score = (gdd_ratio * 0.7) + (precip_factor * 0.3)
    risk_percent = round(risk_score * 100, 1)
    
    if risk_percent >= 70: level = "alto"
    elif risk_percent >= 40: level = "medio"
    else: level = "bajo"
    
    return {
        "pest": rule["pest"],
        "risk_percent": risk_percent,
        "risk_level": level,
        "gdd_7_dias": round(gdd_acum, 1),
        "status": f"Monitoreo {'CRÍTICO' if level == 'alto' else 'preventivo'} recomendado."
    }

@app.route('/plagas', methods=['GET'])
def get_crop_risk():
    lat = request.args.get('latitud', type=float)
    lon = request.args.get('longitud', type=float)
    crop = request.args.get('fruta', type=str)

    if not all([lat, lon, crop]):
        return jsonify({"error": "Parámetros insuficientes (latitud, longitud, fruta)"}), 400

    crop_key = crop.lower()
    if crop_key not in PLAGUE_RULES:
        return jsonify({"error": f"Fruta no registrada. Disponibles: {list(PLAGUE_RULES.keys())}"}), 400

    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_max"
        f"&timezone=America/Santiago"
    )
    
    try:
        res = requests.get(weather_url, timeout=10)
        w_data = res.json()["daily"]
        
        # Diagnóstico para el administrador
        avg_humidity = sum(w_data["relative_humidity_2m_max"]) / 7
        max_precip = max(w_data["precipitation_sum"])
        
        analisis_alertas = []
        for rule in PLAGUE_RULES[crop_key]:
            gdd_total = sum([
                calculate_gdd_sensitive(mx, mn, rule["Tbase"]) 
                for mx, mn in zip(w_data["temperature_2m_max"], w_data["temperature_2m_min"])
            ])
            
            analisis_alertas.append(get_risk_analysis(gdd_total, rule, max_precip, avg_humidity))

        return jsonify({
            "config": {"fruta": crop_key, "lat": lat, "lon": lon},
            "alertas": analisis_alertas,
            "meteo_data": {
                "max_temp_semana": max(w_data["temperature_2m_max"]),
                "min_temp_semana": min(w_data["temperature_2m_min"]),
                "humedad_promedio_max": round(avg_humidity, 1),
                "lluvia_detectada": "Sí" if max_precip > 0 else "No"
            }
        })

    except Exception as e:
        return jsonify({"error": "Error al conectar con el servidor meteorológico", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)