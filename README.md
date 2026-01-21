# VegetAI-labels
Repositorio para el código de APIs del proyecto de aplicación de Gestión de campos agrícolas
## 📄 Documentación del Servicio Meteorológico - Proyecto FruIT

Esta api proporciona una interfaz para consumir datos climáticos de una zona para análisis agrícola (basado en Open-Meteo).

## 🚀 Instalación de Dependencias:

pip install openmeteo-requests pandas requests-cache retry-requests flask

## 🛠 Endpoint: GET /consultar_datos:

http://127.0.0.1:5000/consultar_datos?lat=-37.9739&lon=-72.5897&days=15

Este endpoint devuelve un resumen diario de indicadores clave para la gestión de cultivos.

## 📥 Parámetros de Entrada (Query Params)

    Parametro   |   Tipo    |   Requerido   |   Ejemplo
    lat         |   float   |   SI          |   -37.9739
    lon         |   float   |   SI          |   -72.5897
    days        |   int     |   NO          |   15

## 📤 Estructura de la Respuesta (JSON)
La respuesta devuelve un objeto con el estado, la ubicación confirmada y una lista de datos diarios en la clave data.
{
  "data": [
    {
      "date": "2026-01-14",
      "evapotranspiration": 5.849999904632568,
      "humidity_mean": 61.619998931884766,
      "leaf_wetness": NaN,
      "precip_prob": 5.960000038146973,
      "temp_mean": 15.75,
      "wind_direction": 236.17999267578125,
      "wind_speed": 15.819999694824219
    },
    {
      "date": "2026-01-15",
      "evapotranspiration": 5.539999961853027,
      "humidity_mean": 60.290000915527344,
      "leaf_wetness": NaN,
      "precip_prob": 6.579999923706055,
      "temp_mean": 14.770000457763672,
      "wind_direction": 190.92999267578125,
      "wind_speed": 15.850000381469727
    },
    {
        ...
    }  ],
  "location": {
    "lat": -37.9739,
    "lon": -72.5897
  },
  "status": "ok"
}