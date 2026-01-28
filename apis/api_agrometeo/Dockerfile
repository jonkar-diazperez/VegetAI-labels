# Usa Python 3.11 en su versión ligera
FROM python:3.11-slim

# Configuraciones de entorno para Python en Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Dependencias del sistema para psycopg2 (Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Exponemos el puerto
EXPOSE 5000

# Comando de arranque
CMD ["python", "agrometeo-service.py"]