# Imagen base ligera de Python 3.11
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias para PostgreSQL y compilación
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependencias de Python primero (mejor uso de caché)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de la aplicación
COPY . .

# Expone el puerto que usa Flask
EXPOSE 5000

# Ejecuta la aplicación directamente. 
# El control de espera lo hará Docker Compose con 'service_healthy'
CMD ["python", "main.py"]
