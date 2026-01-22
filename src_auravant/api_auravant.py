from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env al entorno de Python
load_dotenv()

# Acceder al token usando os.getenv
# El segundo parámetro es un valor por defecto si no encuentra la variable
TOKEN_API = os.getenv("AURAVANT_token")
URL_API = os.getenv("AURAVANT_url")

def auravant_parcela(params:dict):
    try:
        if not TOKEN_API:
            return jsonify({"error": "Token no configurado"}), 500
        
        # Ejemplo de cómo usarlo en una cabecera (header)
        headers = {
            "Authorization": f"Bearer {TOKEN_API}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        # Aquí iría tu lógica de requests.get(url, headers=headers)
        api_response = requests.post(URL_API + "/agregarlote", data=params, headers=headers)
        # Lanza una excepción si el status code es de error (4xx o 5xx)
        api_response.raise_for_status()
        print("API AURAVANT EJECUTADA")
        print("Resultado API:",api_response.json()['res'])
        print("Status API:",api_response.status_code)
        
        print(api_response.json())
        return api_response.json(), 200
        '''
        if api_response['res'] == 'ok':
            print(api_response.json())
            return jsonify(api_response.json()), 200
        else:    
            return jsonify({"mensaje": "Error en ejecución /agregarlote"}), 500
        '''
    except Exception as e:
        return jsonify({"Error": f"Error en llamada AURAVANT: {e}"}), 500
