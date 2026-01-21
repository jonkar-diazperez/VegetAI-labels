from flask import Flask, jsonify, request
import openmeteo_requests
import requests_cache
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime

# ----------------------------
# CONFIGURACIÓN RENDER
# ----------------------------
hosting = "dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com"
puerto = "5432"
nombre_db = "reto_db_gty6"
usuario = "admin"
pswd = "HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q"

DATABASE_URL = f"postgresql://{usuario}:{pswd}@{hosting}:{puerto}/{nombre_db}"
engine = create_engine(DATABASE_URL)

# ----------------------------
# DATOS DE LA PARCELA
# ----------------------------
PARCELA_INFO = {
    "parcela_id": 784112,
    "nombre_parcela": "Parcela 20343",
    "finca_id": 227752,
    "lat": -33.19512257289546,
    "lon": -70.72926807455951
}

# ----------------------------
# SETUP CLIENTE OPEN-METEO
# ----------------------------
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
url_api = "https://api.open-meteo.com/v1/forecast"

app = Flask(__name__)

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
# FUNCIONES DE PERSISTENCIA (Gestión y Monitorización)
# ----------------------------
def registrar_log(endpoint, estado, mensaje="OK"):
    """Guarda rastro de la actividad para monitorización"""
    query = text("""
        INSERT INTO logs_procesos (fecha, proceso, endpoint, estado, mensaje)
        VALUES (:fecha, :proceso, :endpoint, :estado, :mensaje)
    """)
    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "fecha": datetime.now(),
                "proceso": "agrometeo-service",
                "endpoint": endpoint,
                "estado": estado,
                "mensaje": mensaje
            })
            conn.commit()
    except Exception as e:
        print(f"Error en monitorización: {e}")

def guardar_en_db(nombre_columna, valor, lat, lon):
    """Inserta el dato climático en Render"""
    query = text(f"""
        INSERT INTO registros_clima (
            fecha, parcela_id, nombre_parcela, finca_id, latitud, longitud, {nombre_columna}
        )
        VALUES (:fecha, :p_id, :p_nom, :f_id, :lat, :lon, :val)
    """)
    with engine.connect() as conn:
        conn.execute(query, {
            "fecha": datetime.now(),
            "p_id": PARCELA_INFO["parcela_id"],
            "p_nom": PARCELA_INFO["nombre_parcela"],
            "f_id": PARCELA_INFO["finca_id"],
            "lat": lat,
            "lon": lon,
            "val": valor
        })
        conn.commit()

# ----------------------------
# LÓGICA DE ENDPOINTS
# ----------------------------
def obtener_variable_actual(var_name):
    lat = request.args.get('lat', default=PARCELA_INFO["lat"], type=float)
    lon = request.args.get('lon', default=PARCELA_INFO["lon"], type=float)
    endpoint_path = request.path

    try:
        params = {"latitude": lat, "longitude": lon, "current": [var_name]}
        responses = openmeteo.weather_api(url_api, params=params)
        valor = round(responses[0].Current().Variables(0).Value(), 2)
        nombre_es = TRADUCCIONES.get(var_name, var_name)
        
        # 1. Guardar dato climático
        guardar_en_db(nombre_es, valor, lat, lon)
        # 2. Registrar log de éxito (Monitorización)
        registrar_log(endpoint_path, "EXITO")

        return jsonify({
            nombre_es: valor,
            "parcela": PARCELA_INFO["nombre_parcela"],
            "status": "Guardado y Monitorizado"
        })

    except Exception as e:
        registrar_log(endpoint_path, "ERROR", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return {"estado": "OK", "servicio": "Agrometeo Service", "version": "1.1.0"}

@app.route('/temperatura')
def temperatura(): return obtener_variable_actual("temperature_2m")

@app.route('/humedad_relativa')
def humedad_relativa(): return obtener_variable_actual("relative_humidity_2m")

@app.route('/humedad_suelo')
def humedad_suelo(): return obtener_variable_actual("soil_moisture_0_1cm")

@app.route('/precipitacion')
def precipitacion(): return obtener_variable_actual("precipitation")

@app.route('/viento_velocidad')
def viento_velocidad(): return obtener_variable_actual("windspeed_10m")

@app.route('/viento_direccion')
def viento_direccion(): return obtener_variable_actual("winddirection_10m")

@app.route('/evapotranspiracion')
def evapotranspiracion(): return obtener_variable_actual("evapotranspiration")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
