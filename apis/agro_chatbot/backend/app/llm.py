from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from config_env import Config

# 1. Configuración del cerebro de AgroTech (Llama 3.3 70B)
llm = ChatGroq(
    groq_api_key=Config.GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.3  # Balance entre precisión técnica y fluidez natural
)

# 2. Definición de la personalidad y conocimientos de AgroTech
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Eres el Asistente Experto de AgroTech, una plataforma avanzada de gestión de cultivos y predicción climática. "
        "Tu objetivo es ayudar a agricultores e ingenieros a tomar decisiones basadas en datos. "
        "\n\nREGLAS DE RESPUESTA:"
        "\n1. Análisis Técnico: Interpreta variables como ET0 (Evapotranspiración), radiación solar y humedad."
        "\n2. Contexto de Cultivo: Sugiere acciones según el estado fenológico y las predicciones."
        "\n3. Estilo: Sé profesional, directo y utiliza unidades de medida métricas."
        "\n4. Aviso: Siempre indica que tus recomendaciones son basadas en datos y deben ser validadas en campo."
    )),
    MessagesPlaceholder(variable_name="history"), # Para que AgroTech recuerde qué parcelas estamos analizando
    ("human", "{input}"),
])

# 3. Almacenamiento de memoria conversacional por sesión
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# 4. Construcción de la cadena operativa (LCEL)
chain = prompt | llm

# Versión con memoria
agro_agent = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

def get_answer(question: str, user_id: str = "demo_user") -> str:
    """
    Envía una consulta a AgroTech. 
    user_id permite que el bot recuerde la conversación anterior con ese usuario específico.
    """
    try:
        response = agro_agent.invoke(
            {"input": question},
            config={"configurable": {"session_id": user_id}}
        )
        return response.content
    except Exception as e:
        return f"Error en el motor AgroTech AI: {str(e)}"