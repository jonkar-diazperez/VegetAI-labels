# VegetAI-labels
Repositorio para el código de APIs del proyecto de aplicación de Gestión de campos agrícolas

1. 🌾 Módulo de Gestión de Riesgo Fitosanitario (AgriManager API)
Este módulo es un motor de decisión basado en Grados Días Desarrollo (GDD) y variables meteorológicas en tiempo real. Su objetivo es predecir el riesgo de aparición de plagas en las propiedades agrícolas para optimizar la aplicación de agroquímicos.

2. 🚀 Stack Tecnológico
Backend: Flask (Python)

Datos Meteorológicos: Open-Meteo API (Datos en tiempo real)

Lógica Biológica: Método de Corte Diurno para GDD.

3. 🛠 API Endpoint para Integración
El frontend debe realizar peticiones GET al siguiente endpoint:

URL: /plagas

Parámetros requeridos:

latitud (float): Coordenada decimal de la propiedad.

longitud (float): Coordenada decimal de la propiedad.

fruta (string): Nombre del cultivo (ej: manzana, uva, limón).

Ejemplo de Consulta (Axios/Fetch):
GET /plagas?latitud=-34.58&longitud=-70.98&fruta=manzana

4. 📊 Estructura de la Respuesta (JSON)
El Full Stack recibirá un objeto con dos secciones clave: alertas (para las gráficas de riesgo) y meteo_data (para el resumen del clima).

JSON

{
  "alertas": [
    {
      "pest": "pulgón",
      "risk_percent": 82.5,
      "risk_level": "alto",
      "gdd_7_dias": 145.2,
      "status": "Monitoreo CRÍTICO recomendado."
    }
  ],
  "meteo_data": {
    "humedad_promedio_max": 75.2,
    "lluvia_detectada": "No",
    "max_temp_semana": 32.5,
    "min_temp_semana": 12.1
  }
}
5. 🎨 Guía para el Frontend (UI/UX)
Para una correcta visualización en el dashboard de gestión de la propiedad, se recomienda seguir esta lógica de colores según el risk_level:

🔴 Alto (>= 70%): Color Hex #E74C3C. Mostrar alerta crítica y sugerir revisión de stock de pesticidas.

🟡 Medio (40% - 69%): Color Hex #F1C40F. Alerta preventiva. Sugerir incremento de monitoreo en terreno.

🟢 Bajo (< 40%): Color Hex #2ECC71. Estado óptimo. No requiere acciones inmediatas.

6. 🧠 Lógica del Algoritmo (Para el Backend)
El cálculo no es un promedio simple. El motor utiliza el Método de Corte Diurno:

Si la temperatura máxima del día supera la Tbase de la plaga, hay acumulación de calor.

Se pondera un 70% el calor acumulado (GDD) y un 30% la humedad/precipitación.

Esto evita falsos negativos en zonas con noches muy frías pero días soleados.

7. 🧪 Casos de Prueba
latitud -60, longitud -50, fruta manzana
