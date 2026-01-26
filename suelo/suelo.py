import os
import ee
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
GEE_PROJECT_ID = os.getenv('GEE_PROJECT_ID')

app = Flask(__name__)

# --- INICIALIZACIÓN ROBUSTA ---
try:
    if os.path.exists('credentials.json'):
        credenciales = ee.ServiceAccountCredentials('', 'credentials.json')
        ee.Initialize(credenciales, project=GEE_PROJECT_ID)
        print("✅ GEE inicializado con Service Account")
    else:
        ee.Initialize(project=GEE_PROJECT_ID)
        print("✅ GEE inicializado con credenciales locales")
except Exception as e:
    print(f"❌ Error crítico de GEE: {e}")

def procesar_datos_gee(lat, lon):
    punto = ee.Geometry.Point([lon, lat])
    ahora = datetime.now()
    
    # 1. TOPOGRAFÍA (SRTM)
    srtm = ee.Image('CGIAR/SRTM90_V4')
    pendiente = ee.Terrain.slope(srtm)
    topo = srtm.addBands(pendiente).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=punto, scale=30
    ).getInfo() or {} # Si es None, devuelve dict vacío

    # 2. SUELO (SoilGrids)
    suelo_img = ee.Image.cat([
        ee.Image("projects/soilgrids-isric/clay_mean").select(['clay_0-5cm_mean', 'clay_60-100cm_mean']),
        ee.Image("projects/soilgrids-isric/phh2o_mean").select(['phh2o_0-5cm_mean', 'phh2o_60-100cm_mean']),
        ee.Image("projects/soilgrids-isric/soc_mean").select('soc_0-5cm_mean'),
        ee.Image("projects/soilgrids-isric/sand_mean").select('sand_0-5cm_mean')
    ])
    suelo = suelo_img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=punto, scale=250
    ).getInfo() or {}

    # 3. HISTORIAL NDVI (MODIS)
    historial_ndvi = {}
    modis = ee.ImageCollection("MODIS/061/MOD13Q1").select('NDVI')
    
    for y in range(ahora.year - 5, ahora.year):
        inicio, fin = f"{y}-01-01", f"{y}-12-31"
        # .get('NDVI') puede devolver None, manejamos con getInfo()
        val_raw = modis.filterDate(inicio, fin).median().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=punto, scale=250
        ).get('NDVI').getInfo()
        historial_ndvi[str(y)] = round(val_raw * 0.0001, 3) if val_raw is not None else 0

    # 4. CLIMA (CHIRPS)
    lluvia_data = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
        .filterDate((ahora - timedelta(days=365)).strftime('%Y-%m-%d'), ahora.strftime('%Y-%m-%d')) \
        .sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=punto, scale=5000).getInfo() or {}

    # --- FORMATEO SEGURO (Previene error NoneType / int) ---
    def safe_div(val, divisor=10):
        return (val / divisor) if val is not None else 0

    sand = safe_div(suelo.get('sand_0-5cm_mean'))
    clay = safe_div(suelo.get('clay_0-5cm_mean'))
    silt = max(0, 100 - (sand + clay)) if (sand + clay) > 0 else 0
    
    ph_sup = safe_div(suelo.get('phh2o_0-5cm_mean'))
    ph_prof = safe_div(suelo.get('phh2o_60-100cm_mean'))
    soc = safe_div(suelo.get('soc_0-5cm_mean'))

# --- RETORNO SEGURO ---
    # Usamos (valor or 0) para asegurar que round() siempre reciba un número
    return {
        "coordenadas": {"lat": lat, "lon": lon},
        "topografia": {
            "elevacion_msnm": round(topo.get('elevation') or 0, 2),
            "pendiente_grados": round(topo.get('slope') or 0, 2)
        },
        "suelo": {
            "textura": {
                "arena": round(sand or 0, 1), 
                "limo": round(silt or 0, 1), 
                "arcilla": round(clay or 0, 1)
            },
            "ph_superficie": round(ph_sup or 0, 2),
            "ph_profundidad": round(ph_prof or 0, 2),
            "materia_organica_gkg": round(soc or 0, 2)
        },
        "clima": {
            "precipitacion_anual_mm": round(lluvia_data.get('precipitation') or 0, 2)
        },
        "productividad_ndvi": historial_ndvi
    }

@app.route('/analisis', methods=['POST'])
def api_analisis():
    # force=True permite que funcione aunque el cliente no envíe el header JSON
    datos = request.get_json(force=True)
    
    if not datos or 'lat' not in datos or 'lon' not in datos:
        return jsonify({"error": "El cuerpo JSON debe contener 'lat' y 'lon'"}), 400
    
    try:
        resultado = procesar_datos_gee(datos['lat'], datos['lon'])
        return jsonify(resultado), 200
    except Exception as e:
        # Esto capturará cualquier error de lógica interna
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # host='0.0.0.0' es vital para Docker
    app.run(host='0.0.0.0', port=5002, debug=True)