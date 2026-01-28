FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL="postgresql://admin:HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q@dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com/reto_db_gty6?sslmode=require"

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias del sistema y Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libpq-dev git && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y gcc g++ && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copiar código y credenciales
COPY . .

# Crear carpeta de cache para requests-cache
RUN mkdir -p /app/.cache

# Exponer puerto Flask
EXPOSE 5000

# Ejecutar la app
CMD ["python", "api_suelo_clima_hist.py"]
