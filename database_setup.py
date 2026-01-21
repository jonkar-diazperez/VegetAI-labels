# database_setup.py
from sqlalchemy import create_engine, text, URL

# Construimos la URL de forma segura para evitar el error de puerto vacío
db_url = URL.create(
    drivername="postgresql",
    username="admin",
    password="HBBQ4KQy4S6OP1qAOmBuArJ8SKKouu2q",
    host="dpg-d5nov1q4d50c73fu8ig0-a.oregon-postgres.render.com",
    port=5432,
    database="reto_db_gty6"
)

def setup_database():
    try:
        # Creamos el motor de conexión usando el objeto URL
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            print("Conectando a Render para configurar tablas...")
            
            # 1. Crear tabla de registros climáticos
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS registros_clima (
                    id SERIAL PRIMARY KEY,
                    fecha TIMESTAMP,
                    parcela_id INTEGER,
                    nombre_parcela VARCHAR(100),
                    finca_id INTEGER,
                    latitud FLOAT,
                    longitud FLOAT,
                    temperatura FLOAT,
                    humedad_relativa FLOAT,
                    humedad_suelo FLOAT,
                    precipitacion FLOAT,
                    viento_velocidad FLOAT,
                    viento_direccion FLOAT,
                    evapotranspiracion FLOAT
                );
            """))
            
            # 2. Crear tabla de monitorización (Logs)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS logs_procesos (
                    id SERIAL PRIMARY KEY,
                    fecha TIMESTAMP,
                    proceso VARCHAR(50),
                    endpoint VARCHAR(50),
                    estado VARCHAR(20),
                    mensaje TEXT
                );
            """))
            
            conn.commit()
            print("Tablas creadas/verificadas con éxito en Render.")
            
    except Exception as e:
        print(f"Error al configurar la base de datos: {e}")

if __name__ == "__main__":
    setup_database()
