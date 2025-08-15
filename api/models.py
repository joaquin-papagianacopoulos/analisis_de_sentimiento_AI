# api/models.py
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Enum, DECIMAL
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Noticia(Base):
    __tablename__ = "noticias"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fecha = Column(TIMESTAMP, nullable=False)
    fuente = Column(String(255))
    autor = Column(String(255))
    url = Column(Text, nullable=False, unique=True)
    titulo = Column(Text, nullable=False)
    descripcion = Column(Text)
    contenido = Column(Text)
    palabra_clave = Column(String(100), nullable=False)
    sentimiento_label = Column(Enum("positive", "neutral", "negative"), nullable=False)
    sentimiento_score = Column(DECIMAL(5,4), nullable=False)
    idioma = Column(String(10))
