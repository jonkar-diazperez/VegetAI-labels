from flask import Flask, request, jsonify
import requests
import token_auravant as token
import os
from dotenv import load_dotenv

load_dotenv()

def auravant_parcela(params:dict):
    try:
        TOKEN_API = token.get_token()
        if not TOKEN_API:
            return jsonify({"error": "Token no configurado"}), 500
        
        # Cabecera requerida para invocaciones a la API de Auravant
        url = os.getenv("AURAVANT_url") + "/agregarlote"
        headers = {
            "Authorization": f"Bearer {TOKEN_API}",
            "Content-Type": "application/x-www-form-urlencoded",
            "x-auth-s": os.getenv("AURAVANT_ESPACIO")
        }
        # LLamada a la API de Auravant
        print(f"Consultando: {url}...")
        api_response = requests.post(url, data=params, headers=headers)
        # Lanza una excepción si el status code es de error (4xx o 5xx)
        api_response.raise_for_status()
        print("API AURAVANT EJECUTADA")
        print("Resultado API:",api_response.json()['res'])
        print("Status API:",api_response.status_code)
        
        #print(api_response.json())
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

def consultar_fincas(campo_id:str):
    try:
        TOKEN_API = token.get_token()
        if not TOKEN_API:
            return jsonify({"error": "Token no configurado"}), 500
        # Cabecera requerida para invocaciones a la API de Auravant
        #url = f"https://livingcarbontech.auravant.com/api/getfields"
        url = os.getenv("AURAVANT_url") + "/getfields"
        headers = {
            "Authorization": f"Bearer {TOKEN_API}",
            "Content-Type": "application/x-www-form-urlencoded",
            "x-auth-s": os.getenv("AURAVANT_ESPACIO")
        }

        print(f"Consultando: {url}...")
        
        api_response = requests.get(url, headers=headers)
        api_response.raise_for_status()
        print("API AURAVANT EJECUTADA")
        print("Status API:",api_response.status_code)

        if api_response.status_code == 200:
            campos = api_response.json()
            #print(campos)
            # busqueda de campo en lista de campos del usuario
            campo_encontrado = token.obtener_campo_por_id(campos, campo_id)
            if campo_encontrado:
                #print("Campo:",campo_encontrado)
                return campo_encontrado, 200
            else:
                return jsonify({"Mensaje": "Campo no encontrado"}), 210
        elif api_response.status_code == 404:
            print("❌ Error 404: La ruta /api/v1/fields no es correcta para tu tipo de cuenta.")
        else:
            print(f"❌ Error {api_response.status_code}: {api_response.text}")

    except Exception as e:
        return jsonify({"Error": f"❌ Error en llamada AURAVANT: {e}"}), 404