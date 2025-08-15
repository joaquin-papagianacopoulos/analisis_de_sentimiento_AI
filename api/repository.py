# repository.py
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, desc, func
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .db import engine
from .models import Noticia, SentimentEnum
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Obtiene una sesión de base de datos"""
    return SessionLocal()

def guardar_noticias(noticias_data: List[Dict]) -> int:
    """
    Guarda noticias en la base de datos
    
    Args:
        noticias_data: Lista de diccionarios con datos de noticias
    
    Returns:
        Número de noticias nuevas guardadas
    """
    session = get_db_session()
    nuevas_guardadas = 0
    
    try:
        for noticia_data in noticias_data:
            try:
                # Validar y convertir sentimiento_label
                sentiment_label = noticia_data.get('sentimiento_label', 'neutral')
                if sentiment_label not in ['positive', 'neutral', 'negative']:
                    sentiment_label = 'neutral'
                
                # Crear objeto Noticia
                noticia = Noticia(
                    fecha=noticia_data.get('fecha', datetime.now()),
                    fuente=noticia_data.get('fuente', '')[:255],  # Truncar si es muy largo
                    autor=noticia_data.get('autor', '')[:255] if noticia_data.get('autor') else None,
                    url=noticia_data.get('url', ''),
                    titulo=noticia_data.get('titulo', ''),
                    descripcion=noticia_data.get('descripcion', ''),
                    contenido=noticia_data.get('contenido', ''),
                    palabra_clave=noticia_data.get('palabra_clave', '')[:100],
                    sentimiento_label=SentimentEnum(sentiment_label),
                    sentimiento_score=noticia_data.get('sentimiento_score', 2.5),
                    idioma=noticia_data.get('idioma', 'es')
                )
                
                session.add(noticia)
                session.commit()
                nuevas_guardadas += 1
                logger.info(f"Noticia guardada: {noticia.titulo[:50]}...")
                
            except IntegrityError:
                # URL duplicada - ya existe
                session.rollback()
                logger.info(f"Noticia ya existe: {noticia_data.get('titulo', 'Sin título')[:50]}...")
                continue
            except Exception as e:
                session.rollback()
                logger.error(f"Error guardando noticia individual: {e}")
                continue
                
    except Exception as e:
        session.rollback()
        logger.error(f"Error general guardando noticias: {e}")
    finally:
        session.close()
    
    return nuevas_guardadas

def obtener_noticias_por_palabra_clave(
    palabra_clave: str, 
    limit: int = 50,
    days_back: int = 7
) -> List[Dict]:
    """
    Obtiene noticias filtradas por palabra clave
    """
    session = get_db_session()
    try:
        fecha_limite = datetime.now() - timedelta(days=days_back)
        
        noticias = session.query(Noticia).filter(
            and_(
                Noticia.palabra_clave == palabra_clave,
                Noticia.fecha >= fecha_limite
            )
        ).order_by(desc(Noticia.fecha)).limit(limit).all()
        
        return [noticia.to_dict() for noticia in noticias]
        
    except Exception as e:
        logger.error(f"Error obteniendo noticias: {e}")
        return []
    finally:
        session.close()

def obtener_estadisticas_sentimiento(
    palabra_clave: Optional[str] = None,
    days_back: int = 7
) -> Dict:
    """
    Obtiene estadísticas de sentimiento
    """
    session = get_db_session()
    try:
        fecha_limite = datetime.now() - timedelta(days=days_back)
        
        query = session.query(Noticia).filter(Noticia.fecha >= fecha_limite)
        
        if palabra_clave:
            query = query.filter(Noticia.palabra_clave == palabra_clave)
        
        # Contar por sentimiento
        sentimientos = session.query(
            Noticia.sentimiento_label,
            func.count(Noticia.id).label('count'),
            func.avg(Noticia.sentimiento_score).label('avg_score')
        ).filter(
            Noticia.fecha >= fecha_limite
        )
        
        if palabra_clave:
            sentimientos = sentimientos.filter(Noticia.palabra_clave == palabra_clave)
            
        sentimientos = sentimientos.group_by(Noticia.sentimiento_label).all()
        
        # Procesar resultados
        stats = {
            'total_noticias': 0,
            'positive': {'count': 0, 'avg_score': 0.0},
            'neutral': {'count': 0, 'avg_score': 0.0},
            'negative': {'count': 0, 'avg_score': 0.0},
            'overall_avg_score': 0.0
        }
        
        total_score = 0
        for sentiment, count, avg_score in sentimientos:
            sentiment_key = sentiment.value
            stats[sentiment_key]['count'] = count
            stats[sentiment_key]['avg_score'] = round(float(avg_score or 0), 2)
            stats['total_noticias'] += count
            total_score += float(avg_score or 0) * count
        
        if stats['total_noticias'] > 0:
            stats['overall_avg_score'] = round(total_score / stats['total_noticias'], 2)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {}
    finally:
        session.close()

def obtener_noticias_recientes(limit: int = 10) -> List[Dict]:
    """
    Obtiene las noticias más recientes
    """
    session = get_db_session()
    try:
        noticias = session.query(Noticia).order_by(
            desc(Noticia.fecha)
        ).limit(limit).all()
        
        return [noticia.to_dict() for noticia in noticias]
        
    except Exception as e:
        logger.error(f"Error obteniendo noticias recientes: {e}")
        return []
    finally:
        session.close()

def buscar_noticias(
    query: str,
    sentiment_filter: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """
    Busca noticias por texto en título o descripción
    """
    session = get_db_session()
    try:
        db_query = session.query(Noticia).filter(
            Noticia.titulo.contains(query) | 
            Noticia.descripcion.contains(query)
        )
        
        if sentiment_filter and sentiment_filter in ['positive', 'neutral', 'negative']:
            db_query = db_query.filter(
                Noticia.sentimiento_label == SentimentEnum(sentiment_filter)
            )
        
        noticias = db_query.order_by(desc(Noticia.fecha)).limit(limit).all()
        
        return [noticia.to_dict() for noticia in noticias]
        
    except Exception as e:
        logger.error(f"Error buscando noticias: {e}")
        return []
    finally:
        session.close()