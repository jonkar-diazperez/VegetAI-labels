from config_env import Config
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config_env import Config

# dialect+driver://usuario:contraseña@host:puerto/nombre_db
engine = create_engine(Config.DATABASE_URL)

Base = declarative_base()

class Interaccion(Base):
    __tablename__ = "interacciones"
    id = Column(Integer, primary_key=True)
    pregunta = Column(String, nullable=False)
    respuesta = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

SesionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
