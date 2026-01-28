# Usa Python 3.11 en su versión ligera
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema necesarias para PostgreSQL si fuera necesario
# (psycopg2-binary suele no necesitarlas, pero es buena práctica)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de requisitos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido de tu carpeta local al contenedor
COPY . .

# Expone el puerto que usa tu app de Flask
EXPOSE 5001

# Comando para ejecutar la aplicación
# Asegúrate de que tu script se llame main.py o cambia el nombre aquí
CMD ["python", "clima-historics.py"]