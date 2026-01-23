from flask import Flask, request, jsonify
from ia_service import get_answer
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Endpoint de prueba para verificar que el servidor corre
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "El asistente AI esta activo", "service": "Flask"}), 200

# Endpoint principal de Chat
@app.route('/chat', methods=['POST'])
def chat():
    """
    Recibe un JSON con:
    {
    "user_email": "usuario@ejemplo.com",
    "message": "¿Cómo está la radiación hoy?"
    }
    """
    data = request.get_json()

    # Validación básica de datos
    if not data or 'message' not in data or 'user_email' not in data:
        return jsonify({"error": "Faltan campos obligatorios: user_email y message"}), 400

    user_email = data['user_email']
    question = data['message']
    try:
        # Llamada a la lógica de LangChain en ia_service.py
        # Usamos el email como session_id para que Postgres recupere su historial
        ai_response = get_answer(question, user_email)

        return jsonify({
        "user_email": user_email,
        "response": ai_response
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error en el motor AgroTech: {str(e)}"}), 500

if __name__ == '__main__':
    # debug=True para ver cambios en tiempo real
    app.run(debug=True, port=5000)