# Usa una imagen ligera de Python
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias primero (para aprovechar el cache de Docker)
COPY requirements.txt .

# Instala las librerías necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu proyecto
COPY . .

# Expone el puerto que usa Flask
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "consultar_datos.py"]