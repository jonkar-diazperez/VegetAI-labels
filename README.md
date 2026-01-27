# VegetAI-labels
Repositorio para el código de APIs del proyecto de aplicación de Gestión de campos agrícolas

## API AURAVANT - Gestión de campos y parcelas

Esta API tiene 2 operaciones creadas para ser utilizadas por el FRONT como interfaz con este sistema de gestión de fincas y sus cosechas.
### AGREGAR PARCELA (POST)
API para la creación en AURAVANT de las parcelas introducidas por el usuario a partir de las coordenadas del polígono definido por el mismo. El usuario introducirá también el nombre de la parcela y el campo al que está asociada. Se pueden asociar varias parcelas en el mismo campo.

**ENDPOINT**
\<hostname\>/agregar_parcela

**REQUEST**
```Python
{
    "data": [
        "TEST parcela 20260121005",	#Nombre de la parcela que se registra con sus coordenadas
        "POLYGON((-71.088430 -34.727273, -71.087058 -34.727273, -71.087058 -34.727777, -71.088430 -34.727777,-71.088430 -34.727273))",	#Coordenadas de los puntos que delimitan la parcela
        "TEST campo 20260121005"		#Nombre del campo donde está la parcela. Si no existe ya se crea 					con esa parcela
    ]
}

```
**RESPONSE**
```Python
{
  "id_campo": 227823,
  "id_lote": "784377",
  "info": "Nuevo id lote 784377",
  "res": "ok",
  "uuid_campo": "ed4a7eae-5b64-417b-b22a-ce620e0bd1cf",
  "uuid_lote": "7dc09229-0063-410e-8d90-c020aa5c1f8d"
}

```
### CONSULTAR PARCELA (GET)
API para la consulta en AURAVANT de la información de las parcelas introducidas por el usuario usando el ID de la parcela en AURAVANT. 

**ENDPOINT**
\<hostname\>/consultar_parcela

**REQUEST**
```Python
{
    "data": [
        "784666"	#ID en AURAVANT de la parcela que se consulta
    ]
}

```
**RESPONSE**
```Python
{
  "country": "CL",
  "currency": "$",
  "farm": "test campo 20260122003",
  "id": 784666,
  "name": "TEST parcela 20260122003",
  "permissions": [
    3,    4,    5,    6,    7,    8,    9,    10,    11,    12,    13,    14,    15,    16,    17,    18,    20,    22,
    24,    27,    28,    30,    31,    32,    33,    34,    35,    37,    38,    41,    42,    48,    50,    52,    53,    60,    61,    62,    63,    70,    72,    94,    100,    101,    110,    111,    112,    113,    114,    120,    121,    131,    140,    141,    142,    143,    150,    151,    210,    211,    212,    213,    220,    241,    250,    251,    252,    260,    261,    262,    320,    321,    322,    323,    345,    800,    801,    802,    803,    804,    805,    806,    900,    901,    902,    903,    904,    905,    906,    907,    909,    910,    911,    921
  ],
  "province": null,
  "role": 1,
  "shapes": {
    "current": {
      "area": 0.7026615,
      "bbox": "POLYGON((-71.08843 -34.727777,-71.08843 -34.727273,-71.087058 -34.727273,-71.087058 -34.727777,-71.08843 -34.727777))",
      "campaign_from": null,
      "campaign_to": null,
      "centroid": "POINT(-71.087744 -34.727525)",
      "end_date": "current",
      "polygon": "POLYGON((-71.08843 -34.727273,-71.087058 -34.727273,-71.087058 -34.727777,-71.08843 -34.727777,-71.08843 -34.727273))",
      "shape_id": 808399,
      "start_date": "2026-01-22T21:46:00Z"
    }
  },
  "tags_field": null,
  "tags_field_colors": null,
  "tags_field_names": null,
  "uuid": "49c30bf3-4dfc-4b00-87a8-84c9dc27f217"
}
```