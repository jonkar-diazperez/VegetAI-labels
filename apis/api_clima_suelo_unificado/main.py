import pandas as pd
import requests
import requests_cache
from flask import Flask, jsonify, request
from flask_cors import CORS
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# -------------------------------------------------
# 1. CONFIGURACIÓN GLOBAL
# -------------------------------------------------
app = Flask(__name__)
CORS(app)

DB_URL = "postgresql://admin:HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q@dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com:5432/reto_db_gty6"
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600)

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
import openmeteo_requests
openmeteo = openmeteo_requests.Client(session=retry_session)
url_api_forecast = "https://api.open-meteo.com/v1/forecast"

# --- MAPEOS FUNDAMENTALES (Si faltan, nada funciona) ---
TRADUCCIONES = {
    "temperature_2m": "temperatura",
    "relative_humidity_2m": "humedad_relativa",
    "soil_moisture_0_1cm": "humedad_suelo",
    "precipitation": "precipitacion",
    "windspeed_10m": "viento_velocidad",
    "winddirection_10m": "viento_direccion",
    "evapotranspiration": "evapotranspiracion"
}

MAPEO_API_DAILY = {
    "temperatura": "temperature_2m_mean",
    "humedad_relativa": "relative_humidity_2m_mean",
    "humedad_suelo": "soil_moisture_0_to_7cm_mean",
    "precipitacion": "precipitation_sum",
    "viento_velocidad": "wind_speed_10m_max",
    "viento_direccion": "wind_direction_10m_dominant",
    "evapotranspiracion": "et0_fao_evapotranspiration"
}

# -------------------------------------------------
# 2. FUNCIÓN AUXILIAR TIEMPO REAL
# -------------------------------------------------
def procesar_variable(var_name):
    datos = request.get_json(silent=True)
    if not datos or not all(k in datos for k in ["parcela_id", "lat", "lon"]):
        return jsonify({"error": "Faltan campos: parcela_id, lat, lon"}), 400
    try:
        params = {"latitude": datos["lat"], "longitude": datos["lon"], "current": [var_name]}
        res = openmeteo.weather_api(url_api_forecast, params=params)
        valor = round(res[0].Current().Variables(0).Value(), 2)
        nombre_es = TRADUCCIONES.get(var_name, var_name)

        query = text(f"INSERT INTO clima_parcela (parcela_id, fecha, latitud, longitud, {nombre_es}) VALUES (NOW(), :p_id, :lat, :lon, :val)")
        with engine.begin() as conn:
            conn.execute(query, {"p_id": datos["parcela_id"], "lat": datos["lat"], "lon": datos["lon"], "val": valor})
        return jsonify({"variable": nombre_es, "valor": valor, "status": "Guardado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# 3. ENDPOINTS INDIVIDUALES (TIEMPO REAL)
# -------------------------------------------------

# EJEMPLO DE CONSULTA

"""
{
  "status": "Guardado",
  "valor": 24.15,
  "variable": "temperatura"
}
"""

@app.route('/temperatura', methods=['POST'])
def temperatura(): return procesar_variable("temperature_2m")

@app.route('/humedad_relativa', methods=['POST'])
def humedad_relativa(): return procesar_variable("relative_humidity_2m")

@app.route('/humedad_suelo', methods=['POST'])
def humedad_suelo(): return procesar_variable("soil_moisture_0_1cm")

@app.route('/precipitacion', methods=['POST'])
def precipitacion(): return procesar_variable("precipitation")

@app.route('/viento_velocidad', methods=['POST'])
def viento_velocidad(): return procesar_variable("windspeed_10m")

@app.route('/viento_direccion', methods=['POST'])
def viento_direccion(): return procesar_variable("winddirection_10m")

@app.route('/evapotranspiracion', methods=['POST'])
def evapotranspiracion(): return procesar_variable("evapotranspiration")

# -------------------------------------------------
# 4. ENDPOINT HISTÓRICO DAILY
# -------------------------------------------------

# EJEMPLO DE CONSULTA JSON

"""
{
    "parcela_id": 784112,
    "lat": -33.1951,
    "lon": -70.7292,
    "inicio": "2024-01-01",
    "fin": "2024-01-15",
    "variables": [
        "temperatura",
        "precipitacion",
        "humedad_suelo",
        "evapotranspiracion"
    ]
}
"""

@app.route('/cargar_historico', methods=['POST'])
def cargar_historico():
    datos = request.get_json()
    if not datos: 
        return jsonify({"error": "No se recibió JSON"}), 400

    # Extraer datos del input
    parcela_id = datos.get("parcela_id")
    lat = datos.get("lat")
    lon = datos.get("lon")
    fecha_inicio = datos.get("inicio")
    fecha_fin = datos.get("fin")
    variables_solicitadas = datos.get("variables", [])

    # Validación de campos
    campos_obligatorios = ["parcela_id", "lat", "lon", "inicio", "fin"]
    faltantes = [f for f in campos_obligatorios if datos.get(f) is None]
    
    if faltantes or not variables_solicitadas:
        return jsonify({"error": f"Faltan parámetros: {', '.join(faltantes) if faltantes else 'variables'}"}), 400

    # Filtrar variables que existen en nuestro mapeo
    variables_validas = [v for v in variables_solicitadas if v in MAPEO_API_DAILY]
    if not variables_validas:
        return jsonify({"error": "Variables solicitadas no soportadas"}), 400

    try:
        # 1. Llamada a la API de Históricos de Open-Meteo
        api_vars = [MAPEO_API_DAILY[v] for v in variables_validas]
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "daily": ",".join(api_vars),
            "timezone": "UTC"
        }

        response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=30)
        data = response.json()

        if "error" in data:
            return jsonify({"error_api": data.get("reason")}), 400

        daily_data = data["daily"]
        fechas = daily_data["time"]

        # 2. Preparar datos para Base de Datos y para el Output JSON
        columnas_sql = ", ".join(variables_validas)
        placeholders = ", ".join([f":{v}" for v in variables_validas])
        
        query_db = text(f"INSERT INTO clima_parcela (parcela_id, fecha, latitud, longitud, {columnas_sql}) VALUES (:fecha, :p_id, :lat, :lon, {placeholders})")

        registros_db = []
        lista_historico_output = []

        for i in range(len(fechas)):
            # Diccionario para la DB
            fila_db = {
                "fecha": fechas[i],
                "p_id": parcela_id,
                "lat": lat,
                "lon": lon
            }
            # Diccionario para el JSON de salida 
            punto_json = {"fecha": fechas[i]}

            for var in variables_validas:
                valor = daily_data[MAPEO_API_DAILY[var]][i]
                fila_db[var] = valor
                punto_json[var] = valor

            registros_db.append(fila_db)
            lista_historico_output.append(punto_json)

        # 3. Guardar en Base de Datos
        with engine.begin() as conn:
            conn.execute(query_db, registros_db)

        # 4. Retornar salida
        return jsonify({
            "historico": lista_historico_output,
            "parcela_id": parcela_id,
            "periodo": {
                "fin": fecha_fin,
                "inicio": fecha_inicio
            },
            "status": "Éxito",
            "total_dias": len(lista_historico_output)
        })

    except Exception as e:
        return jsonify({"error": "Error interno", "detalle": str(e)}), 500

# -------------------------------------------------
# 5. CONSULTA SEMANA PREVIA DEFECTO
# -------------------------------------------------

"""
http://127.0.0.1:5000/consultar_datos?lat=-33.1951&lon=-70.7292&days=5
"""

@app.route('/consultar_datos', methods=['GET'])
def consultar_datos():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    dias_atras = request.args.get('days', default=7, type=int)
    
    if lat is None or lon is None:
        return jsonify({"error": "Faltan parametros 'lat' o 'lon'"}), 400
    
    try:
        # 1. Calcular rango de fechas
        hoy = datetime.now()
        fecha_inicio = hoy - timedelta(days=dias_atras)
        
        # 2. Configurar llamada a la API (Forecast)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_mean", 
                "relative_humidity_2m_mean", 
                "precipitation_probability_mean", 
                "wind_speed_10m_mean", 
                "winddirection_10m_dominant", 
                "et0_fao_evapotranspiration_sum"
            ],
            "timezone": "auto",
            "start_date": fecha_inicio.strftime('%Y-%m-%d'),
            "end_date": hoy.strftime('%Y-%m-%d'),
        }
        
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        daily = response.Daily()

        # 3. Procesamiento avanzado con Pandas
        data_dict = {
            "date": pd.date_range(
                start=pd.to_datetime(daily.Time() + response.UtcOffsetSeconds(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd() + response.UtcOffsetSeconds(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ),
            "temp_mean": daily.Variables(0).ValuesAsNumpy(),
            "humidity_mean": daily.Variables(1).ValuesAsNumpy(),
            "precip_prob": daily.Variables(2).ValuesAsNumpy(),
            "wind_speed": daily.Variables(3).ValuesAsNumpy(),
            "wind_direction": daily.Variables(4).ValuesAsNumpy(),
            "evapotranspiration": daily.Variables(5).ValuesAsNumpy()
        }
        
        df = pd.DataFrame(data=data_dict)
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        df = df.round(2)
        
        return jsonify({
            "status": "ok",
            "location": {"lat": lat, "lon": lon},
            "data": df.to_dict(orient='records')
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)