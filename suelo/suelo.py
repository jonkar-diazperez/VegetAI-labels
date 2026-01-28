import os
import ee
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy


GEE_PROJECT_ID = '689397879813'


DATABASE_URL = "postgresql://admin:HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q@dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com/reto_db_gty6?sslmode=require"

app = Flask(__name__)

# --- CONFIGURACIÓN DE BASE DE DATOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración necesaria para conectar con Render desde local (SSL)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "sslmode": "require"
    },
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

# --- MODELO DE LA TABLA ---
class RegistroAnalisis(db.Model):
    __tablename__ = 'registros_gee'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_consulta = db.Column(db.DateTime, default=datetime.utcnow)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    datos_completos = db.Column(db.JSON, nullable=False) 

# --- INICIALIZACIÓN DE GEE ---
try:
    if os.path.exists('credentials.json'):
        credenciales = ee.ServiceAccountCredentials('', 'credentials.json')
        ee.Initialize(credenciales, project=GEE_PROJECT_ID)
        print("✅ GEE inicializado con Service Account")
    else:
        # Esto intentará usar el login previo de 'earthengine authenticate'
        ee.Initialize(project=GEE_PROJECT_ID)
        print("✅ GEE inicializado con credenciales locales")
except Exception as e:
    print(f"❌ Error crítico de GEE: {e}")

# --- FUNCIÓN DE PROCESAMIENTO ---
def procesar_datos_gee(lat, lon):
    punto = ee.Geometry.Point([lon, lat])
    ahora = datetime.now()
    
    # 1. Topografía
    srtm = ee.Image('CGIAR/SRTM90_V4')
    pendiente = ee.Terrain.slope(srtm)
    topo = srtm.addBands(pendiente).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=punto, scale=30
    ).getInfo() or {}

    # 2. Suelo
    suelo_img = ee.Image.cat([
        ee.Image("projects/soilgrids-isric/clay_mean").select(['clay_0-5cm_mean', 'clay_60-100cm_mean']),
        ee.Image("projects/soilgrids-isric/phh2o_mean").select(['phh2o_0-5cm_mean', 'phh2o_60-100cm_mean']),
        ee.Image("projects/soilgrids-isric/soc_mean").select('soc_0-5cm_mean'),
        ee.Image("projects/soilgrids-isric/sand_mean").select('sand_0-5cm_mean')
    ])
    suelo = suelo_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=punto, scale=250
    ).getInfo() or {}

    # 3. Historial NDVI
    historial_ndvi = {}
    modis = ee.ImageCollection("MODIS/061/MOD13Q1").select('NDVI')
    for y in range(ahora.year - 5, ahora.year):
        inicio, fin = f"{y}-01-01", f"{y}-12-31"
        val_raw = modis.filterDate(inicio, fin).median().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=punto, scale=250
        ).get('NDVI').getInfo()
        historial_ndvi[str(y)] = round(val_raw * 0.0001, 3) if val_raw is not None else 0

    # 4. Clima
    lluvia_data = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterDate((ahora - timedelta(days=365)).strftime('%Y-%m-%d'), ahora.strftime('%Y-%m-%d')) \
        .sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=punto, scale=5000).getInfo() or {}

    def safe_div(val): return (val / 10) if val is not None else 0
    sand = safe_div(suelo.get('sand_0-5cm_mean'))
    clay = safe_div(suelo.get('clay_0-5cm_mean'))

    return {
        "coordenadas": {"lat": lat, "lon": lon},
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
        "clima": {
            "precipitacion_anual_mm": round(lluvia_data.get('precipitation') or 0, 2)
        },
        "productividad_ndvi": historial_ndvi
    }

# --- ENDPOINT ---
@app.route('/tierra', methods=['POST'])
def api_analisis():
    datos = request.get_json(force=True)
    if not datos or 'lat' not in datos or 'lon' not in datos:
        return jsonify({"error": "Faltan lat/lon"}), 400
    
    try:
        resultado = procesar_datos_gee(datos['lat'], datos['lon'])
        
        # Guardar en Base de Datos
        nuevo_registro = RegistroAnalisis(
            lat=datos['lat'],
            lon=datos['lon'],
            datos_completos=resultado
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        
        resultado['db_id'] = nuevo_registro.id
        return jsonify(resultado), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- INICIO ---
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("✅ Conexión exitosa a OREGON (Render) y tabla verificada")
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            
    app.run(host='0.0.0.0', port=5002, debug=True)