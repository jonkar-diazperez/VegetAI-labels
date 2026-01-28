import os
import ee
import pandas as pd
import requests
import requests_cache
from flask import Flask, jsonify, request
from flask_cors import CORS
from retry_requests import retry
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
import openmeteo_requests
from dateutil.relativedelta import relativedelta
import threading
import json

# -------------------------------------------------
# 1. CONFIGURACIÓN GLOBAL Y BASE DE DATOS
# -------------------------------------------------
app = Flask(__name__)
CORS(app)

DATABASE_URL = "postgresql://admin:HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q@dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com/reto_db_gty6?sslmode=require"
engine = create_engine(DATABASE_URL)

# Cliente Open-Meteo con Cache y Retry
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# -------------------------------------------------
# 2. FUNCIONES DE REGISTRO
# -------------------------------------------------

def registrar_log(endpoint, estado, mensaje=None, proceso="SISTEMA"):
    """
    Inserta un log en la tabla logs_procesos usando la fecha/hora del servidor de la base de datos.
    
    Parámetros:
    - endpoint: string con la ruta del endpoint
    - estado: string ("EXITO", "ERROR", etc.)
    - mensaje: string opcional con detalle del log
    - proceso: string indicando el proceso que genera el log
    """
    query = text("""
        INSERT INTO logs_procesos (fecha, proceso, endpoint, estado, mensaje)
        VALUES (NOW(), :proceso, :endpoint, :estado, :mensaje)
    """)
    try:
        with engine.begin() as conn:
            conn.execute(query, {
                "proceso": proceso,
                "endpoint": endpoint,
                "estado": estado,
                "mensaje": mensaje
            })
    except Exception as e:
        print(f"Error guardando log: {e}")


# -------------------------------------------------
# 3. INICIALIZACIÓN GOOGLE EARTH ENGINE
# -------------------------------------------------
GEE_PROJECT_ID = '689397879813'
try:
    if os.path.exists('credentials.json'):
        credenciales = ee.ServiceAccountCredentials('', 'credentials.json')
        ee.Initialize(credenciales, project=GEE_PROJECT_ID)
    else:
        ee.Initialize(project=GEE_PROJECT_ID)
    print("GEE Inicializado correctamente")
except Exception as e:
    print(f"Error GEE: {e}")

# -------------------------------------------------
# 4. MAPEO HISTÓRICO
# -------------------------------------------------
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
# 5. FUNCIONES DE PROCESAMIENTO GEE
# -------------------------------------------------
def procesar_datos_gee(lat, lon):
    punto = ee.Geometry.Point([lon, lat])
    ahora = datetime.now(timezone.utc)

    # Topografía
    srtm = ee.Image('CGIAR/SRTM90_V4')
    topo = srtm.addBands(ee.Terrain.slope(srtm)).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=punto, scale=30
    ).getInfo() or {}

    # Suelo
    suelo_img = ee.Image.cat([
        ee.Image("projects/soilgrids-isric/clay_mean").select(['clay_0-5cm_mean']),
        ee.Image("projects/soilgrids-isric/phh2o_mean").select(['phh2o_0-5cm_mean']),
        ee.Image("projects/soilgrids-isric/soc_mean").select('soc_0-5cm_mean'),
        ee.Image("projects/soilgrids-isric/sand_mean").select('sand_0-5cm_mean')
    ])
    suelo = suelo_img.reduceRegion(reducer=ee.Reducer.mean(), geometry=punto, scale=250).getInfo() or {}

    # NDVI más reciente (último mes)
    modis = ee.ImageCollection("MODIS/061/MOD13Q1").select('NDVI')
    desde = (ahora - relativedelta(months=1)).strftime('%Y-%m-%d')
    hasta = ahora.strftime('%Y-%m-%d')

    ndvi_actual = modis.filterDate(desde, hasta).median().reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=punto,
        scale=250
    ).get('NDVI').getInfo()
    ndvi_actual = round(ndvi_actual * 0.0001, 3) if ndvi_actual is not None else 0

    # Lluvia anual
    lluvia_data = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterDate((ahora - timedelta(days=365)).strftime('%Y-%m-%d'), ahora.strftime('%Y-%m-%d')) \
        .sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=punto, scale=5000).getInfo() or {}

    def safe_div(val): return (val / 10) if val is not None else 0
    sand, clay = safe_div(suelo.get('sand_0-5cm_mean')), safe_div(suelo.get('clay_0-5cm_mean'))

    return {
        "topografia": {
            "elevacion_msnm": round(topo.get('elevation') or 0, 2),
            "pendiente_grados": round(topo.get('slope') or 0, 2)
        },
        "suelo": {
            "textura": {
                "arena": round(sand, 1),
                "limo": round(max(0, 100 - (sand + clay)), 1),
                "arcilla": round(clay, 1)
            },
            "ph_superficie": round(safe_div(suelo.get('phh2o_0-5cm_mean')), 2),
            "materia_organica_gkg": round(safe_div(suelo.get('soc_0-5cm_mean')), 2)
        },
        "clima_anual": {
            "precipitacion_acumulada_mm": round(lluvia_data.get('precipitation') or 0, 2)
        },
        "ndvi_actual": ndvi_actual  # <-- solo NDVI más reciente
    }

# -------------------------------------------------
# 6. ENDPOINT INICIAL
# -------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

# -------------------------------------------------
# 7. ENDPOINT GOOGLE ENGINE
# -------------------------------------------------

# FORMATO DE CONSULTA
"""
{
    "parcela_id": 101,
    "lat": -33.4489,
    "lon": -70.6693
}
"""

@app.route('/tierra', methods=['POST'])
def api_analisis():
    datos = request.get_json(force=True)
    endpoint_path = request.path
    if not datos or not all(k in datos for k in ["parcela_id", "lat", "lon"]):
        registrar_log(endpoint_path, "ERROR", "Faltan parametros", "ANALISIS_SUELO")
        return jsonify({"error": "Faltan parametros: parcela_id, lat, lon"}), 400
    
    try:
        resultado = procesar_datos_gee(datos['lat'], datos['lon'])
        query = text("""
            INSERT INTO suelo_parcela (parcela_id, fecha_consulta, latitud, longitud, datos_suelo)
            VALUES (:p_id, :fecha, :lat, :lon, :data)
        """)
        with engine.begin() as conn:
            conn.execute(query, {
                "p_id": datos["parcela_id"],
                "fecha": datetime.now(timezone.utc).replace(tzinfo=None),
                "lat": datos["lat"],
                "lon": datos["lon"],
                "data": json.dumps(resultado)  # <-- CAMBIO AQUÍ
            })
        registrar_log(endpoint_path, "EXITO", f"Suelo ID {datos['parcela_id']}", "ANALISIS_SUELO")
        return jsonify({"status": "Suelo procesado", "data": resultado}), 200
    except Exception as e:
        registrar_log(endpoint_path, "ERROR", str(e), "ANALISIS_SUELO")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# 8. ENDPOINT HISTORICO CLIMA DIARIO
# -------------------------------------------------

# FORMATO DE CONSULTA JSON
"""
{
    "parcela_id": 101,
    "lat": -33.4489,
    "lon": -70.6693,
    "inicio": "2024-01-01",
    "fin": "2024-01-15",
    "variables": [
        "temperatura",
        "humedad_relativa",
        "precipitacion"
    ]
}
"""

@app.route('/cargar_historico_daily', methods=['POST'])
def cargar_historico_daily():
    datos = request.get_json()
    endpoint_path = request.path
    
    if not datos or not all(k in datos for k in ["parcela_id", "lat", "lon", "inicio", "fin"]):
        return jsonify({"error": "Faltan parametros obligatorios"}), 400

    variables_solicitadas = [v for v in datos.get("variables", []) if v in MAPEO_API_DAILY]
    if not variables_solicitadas:
        return jsonify({"error": "No hay variables validas"}), 400

    try:
        api_vars = [MAPEO_API_DAILY[v] for v in variables_solicitadas]
        params = {
            "latitude": datos["lat"], 
            "longitude": datos["lon"],
            "start_date": datos["inicio"], 
            "end_date": datos["fin"],
            "daily": ",".join(api_vars), 
            "timezone": "UTC"
        }
        response = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=30).json()
        if "error" in response: 
            registrar_log(endpoint_path, "ERROR", response.get("reason"), "CARGA_HISTORICA")
            return jsonify({"error_api": response.get("reason")}), 400

        fechas = response["daily"]["time"]
        lista_historico = []

        # Preparamos la respuesta inmediata
        for i in range(len(fechas)):
            item = {"fecha": fechas[i]}
            for v in variables_solicitadas:
                valor = response["daily"][MAPEO_API_DAILY[v]][i]
                item[v] = round(float(valor), 3) if valor is not None else 0.0
            lista_historico.append(item)

        response_json = {"status": "Exito", "total_dias": len(fechas), "historico": lista_historico}

        # Guardado en DB en segundo plano
        def guardar_daily(endpoint_path):
            try:
                with engine.begin() as conn:
                    for i in range(len(fechas)):
                        columnas = ["parcela_id", "fecha", "tipo", "latitud", "longitud"]
                        valores_query = [
                            datos["parcela_id"],
                            fechas[i],   # <-- GUARDAR EXACTAMENTE DEL JSON
                            "diario",
                            datos["lat"],
                            datos["lon"]
                        ]
                        for v in variables_solicitadas:
                            valor = response["daily"][MAPEO_API_DAILY[v]][i]
                            valor_limpio = round(float(valor), 3) if valor is not None else 0.0
                            columnas.append(v)
                            valores_query.append(valor_limpio)
                        col_str = ", ".join(columnas)
                        placeholders = ", ".join([f":v{j}" for j in range(len(valores_query))])
                        dict_params = {f"v{j}": val for j, val in enumerate(valores_query)}
                        conn.execute(text(f"INSERT INTO clima_hist_parcela ({col_str}) VALUES ({placeholders})"), dict_params)
                registrar_log(endpoint_path, "EXITO", f"Cargados {len(fechas)} dias en DB", "CARGA_HISTORICA")
            except Exception as e:
                registrar_log(endpoint_path, "ERROR", str(e), "CARGA_HISTORICA")

        threading.Thread(target=guardar_daily, args=(endpoint_path,), daemon=True).start()
        return jsonify(response_json), 200

    except Exception as e:
        registrar_log(endpoint_path, "ERROR", str(e), "CARGA_HISTORICA")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# 9. ENDPOINT HISTORICO CLIMA MENSUAL
# -------------------------------------------------

# FORMATO DE CONSULTA JSON
"""
{
    "parcela_id": 101,
    "lat": -33.4489,
    "lon": -70.6693,
    "inicio": "2019-01-01",
    "fin": "2024-12-31",
    "variables": [
        "temperatura",
        "humedad_relativa",
        "precipitacion"
    ]
}
"""

@app.route('/cargar_historico_monthly', methods=['POST'])
def cargar_historico_monthly():
    datos = request.get_json()
    endpoint_path = request.path

    if not datos or not all(k in datos for k in ["parcela_id", "lat", "lon", "inicio", "fin"]):
        return jsonify({"error": "Faltan parametros obligatorios"}), 400

    MAPEO_API_HOURLY = {
        "temperatura": "temperature_2m",
        "humedad_relativa": "relative_humidity_2m",
        "humedad_suelo": "soil_moisture_0_to_7cm",
        "precipitacion": "precipitation",
        "evapotranspiracion": "et0_fao_evapotranspiration",
        "viento_velocidad": "wind_speed_10m",
        "viento_direccion": "wind_direction_10m"
    }

    variables_solicitadas = [v for v in datos.get("variables", []) if v in MAPEO_API_HOURLY]
    if not variables_solicitadas:
        return jsonify({"error": "No hay variables validas"}), 400

    api_vars = [MAPEO_API_HOURLY[v] for v in variables_solicitadas]

    try:
        params = {
            "latitude": datos["lat"],
            "longitude": datos["lon"],
            "start_date": datos["inicio"],
            "end_date": datos["fin"],
            "hourly": api_vars,
            "timezone": "UTC"
        }

        responses = openmeteo.weather_api("https://archive-api.open-meteo.com/v1/archive", params=params)
        response = responses[0]
        hourly = response.Hourly()

        df = pd.DataFrame({
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
        })

        for i, var in enumerate(api_vars):
            df[var] = hourly.Variables(i).ValuesAsNumpy()

        # Normalizamos fecha pero mantenemos UTC
        df['date'] = df['date'].dt.normalize()

        # Fechas inicio/fin TAMBIÉN en UTC
        fecha_inicio = pd.to_datetime(datos["inicio"], utc=True)
        fecha_fin = pd.to_datetime(datos["fin"], utc=True)

        df = df[(df['date'] >= fecha_inicio) & (df['date'] <= fecha_fin)]

        agg_dict = {v: 'mean' for v in api_vars}
        if "precipitacion" in variables_solicitadas:
            agg_dict[MAPEO_API_HOURLY["precipitacion"]] = 'sum'
        if "evapotranspiracion" in variables_solicitadas:
            agg_dict[MAPEO_API_HOURLY["evapotranspiracion"]] = 'sum'

        df_monthly = df.set_index('date').resample('MS').agg(agg_dict)

        df_monthly.rename(
            columns={v: k for k, v in MAPEO_API_HOURLY.items() if k in variables_solicitadas},
            inplace=True
        )

        df_monthly.index = df_monthly.index.strftime('%Y-%m-%d')

        historico = df_monthly.reset_index().rename(columns={"date": "fecha"}).to_dict(orient='records')

        def guardar_monthly(*_):
            try:
                with engine.begin() as conn:
                    for item in historico:
                        columnas = ["parcela_id", "fecha", "tipo", "latitud", "longitud"]
                        valores_query = [
                            datos["parcela_id"],
                            item["fecha"],   # <-- STRING JSON
                            "mensual",
                            datos["lat"],
                            datos["lon"]
                        ]

                        for v in variables_solicitadas:
                            valor = item[v]
                            valor_limpio = round(float(valor), 3) if valor is not None else 0.0
                            columnas.append(v)
                            valores_query.append(valor_limpio)

                        col_str = ", ".join(columnas)
                        placeholders = ", ".join([f":v{j}" for j in range(len(valores_query))])
                        dict_params = {f"v{j}": val for j, val in enumerate(valores_query)}

                        conn.execute(
                            text(f"INSERT INTO clima_hist_parcela ({col_str}) VALUES ({placeholders})"),
                            dict_params
                        )

                registrar_log("/cargar_historico_monthly", "EXITO", f"Cargados {len(historico)} meses en DB", "CARGA_HISTORICA")

            except Exception as e:
                registrar_log("/cargar_historico_monthly", "ERROR", str(e), "CARGA_HISTORICA")

        threading.Thread(target=guardar_monthly, args=(endpoint_path,), daemon=True).start()

        return jsonify({
            "status": "Exito",
            "total_dias": len(historico),
            "historico": historico
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------
# 11. MAIN
# -------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
