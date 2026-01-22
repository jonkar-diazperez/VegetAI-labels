from flask import Flask, request, jsonify
from dotenv import load_dotenv
import pandas as pd
import os
import requests
import api_auravant as aur

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route("/", methods = ['GET'])
def main():
    return "API de aplicación campos agrícolas"

# 1. Llamada a GROQ para obtener respuesta a partir del prompt introducido por el usuario
@app.route("/agregar_parcela", methods = ['POST'])
def agregar_parcela():
    """{'data': [
        "nombre de la parcela",
        "POLYGON((-71.14 -34.65, -71.14 -34.6571,-71.13 -34.655, -71.13 -34.65,-71.14 -34.65))",
        "nombre del campo donde está la parcela"]}"""  
    try:
        parcela = request.get_json()

        if not parcela or 'data' not in parcela:
            return jsonify({"Error":"No se han proporcionado datos"}), 400
        #print(parcela['data'])
        parcela_data = parcela.get("data", None) 
        print("----------------------", parcela_data)
        parcela_nueva = {
            "nombre" : parcela_data[0],
            "shape" : parcela_data[1],
            "nombrecampo" : parcela_data[2]
        }
        print(parcela_nueva)
        response_api, response_code = aur.auravant_parcela(parcela_nueva)
        print("Resultado llamada API:",response_api, response_code)
        if response_code > 200:
            return jsonify({"Error":"Error en llamada API."}), response_code
        else: 
            return response_api, response_code
        
    except ValueError:
        return jsonify({"Error":"No se han proporcionado datos válidos"}), 400   
    except Exception as e:
        return jsonify({"Error": f"Se ha producido un error ----- {e}"}), 500 


app.run(host="0.0.0.0", port=5000)
