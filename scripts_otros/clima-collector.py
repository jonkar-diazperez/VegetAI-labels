
# clima-collector.py
import openmeteo_requests
import requests_cache
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime
import time

# 1. CONFIGURACIÓN RENDER (Igual a tu API)
hosting = "dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com"
puerto = "5432"
nombre_db = "reto_db_gty6"
usuario = "admin"
pswd = "HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q"

DATABASE_URL = f"postgresql://{usuario}:{pswd}@{hosting}:{puerto}/{nombre_db}"
engine = create_engine(DATABASE_URL)

PARCELA_INFO = {
    "parcela_id": 784112,
    "nombre_parcela": "Parcela 20343",
    "finca_id": 227752,
    "lat": -33.19512257289546,
    "lon": -70.72926807455951
}

# 2. SETUP CLIENTE OPEN-METEO (Igual a tu API)
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
url_api = "https://api.open-meteo.com/v1/forecast" # <--- LA CLAVE ES ESTA RUTA

def recolectar_y_guardar():
    print(f"[{datetime.now()}] Iniciando colecta horaria...")
    try:
        # Pedimos todas las variables juntas
        params = {
            "latitude": PARCELA_INFO["lat"],
            "longitude": PARCELA_INFO["lon"],
            "current": [
                "temperature_2m", "relative_humidity_2m", "precipitation", 
                "wind_speed_10m", "wind_direction_10m", 
                "soil_moisture_0_1cm", "evapotranspiration"
            ]
        }
        
        responses = openmeteo.weather_api(url_api, params=params)
        current = responses[0].Current()
        
        # INSERT en bloque (Igual a la lógica de tu API pero con todas las columnas)
        query = text("""
            INSERT INTO registros_clima (
                fecha, parcela_id, nombre_parcela, finca_id, latitud, longitud, 
                temperatura, humedad_relativa, precipitacion, 
                viento_velocidad, viento_direccion, humedad_suelo, evapotranspiracion
            )
            VALUES (:fecha, :p_id, :p_nom, :f_id, :lat, :lon, :t, :hr, :pr, :vv, :vd, :hs, :ev)
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "fecha": datetime.now(),
                "p_id": PARCELA_INFO["parcela_id"],
                "p_nom": PARCELA_INFO["nombre_parcela"],
                "f_id": PARCELA_INFO["finca_id"],
                "lat": PARCELA_INFO["lat"],
                "lon": PARCELA_INFO["lon"],
                "t": round(current.Variables(0).Value(), 2),
                "hr": round(current.Variables(1).Value(), 2),
                "pr": round(current.Variables(2).Value(), 2),
                "vv": round(current.Variables(3).Value(), 2),
                "vd": round(current.Variables(4).Value(), 2),
                "hs": round(current.Variables(5).Value(), 2),
                "ev": round(current.Variables(6).Value(), 2)
            })
            conn.commit()
        print("✅ Éxito: Fila horaria guardada en Render.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        recolectar_y_guardar()
        print("Esperando 1 hora...")
        time.sleep(3600)
