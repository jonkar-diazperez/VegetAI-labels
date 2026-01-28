from flask import Flask, jsonify, request
import requests
from sqlalchemy import create_engine, text, URL

# -------------------------------------------------
# 1. CONFIGURACIÓN CONEXIÓN POSTGRES
# -------------------------------------------------
db_url = URL.create(
    drivername="postgresql",
    username="admin",
    password="HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q",
    host="dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com",
    port=5432,
    database="reto_db_gty6"
)
engine = create_engine(db_url)

# -------------------------------------------------
# 2. MAPEO VARIABLES (CORREGIDO PARA ARCHIVE API)
# -------------------------------------------------
# Nota: La API de Archive usa nombres ligeramente distintos a la de Forecast.
MAPEO_API_DAILY = {
    "temperatura": "temperature_2m_mean",
    "humedad_relativa": "relative_humidity_2m_mean",
    "humedad_suelo": "soil_moisture_0_to_7cm_mean",    # En Archive se usa 0_to_7cm
    "precipitacion": "precipitation_sum",
    "viento_velocidad": "wind_speed_10m_max",         # Nombre correcto en Archive
    "viento_direccion": "wind_direction_10m_dominant",
    "evapotranspiracion": "et0_fao_evapotranspiration"
}

app = Flask(__name__)

# -------------------------------------------------
# 3. ENDPOINT HISTÓRICO DAILY
# -------------------------------------------------

@app.route('/cargar_historico', methods=['POST'])
def cargar_historico():
    datos = request.get_json()

    if not datos:
        return jsonify({"error": "No se recibió JSON"}), 400

    parcela_id = datos.get("parcela_id")
    lat = datos.get("lat")
    lon = datos.get("lon")
    fecha_inicio = datos.get("inicio")
    fecha_fin = datos.get("fin")
    variables_solicitadas = datos.get("variables", [])

    campos_obligatorios = ["parcela_id", "lat", "lon", "inicio", "fin"]
    faltantes = [f for f in campos_obligatorios if datos.get(f) is None]
    
    if faltantes or not variables_solicitadas:
        return jsonify({"error": f"Faltan parámetros: {', '.join(faltantes) if faltantes else 'variables'}"}), 400

    variables_validas = [v for v in variables_solicitadas if v in MAPEO_API_DAILY]
    if not variables_validas:
        return jsonify({"error": "Variables solicitadas no soportadas"}), 400

    try:
        # 1. Llamada a la API de Open-Meteo
        api_vars = [MAPEO_API_DAILY[v] for v in variables_validas]
        api_url = "https://archive-api.open-meteo.com/v1/archive"

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "daily": ",".join(api_vars),
            "timezone": "UTC"
        }

        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()

        # Si la API devuelve un error (como el que viste antes)
        if "error" in data:
            return jsonify({
                "error_api_open_meteo": data.get("reason"),
                "detalle": "Revisa si las variables o las fechas son correctas para el archivo histórico."
            }), 400

        daily_data = data["daily"]
        fechas = daily_data["time"]

        # 2. Preparar SQL Dinámico
        columnas_sql = ", ".join(variables_validas)
        placeholders = ", ".join([f":{v}" for v in variables_validas])

        query = text(f"""
            INSERT INTO registros_clima (
                fecha, parcela_id, latitud, longitud, {columnas_sql}
            )
            VALUES (
                :fecha, :parcela_id, :latitud, :longitud, {placeholders}
            )
        """)

        registros_db = []
        historico_json = []

        for i in range(len(fechas)):
            fila_db = {
                "fecha": fechas[i],
                "parcela_id": parcela_id,
                "latitud": lat,
                "longitud": lon
            }
            punto_json = {"fecha": fechas[i]}

            for var in variables_validas:
                # Obtenemos el valor de la API usando el mapeo
                valor = daily_data[MAPEO_API_DAILY[var]][i]
                fila_db[var] = valor
                punto_json[var] = valor

            registros_db.append(fila_db)
            historico_json.append(punto_json)

        # 3. Inserción en Base de Datos
        with engine.begin() as conn:
            conn.execute(query, registros_db)

        return jsonify({
            "status": "Éxito",
            "parcela_id": parcela_id,
            "periodo": {"inicio": fecha_inicio, "fin": fecha_fin},
            "total_dias": len(historico_json),
            "historico": historico_json
        })

    except Exception as e:
        return jsonify({"error": "Error interno en el servidor", "detalle": str(e)}), 500

if __name__ == "__main__":
    # Mantener debug=False si el proceso se queda bloqueado en Windows
    app.run(host="0.0.0.0", port=5001, debug=False)