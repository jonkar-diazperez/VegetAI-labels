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
# 2. INFORMACIÓN DE PARCELA (FIJA)
# -------------------------------------------------
PARCELA_INFO = {
    "lat": -33.1951,
    "lon": -70.7292,
    "parcela_id": 784112,
    "nombre_parcela": "Parcela 20343",
    "finca_id": 227752
}

# -------------------------------------------------
# 3. MAPEO VARIABLES (USUARIO → DAILY OPEN-METEO)
# -------------------------------------------------
MAPEO_API_DAILY = {
    "temperatura": "temperature_2m_mean",
    "humedad_relativa": "relative_humidity_2m_mean",
    "humedad_suelo": "soil_moisture_0_1cm_mean",
    "precipitacion": "precipitation_sum",
    "viento_velocidad": "windspeed_10m_mean",
    "viento_direccion": "winddirection_10m_dominant",
    "evapotranspiracion": "et0_fao_evapotranspiration"
}

# -------------------------------------------------
# 4. FLASK
# -------------------------------------------------
app = Flask(__name__)

# -------------------------------------------------
# 5. ENDPOINT HISTÓRICO DAILY
# -------------------------------------------------

# Formato de consulta (POST)
"""
{
  "inicio": "1951-01-01",
  "fin": "1951-01-30",
  "variables": [
    "temperatura"
  ]
}
"""
@app.route('/cargar_historico', methods=['POST'])
def cargar_historico():
    datos = request.get_json()

    if not datos:
        return jsonify({"error": "No se recibió JSON"}), 400

    fecha_inicio = datos.get("inicio")
    fecha_fin = datos.get("fin")
    variables_solicitadas = datos.get("variables", [])

    if not fecha_inicio or not fecha_fin or not variables_solicitadas:
        return jsonify({"error": "Faltan parámetros"}), 400

    # Validar variables
    variables_validas = [v for v in variables_solicitadas if v in MAPEO_API_DAILY]
    if not variables_validas:
        return jsonify({"error": "Variables no válidas"}), 400

    try:
        api_vars = [MAPEO_API_DAILY[v] for v in variables_validas]

        api_url = "https://archive-api.open-meteo.com/v1/archive"

        params = {
            "latitude": PARCELA_INFO["lat"],
            "longitude": PARCELA_INFO["lon"],
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "daily": ",".join(api_vars),
            "timezone": "UTC"
        }

        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()

        if "error" in data:
            return jsonify({"error_api": data.get("reason")}), 400

        daily = data["daily"]
        fechas = daily["time"]

        # SQL dinámico
        columnas_sql = ", ".join(variables_validas)
        placeholders = ", ".join([f":{v}" for v in variables_validas])

        query = text(f"""
            INSERT INTO registros_clima (
                fecha,
                parcela_id,
                nombre_parcela,
                finca_id,
                latitud,
                longitud,
                {columnas_sql}
            )
            VALUES (
                :fecha,
                :parcela_id,
                :nombre_parcela,
                :finca_id,
                :latitud,
                :longitud,
                {placeholders}
            )
        """)

        registros_db = []
        historico_json = []

        for i in range(len(fechas)):
            fila_db = {
                "fecha": fechas[i],
                "parcela_id": PARCELA_INFO["parcela_id"],
                "nombre_parcela": PARCELA_INFO["nombre_parcela"],
                "finca_id": PARCELA_INFO["finca_id"],
                "latitud": PARCELA_INFO["lat"],
                "longitud": PARCELA_INFO["lon"]
            }

            punto = {"fecha": fechas[i]}

            for var in variables_validas:
                valor = daily[MAPEO_API_DAILY[var]][i]
                fila_db[var] = valor
                punto[var] = valor

            registros_db.append(fila_db)
            historico_json.append(punto)

        # Inserción en BBDD
        with engine.begin() as conn:
            conn.execute(query, registros_db)

        return jsonify({
            "status": "Éxito",
            "parcela": PARCELA_INFO["nombre_parcela"],
            "periodo": {
                "inicio": fecha_inicio,
                "fin": fecha_fin
            },
            "variables": variables_validas,
            "total_dias": len(historico_json),
            "historico": historico_json
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------
# 6. EJECUCIÓN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
