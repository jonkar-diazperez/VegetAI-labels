from flask import Flask, jsonify, request
from flask_cors import CORS
import openmeteo_requests
import requests_cache
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime
from datetime import datetime, timedelta  
import pandas as pd                       

# ----------------------------
# CONFIGURACIÓN RENDER / DB
# ----------------------------
hosting = "dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com"
puerto = "5432"
nombre_db = "reto_db_gty6"
usuario = "admin"
pswd = "HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q"

DATABASE_URL = f"postgresql://{usuario}:{pswd}@{hosting}:{puerto}/{nombre_db}"
engine = create_engine(DATABASE_URL)

# ----------------------------
# SETUP CLIENTE OPEN-METEO
# ----------------------------
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
url_api = "https://api.open-meteo.com/v1/forecast"

# ----------------------------
# TRADUCCIONES VARIABLES
# ----------------------------
TRADUCCIONES = {
    "temperature_2m": "temperatura",
    "relative_humidity_2m": "humedad_relativa",
    "soil_moisture_0_1cm": "humedad_suelo",
    "precipitation": "precipitacion",
    "windspeed_10m": "viento_velocidad",
    "winddirection_10m": "viento_direccion",
    "evapotranspiration": "evapotranspiracion"
}

# ----------------------------
# FLASK + CORS
# ----------------------------
app = Flask(__name__)
CORS(app)  # Permitir frontend

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def registrar_log(endpoint, estado, mensaje="OK"):
    query = text("""
        INSERT INTO logs_procesos (fecha, proceso, endpoint, estado, mensaje)
        VALUES (:fecha, :proceso, :endpoint, :estado, :mensaje)
    """)
    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "fecha": datetime.now(),
                "proceso": "clima_tiempo_real",
                "endpoint": endpoint,
                "estado": estado,
                "mensaje": mensaje
            })
            conn.commit()
    except Exception as e:
        print(f"Error en monitorización: {e}")

def guardar_en_db(nombre_columna, valor, parcela_info):
    # Query limpia: solo datos geográficos, ID y la variable medida
    query = text(f"""
        INSERT INTO clima_actual_parcela (
            parcela_id, fecha, latitud, longitud, {nombre_columna}
        )
        VALUES (:p_id, :fecha, :lat, :lon, :val)
    """)
    
    try:
        # Usamos la hora exacta de la consulta
        ahora = datetime.now() 

        with engine.begin() as conn:
            conn.execute(query, {
                "p_id": parcela_info.get("parcela_id"),
                "fecha": ahora,
                "lat": parcela_info["lat"],
                "lon": parcela_info["lon"],
                "val": valor
            })
    except Exception as e:
        registrar_log(request.path, "ERROR", f"Error DB: {str(e)}")
        print(f"Error al insertar: {e}")

# ----------------------------
# PROCESADOR CENTRAL DE VARIABLES
# ----------------------------
def procesar_variable(var_name):
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "Debe enviar un JSON con los datos de la parcela"}), 400

    # Validar campos obligatorios mínimos
    required = ["parcela_id", "lat", "lon"]
    faltantes = [f for f in required if f not in datos]
    if faltantes:
        return jsonify({"error": f"Faltan campos: {', '.join(faltantes)}"}), 400

    endpoint_path = request.path

    try:
        # Consultar API Open-Meteo
        params = {
            "latitude": datos["lat"],
            "longitude": datos["lon"],
            "current": [var_name]
        }
        responses = openmeteo.weather_api(url_api, params=params)
        valor = round(responses[0].Current().Variables(0).Value(), 2)
        nombre_es = TRADUCCIONES.get(var_name, var_name)

        # Guardar en la base de datos
        guardar_en_db(nombre_es, valor, datos)
        registrar_log(endpoint_path, "EXITO")

        # Respuesta JSON
        return jsonify({
            "variable": nombre_es,
            "valor": valor,
            "status": "Guardado y Monitorizado",
            "parcela": {
                "parcela_id": datos["parcela_id"],
                "lat": datos["lat"],
                "lon": datos["lon"]
            }
        })

    except Exception as e:
        registrar_log(endpoint_path, "ERROR", str(e))
        return jsonify({"error": "Error al consultar clima", "detalle": str(e)}), 500

# ----------------------------
# FORMATO DE CONSULTA JSON
# ----------------------------

"""
{
    "parcela_id": 784112,
    "lat": -33.1951,
    "lon": -70.7292
}
"""

# ----------------------------
# ENDPOINTS
# ----------------------------
@app.route('/')
def home():
    return {"estado": "OK", "info": "Envía POST a los endpoints climáticos con JSON de la parcela"}

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


# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
