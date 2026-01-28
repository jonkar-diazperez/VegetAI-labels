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
# SETUP CLIENTE OPEN-METEO
# ----------------------------
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
url_api = "https://api.open-meteo.com/v1/forecast"

app = Flask(__name__)

# ----------------------------
# TRADUCCIÓN VARIABLES
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

def guardar_en_db(nombre_columna, valor, parcela_id, nombre_parcela, finca_id, lat, lon):
    query = text(f"""
        INSERT INTO registros_clima (
            fecha, parcela_id, nombre_parcela, finca_id, latitud, longitud, {nombre_columna}
        )
        VALUES (:fecha, :p_id, :p_nom, :f_id, :lat, :lon, :val)
    """)
    with engine.connect() as conn:
        conn.execute(query, {
            "fecha": datetime.now(),
            "p_id": parcela_id,
            "p_nom": nombre_parcela,
            "f_id": finca_id,
            "lat": lat,
            "lon": lon,
            "val": valor
        })
        conn.commit()

def obtener_variable(variable_key):
    datos = request.get_json()
    if not datos:
        return jsonify({"error": "No se recibió JSON"}), 400

    try:
        parcela_id = datos["parcela_id"]
        nombre_parcela = datos["nombre_parcela"]
        finca_id = datos["finca_id"]
        lat = float(datos["lat"])
        lon = float(datos["lon"])
    except KeyError as e:
        return jsonify({"error": f"Falta parámetro: {e}"}), 400
    except ValueError:
        return jsonify({"error": "Lat o Lon no son válidos"}), 400

    if variable_key not in TRADUCCIONES:
        return jsonify({"error": f"Variable no válida: {variable_key}"}), 400

    try:
        params = {"latitude": lat, "longitude": lon, "current": [variable_key]}
        responses = openmeteo.weather_api(url_api, params=params)
        valor = round(responses[0].Current().Variables(0).Value(), 2)
        nombre_es = TRADUCCIONES[variable_key]

        guardar_en_db(nombre_es, valor, parcela_id, nombre_parcela, finca_id, lat, lon)
        registrar_log(request.path, "EXITO")

        return jsonify({
            "parcela_id": parcela_id,
            "nombre_parcela": nombre_parcela,
            "finca_id": finca_id,
            "lat": lat,
            "lon": lon,
            "variable": nombre_es,
            "valor": valor,
            "status": "Guardado y monitorizado"
        })

    except Exception as e:
        registrar_log(request.path, "ERROR", str(e))
        return jsonify({"error": str(e)}), 500

# ----------------------------
# ENDPOINTS POR VARIABLE
# ----------------------------
@app.route('/temperatura', methods=['POST'])
def temperatura(): return obtener_variable("temperature_2m")

@app.route('/humedad_relativa', methods=['POST'])
def humedad_relativa(): return obtener_variable("relative_humidity_2m")

@app.route('/humedad_suelo', methods=['POST'])
def humedad_suelo(): return obtener_variable("soil_moisture_0_1cm")

@app.route('/precipitacion', methods=['POST'])
def precipitacion(): return obtener_variable("precipitation")

@app.route('/viento_velocidad', methods=['POST'])
def viento_velocidad(): return obtener_variable("windspeed_10m")

@app.route('/viento_direccion', methods=['POST'])
def viento_direccion(): return obtener_variable("winddirection_10m")

@app.route('/evapotranspiracion', methods=['POST'])
def evapotranspiracion(): return obtener_variable("evapotranspiration")

# ----------------------------
# ENDPOINT HOME
# ----------------------------
@app.route('/')
def home():
    return {"estado": "OK", "servicio": "Agrometeo Service", "version": "1.3.0"}

# ----------------------------
# EJECUTAR SERVICIO
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
