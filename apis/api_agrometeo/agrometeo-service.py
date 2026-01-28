from flask import Flask, jsonify, request
from flask_cors import CORS
import openmeteo_requests
import requests_cache
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime

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
                "proceso": "agrometeo-service",
                "endpoint": endpoint,
                "estado": estado,
                "mensaje": mensaje
            })
            conn.commit()
    except Exception as e:
        print(f"Error en monitorización: {e}")

def guardar_en_db(nombre_columna, valor, parcela_info):
    # Permitimos que nombre_parcela y finca_id sean opcionales
    query = text(f"""
        INSERT INTO registros_clima (
            fecha, parcela_id, nombre_parcela, finca_id, latitud, longitud, {nombre_columna}
        )
        VALUES (:fecha, :p_id, :p_nom, :f_id, :lat, :lon, :val)
    """)
    with engine.connect() as conn:
        conn.execute(query, {
            "fecha": datetime.now(),
            "p_id": parcela_info["parcela_id"],
            "p_nom": parcela_info.get("nombre_parcela"),  # opcional
            "f_id": parcela_info.get("finca_id"),          # opcional
            "lat": parcela_info["lat"],
            "lon": parcela_info["lon"],
            "val": valor
        })
        conn.commit()

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

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
