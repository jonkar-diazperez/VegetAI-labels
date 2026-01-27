FROM python:3.10-slim

WORKDIR /app

# Copiar archivos de requisitos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos de la aplicación
COPY . .

# Exponer el puerto 7860 (requerido por Hugging Face Spaces)
EXPOSE 7860

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]