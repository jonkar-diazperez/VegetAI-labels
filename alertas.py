from flask import Flask, request, jsonify
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

# ==============================
# FUNCIONES (las tuyas)
# ==============================
def descargar_historico_hourly(lat, lon, start, end):
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        "&hourly=temperature_2m,precipitation,snowfall,"
        "cloud_cover,wind_speed_10m"
        "&timezone=auto"
    )
    r = requests.get(url, timeout=60)
    data = r.json()
    if "hourly" not in data:
        raise RuntimeError("No se pudo descargar hourly")
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def descargar_historico_por_anios(lat, lon, start_year, end_year):
    dfs = []
    for year in range(start_year, end_year + 1):
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        try:
            df_year = descargar_historico_hourly(lat, lon, start, end)
            dfs.append(df_year)
        except:
            pass
    if not dfs:
        raise RuntimeError("No se pudo descargar ningún año")
    return pd.concat(dfs, ignore_index=True)


def descargar_pronostico(lat, lon):
    url_hourly = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation,snowfall,"
        "cloud_cover,wind_speed_10m"
        "&timezone=auto"
    )
    r = requests.get(url_hourly, timeout=30)
    data = r.json()
    if "hourly" not in data:
        raise RuntimeError("No se pudo descargar hourly forecast")
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def preparar_features_hourly(df):
    df = df.copy()
    df["helada"] = (df["temperature_2m"] <= 0).astype(int)
    df["nevada"] = (df["snowfall"] > 0).astype(int)
    df["hour"] = df["time"].dt.hour
    df["dayofyear"] = df["time"].dt.dayofyear
    df["sin_doy"] = np.sin(2 * np.pi * df["dayofyear"] / 365)
    df["cos_doy"] = np.cos(2 * np.pi * df["dayofyear"] / 365)

    features = [
        "temperature_2m", "precipitation", "snowfall",
        "cloud_cover", "wind_speed_10m", "hour",
        "sin_doy", "cos_doy"
    ]
    return df, features


def entrenar_modelos_hourly(df, features):
    X = df[features]
    y_h = df["helada"]
    y_n = df["nevada"]

    model_h = RandomForestClassifier(
        n_estimators=300, max_depth=10,
        min_samples_leaf=10, random_state=42
    )
    model_n = RandomForestClassifier(
        n_estimators=300, max_depth=10,
        min_samples_leaf=10, random_state=42
    )

    model_h.fit(X, y_h)
    model_n.fit(X, y_n)

    return model_h, model_n


def generar_alertas_completas(df, model_h, model_n, features, umbral=0.5):
    df = df.copy()

    prob_h = model_h.predict_proba(df[features])
    df["prob_helada"] = prob_h[:, 1] if prob_h.shape[1] > 1 else 0.0

    prob_n = model_n.predict_proba(df[features])
    df["prob_nevada"] = prob_n[:, 1] if prob_n.shape[1] > 1 else 0.0

    df["alerta_helada"] = (df["prob_helada"] >= umbral).astype(int)
    df["alerta_nevada"] = (df["prob_nevada"] >= umbral).astype(int)
    df["alerta_lluvia"] = (df["precipitation"] >= 10).astype(int)
    df["alerta_viento"] = (df["wind_speed_10m"] >= 50).astype(int)

    df["date"] = df["time"].dt.date
    df_daily = df.groupby("date").agg(
        temperature_max=("temperature_2m", "max"),
        temperature_min=("temperature_2m", "min"),
        precipitation_sum=("precipitation", "sum"),
        snowfall_sum=("snowfall", "sum"),
        wind_speed_max=("wind_speed_10m", "max"),
        prob_helada_max=("prob_helada", "max"),
        prob_nevada_max=("prob_nevada", "max")
    ).reset_index()

    df_daily["alerta_ola_calor"] = (df_daily["temperature_max"] >= 35).astype(int)
    df_daily["alerta_lluvia_diaria"] = (df_daily["precipitation_sum"] >= 50).astype(int)
    df_daily["alerta_nevada_diaria"] = (df_daily["snowfall_sum"] > 0).astype(int)
    df_daily["alerta_helada_diaria"] = (df_daily["temperature_min"] <= 0).astype(int)

    return df, df_daily


def make_serializable(df):
    df_copy = df.copy()
    for col in df_copy.columns:
        if np.issubdtype(df_copy[col].dtype, np.datetime64):
            df_copy[col] = df_copy[col].astype(str)
        elif np.issubdtype(df_copy[col].dtype, np.integer):
            df_copy[col] = df_copy[col].astype(int)
        elif np.issubdtype(df_copy[col].dtype, np.floating):
            df_copy[col] = df_copy[col].astype(float)
        else:
            df_copy[col] = df_copy[col].astype(str)
    return df_copy


# ==============================
# ENDPOINTS
# ==============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict_zona():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON requerido"}), 400

    lat = data.get("lat")
    lon = data.get("lon")
    zona_id = data.get("zona")

    if lat is None or lon is None or zona_id is None:
        return jsonify({"error": "lat, lon y zona son obligatorios"}), 400

    try:
        # 1) Histórico
        df_hist = descargar_historico_por_anios(lat, lon, 2020, 2025)
        df_hist, features = preparar_features_hourly(df_hist)

        # 2) Entrenamiento
        model_helada, model_nevada = entrenar_modelos_hourly(df_hist, features)

        # 3) Forecast
        forecast_df = descargar_pronostico(lat, lon)
        forecast_df, _ = preparar_features_hourly(forecast_df)

        forecast_hourly, forecast_daily = generar_alertas_completas(
            forecast_df, model_helada, model_nevada, features
        )

        # 4) Serializar
        forecast_hourly = make_serializable(forecast_hourly)
        forecast_daily = make_serializable(forecast_daily)

        return jsonify({
            "zona": zona_id,
            "lat": lat,
            "lon": lon,
            "hourly": forecast_hourly.to_dict(orient="records"),
            "daily": forecast_daily.to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
