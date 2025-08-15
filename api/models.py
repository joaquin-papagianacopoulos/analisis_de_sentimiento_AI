# models.py
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, DECIMAL, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index
import enum
from datetime import datetime

Base = declarative_base()

class SentimentEnum(enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class Noticia(Base):
    __tablename__ = 'noticias'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fecha = Column(TIMESTAMP, nullable=False)
    fuente = Column(String(255))
    autor = Column(String(255))
    url = Column(Text, nullable=False, unique=True)
    titulo = Column(Text, nullable=False)
    descripcion = Column(Text)
    contenido = Column(Text)
    palabra_clave = Column(String(100), nullable=False)
    sentimiento_label = Column(Enum(SentimentEnum), nullable=False)
    sentimiento_score = Column(DECIMAL(5,4), nullable=False)
    idioma = Column(String(10))
    
    # Índices definidos en la tabla
    __table_args__ = (
        Index('idx_noticias_fecha', 'fecha'),
        Index('idx_noticias_sentimiento', 'sentimiento_label'),
        Index('idx_noticias_keyword', 'palabra_clave'),
    )
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'fuente': self.fuente,
            'autor': self.autor,
            'url': self.url,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'contenido': self.contenido,
            'palabra_clave': self.palabra_clave,
            'sentimiento_label': self.sentimiento_label.value if self.sentimiento_label else None,
            'sentimiento_score': float(self.sentimiento_score) if self.sentimiento_score else None,
            'idioma': self.idioma
        }
    
    def __repr__(self):
        return f"<Noticia(id={self.id}, titulo='{self.titulo[:50]}...', sentimiento='{self.sentimiento_label}')>"