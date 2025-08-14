from sqlalchemy.exc import IntegrityError
from .models import Noticia
from .db import SessionLocal

def guardar_noticias(noticias: list):
    session = SessionLocal()
    guardadas = 0
    try:
        for n in noticias:
            noticia = Noticia(**n)
            session.add(noticia)
            try:
                session.commit()
                guardadas += 1
            except IntegrityError:
                session.rollback()  # Duplicada por URL
        return guardadas
    finally:
        session.close()
