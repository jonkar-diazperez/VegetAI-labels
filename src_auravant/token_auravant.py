import requests
import json
from dotenv import load_dotenv
import os

# Variable para guardar el token en memoria
TOKEN_CACHE = None

load_dotenv()
# Configuración
USUARIO = os.getenv("AURAVANT_USUARIO")
PASSWORD = os.getenv("AURAVANT_PASSWORD")
ESPACIO = os.getenv("AURAVANT_ESPACIO")
SUBDOMAIN = os.getenv("AURAVANT_SUBDOMAIN")
EXTENSION_ID = os.getenv("AURAVANT_CLIENT_ID")
SECRET = os.getenv("AURAVANT_SECRET")

def get_token():
    global TOKEN_CACHE
    
    # Si ya tenemos el token, no pedimos otro
    if TOKEN_CACHE:
        return TOKEN_CACHE
    
    # OBTENER TOKEN
    auth_url = "https://livingcarbontech.auravant.com/api/auth"
    auth_data = {"username": USUARIO, "password": PASSWORD, "s": ESPACIO}
    
    try:
        auth_resp = requests.post(auth_url, data=auth_data)
        auth_resp.raise_for_status()
        TOKEN_CACHE = auth_resp.json().get("token")
        print("✅ Autenticación correcta.")
        return TOKEN_CACHE
    except Exception as e:
        print(f"❌ Error obteniendo token AURAVANT: {e}")
        return
    

def obtener_campo_por_id(data, field_id_buscado):
    # Convertimos el ID a string por si el usuario lo pasa como número
    id_str = str(field_id_buscado)
    print("Parcela a buscar:", id_str)
    # Accedemos al diccionario de granjas 
    farms = data.get('user', {}).get('farms', {})
    #print("Campos a buscar:", farms)
    # Iteramos por cada granja para buscar en sus campos 
    for farm_id, farm_info in farms.items():
        fields = farm_info.get('fields', {})
        #print("Parcelas:", fields.keys())
        # Si el ID del campo existe en esta granja, lo devolvemos 
        if id_str in fields.keys():
            print("Campo encontrado:", fields[id_str])
            return fields[id_str]
            
    return None # Si no se encuentra en ninguna granja

