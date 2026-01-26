import requests
import json
from dotenv import load_dotenv
import os

# Variable para guardar el token en memoria
TOKEN_CACHE = None

load_dotenv()
# Configuración
USUARIO = os.getenv("USUARIO")
PASSWORD = os.getenv("PASSWORD")
ESPACIO = os.getenv("ESPACIO")
SUBDOMAIN = os.getenv("SUBDOMAIN")
EXTENSION_ID = os.getenv("CLIENT_ID")
SECRET = os.getenv("SECRET")

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
        print("✅ Autenticación exitosa.")
        return TOKEN_CACHE
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return
    
def consultar_fincas():
    token = get_token()
    url = f"https://livingcarbontech.auravant.com/api/getfields"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "x-auth-s": ESPACIO
    }

    print(f"Consultando: {url}...")
    
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        campos = response.json()
        print(f"✅ Éxito. Se encontraron {len(campos)} elementos.")
                
    elif response.status_code == 404:
        print("❌ Error 404: La ruta /api/v1/fields no es correcta para tu tipo de cuenta.")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


consultar_fincas()
