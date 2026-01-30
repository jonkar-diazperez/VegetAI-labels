import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuraración de la conexion a OpenMeteo
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

@app.route('/')
def home():
    return {"estado": "OK", "info": "Envia GET al endpoint '/consultar_datos' con parametros de la parcela"}

@app.route('/consultar_datos', methods=['GET'])
def obtener_clima_por_dias():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    dias_atras = request.args.get('days', default=7, type=int)
    
    # Validar que lat y lon existan
    if lat is None or lon is None:
        return jsonify({"error": "Faltan parametros 'lat' o 'lon'"}), 400
    
    try:
        # Calcular fechas
        hoy = datetime.now()
        fecha_inicio = hoy - timedelta(days=dias_atras)
        
        # Formatear a string YYYY-MM-DD
        str_hoy = hoy.strftime('%Y-%m-%d')
        str_inicio = fecha_inicio.strftime('%Y-%m-%d')

        # Parámetros de la API
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["temperature_2m_mean", "relative_humidity_2m_mean", "precipitation_probability_mean", "wind_speed_10m_mean", "winddirection_10m_dominant", "et0_fao_evapotranspiration_sum"],
            "timezone": "auto",
            "start_date": str_inicio,
            "end_date": str_hoy,
        }
        
        # Llamada a la API
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Procesamiento de datos por dia
        daily = response.Daily()
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
        
        # Crear DataFrame con todas las columnas
        df = pd.DataFrame(data=data_dict)

        # Convertir fecha a string para JSON
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        
        # Opcional: Redondear valores numéricos para un JSON más limpio
        df = df.round(2)
        resultado = df.to_dict(orient='records')

        return jsonify({
            "status": "ok",
            "location": {"lat": lat, "lon": lon},
            "data": resultado
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)