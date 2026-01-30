from flask import Flask, request, jsonify
import requests
import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

# Configuración extendida de cultivos chilenos
CULTIVOS = {
    "cerezo": {"temp_critica": -2.2, "calor_critico": 32, "viento_max": 30, "nombre": "Cerezo"},
    "palto": {"temp_critica": -1.1, "calor_critico": 35, "viento_max": 25, "nombre": "Palto Hass"},
    "uva": {"temp_critica": 0.0, "calor_critico": 38, "viento_max": 40, "nombre": "Uva de Mesa"},
    "nogal": {"temp_critica": -1.5, "calor_critico": 36, "viento_max": 35, "nombre": "Nogal"},
    "generico": {"temp_critica": 0.0, "calor_critico": 35, "viento_max": 30, "nombre": "Cultivo General"}
}

# ==============================
# PROCESAMIENTO DE DATOS
# ==============================

def obtener_datos(lat, lon, forecast=False):
    url = "https://api.open-meteo.com/v1/forecast" if forecast else "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,precipitation,snowfall,cloud_cover,wind_speed_10m,relative_humidity_2m,soil_temperature_0_to_7cm",
        "timezone": "auto"
    }
    if not forecast:
        params["start_date"], params["end_date"] = "2015-01-01", "2025-12-31"
    
    res = requests.get(url, params=params, timeout=30).json()
    df = pd.DataFrame(res["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df

def preparar_inteligencia(df):
    df = df.copy()
    # Definimos lo que "fastidia" al cultivo (Targets)
    df["target_helada"] = (df["temperature_2m"] <= 0).astype(int)
    df["target_nevada"] = (df["snowfall"] > 0).astype(int)
    df["target_viento"] = (df["wind_speed_10m"] > 30).astype(int)
    
    # Features temporales y físicas
    df["hour"] = df["time"].dt.hour
    df["doy_sin"] = np.sin(2 * np.pi * df["time"].dt.dayofyear / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["time"].dt.dayofyear / 365)
    
    features = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "cloud_cover", "soil_temperature_0_to_7cm", "hour", "doy_sin", "doy_cos"]
    targets = ["target_helada", "target_nevada", "target_viento"]
    return df, features, targets

# ==============================
# MODELO MULTI-AMENAZA
# ==============================

def entrenar_o_cargar(id, df_hist=None):
    fname = f"shield_{id}.joblib"
    if os.path.exists(fname) and df_hist is None:
        return joblib.load(fname)
    
    if df_hist is not None:
        df, feats, targets = preparar_inteligencia(df_hist)
        # Entrenamos un modelo que predice varias amenazas a la vez
        model = RandomForestClassifier(n_estimators=150, class_weight='balanced', random_state=42)
        model.fit(df[feats], df[targets])
        joblib.dump((model, feats), fname)
        return model, feats
    return None, None

# ==============================
# LÓGICA DE ALERTA TOTAL
# ==============================

def analizar_riesgos(df_forecast, model, feats, cultivo_key):
    conf = CULTIVOS.get(cultivo_key, CULTIVOS["cerezo"])
    preds = model.predict(df_forecast[feats]) # Predice [Helada, Nevada, Viento]
    
    df_forecast["p_helada"] = preds[:, 0]
    df_forecast["p_nevada"] = preds[:, 1]
    df_forecast["p_viento"] = preds[:, 2]
    
    df_forecast["date"] = df_forecast["time"].dt.date
    resumen = df_forecast.groupby("date").agg(
        t_min=("temperature_2m", "min"),
        t_max=("temperature_2m", "max"),
        viento_max=("wind_speed_10m", "max"),
        nieve_sum=("snowfall", "sum"),
        hr_min=("relative_humidity_2m", "min")
    ).reset_index()

    def clasificar(row):
        alertas = []
        if row['t_min'] <= conf['temp_critica']: alertas.append("❄️ HELADA CRÍTICA")
        if row['t_max'] >= conf['calor_critico']: alertas.append("🔥 GOLPE DE CALOR")
        if row['nieve_sum'] > 2: alertas.append("🌨️ NIEVE (Peso)")
        if row['viento_max'] >= conf['viento_max']: alertas.append("💨 VIENTO FUERTE")
        if row['t_min'] > 0 and row['t_min'] < 4 and row['hr_min'] < 40: alertas.append("🖤 HELADA NEGRA")
        
        return " | ".join(alertas) if alertas else "✅ CONDICIONES ÓPTIMAS"

    resumen["estado"] = resumen.apply(clasificar, axis=1)
    return resumen

# ==============================
# ENDPOINT
# ==============================

@app.route("/monitor", methods=["POST"])
def monitor():
    data = request.get_json()
    lat, lon, id = data["lat"], data["lon"], data["id"]
    
    # Obtenemos el cultivo enviado
    cultivo_solicitado = data.get("cultivo", "cerezo").lower()
    
    # Si el cultivo no existe en nuestro diccionario, usamos uno genérico
    if cultivo_solicitado not in CULTIVOS:
        cultivo = "generico"
    else:
        cultivo = cultivo_solicitado
    try:
        model, feats = entrenar_o_cargar(id)
        if not model:
            hist = obtener_datos(lat, lon)
            model, feats = entrenar_o_cargar(id, hist)
        
        forecast = obtener_datos(lat, lon, forecast=True)
        # Aseguramos que el forecast tenga las mismas features
        forecast["hour"] = forecast["time"].dt.hour
        forecast["doy_sin"] = np.sin(2 * np.pi * forecast["time"].dt.dayofyear / 365)
        forecast["doy_cos"] = np.cos(2 * np.pi * forecast["time"].dt.dayofyear / 365)
        
        informe = analizar_riesgos(forecast, model, feats, cultivo)
        
        return jsonify({
            "id": id,
            "cultivo": CULTIVOS[cultivo]["nombre"],
            "reporte_7_dias": informe.to_dict(orient="records")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)