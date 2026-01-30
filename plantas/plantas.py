from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

api_key = os.getenv("PLANTNET_KEY")

PN_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={api_key}&lang=es"

@app.route('/identificar', methods=['POST'])
def identificar_planta():
    if 'image' not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400
    
    file = request.files['image']
    
    try:
        files = [('images', (file.filename, file.read()))]
        data = {'organs': ['auto']}
        
        res_pn = requests.post(PN_URL, files=files, data=data)

        if res_pn.status_code == 200:
            json_data = res_pn.json()
            best_match = json_data['results'][0]
            species = best_match['species']
            
            
            scientific_name = species.get('scientificNameWithoutAuthor')
            common_names = species.get('commonNames', [])
            
            return jsonify({
                "status": "success",
                "nombre_cientifico": scientific_name,
                "nombre_comun": common_names[0] if common_names else "No disponible",
                "otros_nombres": common_names[1:4],
                "precision": f"{round(best_match.get('score', 0) * 100, 2)}%"
            })
        else:
            return jsonify({"error": "Error de Pl@ntNet", "codigo": res_pn.status_code}), res_pn.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)