🌱 CultiTech – Plataforma Inteligente para la Gestión Agrícola

CultiTech es una plataforma web de inteligencia agrícola diseñada para apoyar la toma de decisiones en el sector frutícola mediante la integración de datos climáticos, análisis visual, modelos de predicción y servicios de inteligencia artificial.

El proyecto nace como un MVP (Producto Mínimo Viable) enfocado inicialmente en el contexto chileno, pero con una arquitectura pensada para escalar a otros países y realidades agrícolas.

🎯 Objetivo del proyecto

Desarrollar una plataforma que permita:

Centralizar información relevante del cultivo.

Anticipar riesgos climáticos y fitosanitarios.

Integrar evidencias visuales del estado real del campo.

Facilitar la comunicación entre productores, asesores y managers.

Apoyar decisiones técnicas y comerciales basadas en datos.

La plataforma actúa como herramienta de apoyo, no como sustituto del criterio humano.

🚀 Visión general
Proyecto desarrollado como un MVP validado por equipos Full Stack y Data Science, enfocado inicialmente en el sector frutícola chileno (cerezos, uvas, paltos), con una arquitectura escalable que permite adaptación a otras regiones y cultivos.

El objetivo principal es centralizar información agrícola dispersa y convertirla en decisiones técnicas accionables, conectando datos climáticos, registros de campo, imágenes y predicciones de IA a través de 11 microservicios REST.

👥 Perfiles de usuario

La solución se adapta a distintos roles del sector agrícola:

Productor: monitoreo de su campo, alertas, incidencias, estado del cultivo.

Asesor agrícola: análisis técnico, históricos, diagnóstico remoto.

Manager: visión global productiva, planificación logística y gestión de riesgos.

🧩 Arquitectura general

La plataforma se organiza en tres grandes capas:

Frontend

Interfaz web para visualización de datos y experiencia de usuario.
Tecnología: React + Vite

Backend

Lógica de negocio, seguridad, usuarios y orquestación de servicios.
Tecnología: Node.js + Express

Data Science & AI

Servicios analíticos y modelos de inteligencia expuestos como APIs.
Tecnología: Python + Flask

Todo el sistema se comunica mediante APIs REST, permitiendo una arquitectura modular, desacoplada y escalable.


🚀 Funcionalidades principales (MVP)

Integración de datos climáticos en tiempo real e históricos.

Generación de alertas de riesgo climático (heladas, calor, viento).

Predicción de plagas mediante modelos basados en GDD.

Detección de plagas por visión artificial (YOLOv8).

Clasificación de plantas por imagen.

Análisis de suelo y productividad (NDVI).

Asistente agrícola inteligente con IA conversacional.

Trazabilidad básica por parcela y fecha.

🔌 Catálogo de APIs

CultiTech integra 11 microservicios especializados, con documentación técnica detallada (ver “Anexo 1 – Memoria Técnica”).

1	Clima Tiempo Real	7 variables climáticas (temp, humedad, viento...)	✅ Activa
2	Agrometeo Históricos	Tendencias por rango de fechas	✅ Activa
3	Alerta Plagas (GDD)	Riesgo fitosanitario por cultivo	✅ Activa
4	Datos Climáticos Diarios	Indicadores tipo NDVI	✅ Activa
5	Alerta ML	Predicción RF (helada, golpe de calor)	✅ Activa
6	Detección Plagas (YOLOv8)	Visión artificial (78+ plagas)	✅ Activa
7	Clasificación Plantas	Reconocimiento de especie	✅ Activa
8	Análisis Suelo	pH, textura, NDVI, topografía	✅ Activa
9	Asistente IA	Chat LLM (Groq + LangChain)	✅ Activa
10	Auravant Campos	Gestión de parcelas (deprecada)	⚠️ Deprecada
11	Open-Meteo Histórico 5 años	Resúmenes climáticos	✅ Activa

Todas las APIs siguen un diseño unificado y están pensadas para ser reutilizables.

🧠 Inteligencia aplicada

La IA no se concibe como un fin en sí mismo, sino como una capa transversal del producto, aportando:

Anticipación de eventos críticos (heladas, plagas).

Evidencia visual objetiva (detección YOLOv8).

Explicabilidad y soporte a decisiones con IA conversacional (Groq LLM).

Predicciones combinadas: clima + fenología + imágenes.

🧪 Validación del MVP

El MVP fue validado mediante:

Integración funcional entre todos los componentes (Open-Meteo, Hugging Face, Groq).

Validación con escenarios reales (heladas, plagas).

Confirmación de valor agregado para productores y asesores.

El resultado principal es demostrar que la plataforma aporta valor real y puede evolucionar hacia un producto comercial.

⚠️ Limitaciones actuales

Como MVP:

Cobertura limitada de cultivos y plagas.

Modelos centrados en casos prioritarios.

Dependencia de datos externos.

Recomendaciones aún no completamente automáticas.

🔮 Líneas de evolución

Próximos pasos del producto:

Gestión inteligente del riego.

Recomendaciones agronómicas avanzadas.

Análisis de maduración de cultivos.

Integración con más fuentes externas.

Escalado internacional.

🛠️ Tecnologías utilizadas
Capa	Tecnologías
Frontend	React, Vite
Backend	Node.js, Express
Data Science	Python, Flask
ML	Random Forest, YOLOv8
APIs externas	Open-Meteo, MODIS
IA conversacional	LangChain, Groq
Base de datos	PostgreSQL
Visión artificial	OpenCV

⚙️ Instalación y despliegue

MVP operativo desplegado en AWS EC2 y Render (chat).

# Clonar repositorio
git clone https://github.com/jonkar-diazperez/VegetAI-labels.git
cd VegetAI-labels

# Frontend / Backend
npm install && cp .env.example .env
npm run dev # http://localhost:3000

# APIs Python (una por carpeta)
pip install -r requirements.txt
flask run --port=5000

# Base de datos
docker-compose up postgres
Producción recomendada: Docker, AWS EC2, Render (chat IA).

📊 Resultados MVP
Alertas tempranas validadas (heladas, plagas).

Integración multi-API funcional.

Flujo completo: parcela → fecha → evidencia.

Arquitectura escalable y modular.

🔮 Roadmap
🌦️ Gestión inteligente del riego (clima + suelo).

🌿 Recomendaciones agronómicas avanzadas.

🍒 Análisis de madurez y cosecha.

🌍 Escalado internacional (UE / LATAM).

📌 Conclusión

CultiTech demuestra cómo una necesidad real del sector frutícola puede transformarse en una solución digital sólida, escalable y con visión de producto.

El proyecto integra tecnología, datos e inteligencia en una plataforma usable, validando una arquitectura moderna basada en APIs y un enfoque multidisciplinar entre Full Stack y Data Science.
