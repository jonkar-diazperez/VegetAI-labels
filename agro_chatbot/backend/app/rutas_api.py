from flask import Blueprint, request, jsonify
from llm import get_answer
from db import SesionLocal, Interaccion

api = Blueprint("api", __name__)

@api.route("/raiz_api", methods=["GET"])
def health():
    return jsonify({"status": "online", "agent": "CyberSecurity LLM v1.0"})

@api.route("/chat", methods=["POST"])
def chat():
    """
    {
    "pregunta": "¿Qué es un firewall?"
    }
    """
    data = request.get_json()
    pregunta = data.get("pregunta")

    if not pregunta:
        return jsonify({"error": "Es necesario introducir una pregunta"}), 400

    # 1. Obtener respuesta del LLM
    respuesta = get_answer(pregunta)

    # 2. Persistencia en Base de Datos con gestión segura de sesión
    sesion = SesionLocal()
    try:
        nueva_interaccion = Interaccion(pregunta=pregunta, respuesta=respuesta)
        sesion.add(nueva_interaccion)
        sesion.commit()
    except Exception as e:
        sesion.rollback()
        return jsonify({"error": f"Error al guardar en BD: {str(e)}"}), 500
    finally:
        sesion.close()

    return jsonify({
        "pregunta": pregunta,
        "respuesta": respuesta
    })

@api.route("/historial", methods=["GET"])
def historial():
    """Recupera las últimas 10 interacciones de la base de datos."""
    sesion = SesionLocal()
    try:
        items = sesion.query(Interaccion).order_by(Interaccion.timestamp.desc()).limit(10).all()
        resultado = [
            {"id": i.id, "pregunta": i.pregunta, "respuesta": i.respuesta, "fecha": i.timestamp}
            for i in items
        ]
        return jsonify(resultado)
    finally:
        sesion.close()
