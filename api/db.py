# api/db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Datos de conexión
DB_USER = os.getenv("DB_USER", "root")       # tu usuario de MySQL
DB_PASS = os.getenv("DB_PASS", "")           # tu password de MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")  # host
DB_PORT = os.getenv("DB_PORT", "3306")       # puerto
DB_NAME = os.getenv("DB_NAME", "noti")       # base de datos

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear engine y session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
