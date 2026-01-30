from flask import Flask
from flask_cors import CORS
from rutas_api import api

def crear_app():
    app = Flask(__name__)
    # Todas las rutas definidas en rutas_api.py se añaden a la aplicación
    app.register_blueprint(api)
    return app

app = crear_app()

CORS(app) 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)