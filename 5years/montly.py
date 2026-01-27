import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Configuración de la conexion a OpenMeteo
cache_session = requests_cache.CachedSession('.cache', expire_after = -1) # Cache permanente para datos históricos
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# 2. Parámetros de ubicación (Ejemplo: Santiago de Chile)
#lat, lon = -33.4489, -70.6693

@app.route('/')
def home():
    return {"estado": "OK", "info": "Envia GET al endpoint '/5years_history' con parametros de la parcela"}

@app.route('/5years_history', methods=['GET'])
def obtener_hist_5years():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    
    # Validar que lat y lon existan
    if lat is None or lon is None:
        return jsonify({"error": "Faltan parametros 'lat' o 'lon'"}), 400
    
    try:
        # Fecha de hoy
        hoy = datetime.now()

        # Calcular hace exactamente 5 años
        fecha_inicio = hoy - relativedelta(years=5)
        
        # Formatear a string YYYY-MM-DD
        str_hoy = hoy.strftime('%Y-%m-%d')
        str_inicio = fecha_inicio.strftime('%Y-%m-%d')
        
        # Parámetros de la API

        url = "https://archive-api.open-meteo.com/v1/archive" # URL correcta para datos históricos reales
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": str_inicio,
            "end_date": str_hoy,
            "hourly": [
                "temperature_2m", 
                "relative_humidity_2m", 
                "soil_moisture_0_to_7cm", 
                "precipitation",
                "et0_fao_evapotranspiration", 
                "wind_speed_10m", 
                "wind_direction_10m"
            ],
            "timezone": "auto"
        }

        # Petición a la API
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Procesamiento de datos horarios
        hourly = response.Hourly()
        hourly_data = {
            "date": pd.date_range(
                start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
                end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
                freq = pd.Timedelta(seconds = hourly.Interval()),
                inclusive = "left"
            )
        }

        # Extraer variables (el índice debe coincidir con el orden en 'params')
        hourly_data["temp"] = hourly.Variables(0).ValuesAsNumpy()
        hourly_data["hum_rel"] = hourly.Variables(1).ValuesAsNumpy()
        hourly_data["hum_suelo"] = hourly.Variables(2).ValuesAsNumpy()
        hourly_data["precip"] = hourly.Variables(3).ValuesAsNumpy()
        hourly_data["evapo"] = hourly.Variables(4).ValuesAsNumpy()
        hourly_data["viento_vel"] = hourly.Variables(5).ValuesAsNumpy()
        hourly_data["viento_dir"] = hourly.Variables(6).ValuesAsNumpy()

        df = pd.DataFrame(data = hourly_data)

        # Agrupación por Mes
        # Convertimos la fecha a formato mes-año y promediamos (o sumamos en caso de lluvia)
        df['date'] = df['date'].dt.tz_convert('America/Santiago')
        df_mensual = df.set_index('date').resample('MS').agg({
            'temp': 'mean',
            'hum_rel': 'mean',
            'hum_suelo': 'mean',
            'precip': 'sum',      # La lluvia se suma
            'evapo': 'sum',       # La evapotranspiración suele sumarse mensualmente
            'viento_vel': 'mean',
            'viento_dir': 'mean'
        })
        # para que el JSON sea legible y no falle con objetos Timestamp
        df_mensual.index = df_mensual.index.strftime('%Y-%m-%d')
        
        # Convertimos el DataFrame a una lista de diccionarios
        datos_formateados = df_mensual.reset_index().to_dict(orient='records')
        
        return jsonify({
            "status": "ok",
            "location": {"lat": lat, "lon": lon},
            "data": datos_formateados
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    #app.run(debug=True, host='0.0.0.0', port=5001)
    
    # Render asigna un puerto en la variable de entorno PORT
    port = int(os.environ.get('PORT', 5001))
    # Importante: host='0.0.0.0' es obligatorio en Docker/Render
    app.run(debug=False, host='0.0.0.0', port=port)