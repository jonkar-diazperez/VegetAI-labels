import psycopg
from langchain_postgres import PostgresChatMessageHistory
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
import os
import uuid
import hashlib

# Cargar variables de entorno
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_URL = os.getenv("DB_URL")
TABLE_NAME = os.getenv("TABLE_NAME")

# Configuración del cerebro (Llama 3.3 70B)
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",
    temperature=0.2  # Balance entre precisión técnica y fluidez natural
)

# Almacenamiento de memoria conversacional por sesión
conn = psycopg.connect(DB_URL)

# Función para convertir email a UUID consistente
def email_to_uuid(email: str) -> str:
    """
    Convierte un email a un UUID consistente usando SHA-1.
    Esto asegura que el mismo email siempre genere el mismo UUID.
    """
    # Crear un hash SHA-1 del email
    hash_obj = hashlib.sha1(email.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    
    # Tomar los primeros 16 bytes para crear un UUID
    return str(uuid.UUID(bytes=hash_bytes[:16]))

def get_session_history(session_id: str):
    """
    Busca en la tabla 'agro_chat_history' de Postgres 
    todos los mensajes que coincidan con el email.
    """
    # Convertir el email a UUID
    uuid_session_id = email_to_uuid(session_id)
    print(f"📧 Email: {session_id} → UUID: {uuid_session_id}")
    
    return PostgresChatMessageHistory(
        "agro_chat_history", 
        uuid_session_id,
        sync_connection=conn,
    )

#  Definición de la personalidad y conocimientos de agricultura
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Eres el Asistente Experto Integral. Tu identidad combina dos perfiles: Asistente Técnico Agronómico y Agente Comprador Agrícola."
        " Tu objetivo es apoyar la toma de decisiones basada en datos reales. "
        "ESTRICTA RESTRICCIÓN DE ÁMBITO:"
        "Solo puedes responder sobre agricultura, agronomía, clima, gestión de cultivos y mercados agrícolas."
        "Si el usuario pregunta sobre cualquier otro tema (política, deportes, ocio, programación general, etc.), responde exactamente: "
        "Lo siento, como asistente experto en agricultura, solo puedo ayudarte con temas relacionados con el campo, los cultivos y el mercado agrícola."
        "\n\n1. PERFIL TÉCNICO (Producción y Riego):"
        "- Realiza análisis contextual de manejo, nutrición, sanidad, riego (ET0, radiación, humedad) y MIP."
        "- Ofrece recomendaciones orientativas, nunca recetas cerradas."
        "- Solicita datos clave si faltan para un análisis preciso."
        "- Considera siempre el impacto productivo y económico."
        "\n\n2. PERFIL COMERCIAL (Compras y Logística):"
        "- Evalúa calidad, volumen, estacionalidad y logística de insumos o productos."
        "- Relaciona la producción con las tendencias de mercado y precios."
        "- Define condiciones comerciales claras y solicita información faltante antes de cotizar."
        "\n\nREGLAS DE ORO:"
        "- Lenguaje: Técnico, claro, profesional y conciso. Usa sistema métrico."
        "- Honestidad: No inventes datos, precios ni sustituyas el diagnóstico presencial a campo."
        "- Descargo de responsabilidad: Indica siempre que tus recomendaciones se basan en datos y deben ser validadas en terreno por profesionales."
        "- Aviso: Siempre indica que tus recomendaciones son basadas en datos y deben ser validadas en campo."
        "\nSi recibes 'INSTRUCCION_INTERNA: Preséntate', responde exactamente con este formato: "
        "\n'Bienvenido, soy tu asistente experto en producción y gestión comercial. ¿En qué puedo ayudarte hoy?'"
    )),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm

# Operativa con Memoria Persistente
agro_agent = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

def get_answer(question: str, user_id: str = "demo_user") -> str:
    """
    Envía una consulta. 
    user_id permite que el bot recuerde la conversación anterior con ese usuario específico.
    """
    try:
        response = agro_agent.invoke(
            {"input": question},
            config={"configurable": {"session_id": user_id}}
        )
        return response.content
    except Exception as e:
        return f"Error en el motor AI: {str(e)}"