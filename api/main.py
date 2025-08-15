# main.py
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from typing import Optional, List
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Importaciones locales
from sentiment_crew import analyze_sentiment_with_crewai
try:
    from api.db import engine
    from api.models import Base
    from api.repository import (
        guardar_noticias, 
        obtener_estadisticas_sentimiento,
        obtener_noticias_por_palabra_clave,
        obtener_noticias_recientes
    )
except ImportError:
    print("Warning: No se pudieron importar los módulos de base de datos")
    engine = None
    Base = None
    guardar_noticias = None
    obtener_estadisticas_sentimiento = None
    obtener_noticias_por_palabra_clave = None
    obtener_noticias_recientes = None

load_dotenv()

# Variables de entorno
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Crear tablas si existen los módulos
if Base and engine:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="News & Sentiment Tracker API with CrewAI",
    description="API para análisis de sentimientos en noticias usando LLM con CrewAI",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para respuestas
class NewsResponse(BaseModel):
    totalResults: int
    nuevas_guardadas: int
    noticias: List[dict]
    estadisticas: dict
    promedio_sentimiento: float
    parametros_busqueda: dict

class AnalysisStatus(BaseModel):
    status: str
    message: str
    processed_count: int

# ThreadPool para procesamiento en background
executor = ThreadPoolExecutor(max_workers=2)

def process_news_with_llm(noticias_data: List[dict]) -> List[dict]:
    """
    Procesa noticias con análisis LLM usando CrewAI
    """
    try:
        if not GROQ_API_KEY:
            raise Exception("GROQ_API_KEY no configurada")
        
        # Analizar con CrewAI
        analyzed_news = analyze_sentiment_with_crewai(noticias_data, GROQ_API_KEY)
        return analyzed_news
        
    except Exception as e:
        print(f"Error procesando con LLM: {e}")
        # Fallback: mantener datos originales
        return noticias_data

@app.get("/")
def read_root():
    return {
        "message": "News & Sentiment Tracker API with CrewAI - Running",
        "version": "2.0.0",
        "features": ["NewsAPI Integration", "CrewAI Sentiment Analysis", "MySQL Database"]
    }

@app.get("/api/news", response_model=NewsResponse)
async def get_news_with_llm_analysis(
    background_tasks: BackgroundTasks,
    prompt: str = Query(
        default="messi", 
        description="Palabra clave para buscar noticias",
        min_length=1,
        max_length=100
    ),
    days: int = Query(
        default=7,
        description="Días hacia atrás para buscar noticias",
        ge=1,
        le=30
    ),
    page_size: int = Query(
        default=10,
        description="Número de noticias a obtener",
        ge=1,
        le=20  # Reducimos el límite porque el análisis LLM es más lento
    ),
    use_llm: bool = Query(
        default=True,
        description="Usar análisis LLM con CrewAI"
    )
):
    """
    Obtiene noticias y las analiza usando LLM con CrewAI
    """
    
    # Validar API keys
    if not NEWSAPI_KEY:
        raise HTTPException(status_code=500, detail="NEWSAPI_KEY no configurada")
    
    if use_llm and not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada para análisis LLM")
    
    # Buscar noticias
    url = "https://newsapi.org/v2/everything"
    
    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=days)
    
    params = {
        "q": prompt,
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sortBy": "popularity",
        "language": "es",
        "pageSize": page_size,
        "apiKey": NEWSAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="API Key inválida")
            elif response.status_code == 429:
                raise HTTPException(status_code=429, detail="Límite de requests excedido")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Error de NewsAPI: {response.text}")
        
        data = response.json()
        articles = data.get("articles", [])
        
        if not articles:
            return NewsResponse(
                totalResults=0,
                nuevas_guardadas=0,
                noticias=[],
                estadisticas={"positive": 0, "negative": 0, "neutral": 0},
                promedio_sentimiento=0.0,
                parametros_busqueda={
                    "palabra_clave": prompt,
                    "dias_buscados": days,
                    "use_llm": use_llm
                }
            )
        
        # Preparar datos de noticias
        noticias_raw = []
        for art in articles:
            try:
                title_text = art.get("title", "")
                if title_text and title_text.lower() != "[removed]":
                    fecha = datetime.strptime(art["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
                    
                    noticia = {
                        "fecha": fecha,
                        "fuente": art["source"].get("name", "Desconocida"),
                        "autor": art.get("author", "No especificado"),
                        "url": art.get("url", ""),
                        "titulo": title_text,
                        "descripcion": art.get("description", ""),
                        "contenido": art.get("content", ""),
                        "palabra_clave": prompt,
                        "idioma": "es"
                    }
                    
                    noticias_raw.append(noticia)
            except Exception as e:
                print(f"Error procesando artículo: {e}")
                continue
        
        # Análisis de sentimientos
        if use_llm and noticias_raw:
            # Procesar con LLM en un hilo separado para no bloquear
            loop = asyncio.get_event_loop()
            noticias_analizadas = await loop.run_in_executor(
                executor, 
                process_news_with_llm, 
                noticias_raw
            )
        else:
            # Fallback: análisis simple
            noticias_analizadas = []
            for noticia in noticias_raw:
                noticia.update({
                    'sentimiento_label': 'neutral',
                    'sentimiento_score': 2.5
                })
                noticias_analizadas.append(noticia)
        
        # Guardar en base de datos en background
        guardadas = 0
        if guardar_noticias and noticias_analizadas:
            background_tasks.add_task(
                save_news_background,
                noticias_analizadas.copy()
            )
        
        # Calcular estadísticas
        sentimientos = [n["sentimiento_label"] for n in noticias_analizadas]
        stats = {
            "positive": sentimientos.count("positive"),
            "negative": sentimientos.count("negative"),
            "neutral": sentimientos.count("neutral")
        }
        
        promedio = sum(n["sentimiento_score"] for n in noticias_analizadas) / len(noticias_analizadas) if noticias_analizadas else 0
        
        return NewsResponse(
            totalResults=len(noticias_analizadas),
            nuevas_guardadas=0,  # Se actualiza en background
            noticias=noticias_analizadas,
            estadisticas=stats,
            promedio_sentimiento=round(promedio, 3),
            parametros_busqueda={
                "palabra_clave": prompt,
                "dias_buscados": days,
                "desde": from_dt.isoformat(),
                "hasta": to_dt.isoformat(),
                "use_llm": use_llm
            }
        )
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout conectando con NewsAPI")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Error de conexión con NewsAPI")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

def save_news_background(noticias_data: List[dict]):
    """
    Guarda noticias en background task
    """
    try:
        if guardar_noticias:
            guardadas = guardar_noticias(noticias_data)
            print(f"Background: {guardadas} noticias guardadas en BD")
    except Exception as e:
        print(f"Error en background task: {e}")

@app.get("/api/news/recent")
def get_recent_news(limit: int = Query(default=10, ge=1, le=50)):
    """
    Obtiene noticias recientes de la base de datos
    """
    if not obtener_noticias_recientes:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    
    try:
        noticias = obtener_noticias_recientes(limit)
        return {
            "total": len(noticias),
            "noticias": noticias
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo noticias: {str(e)}")

@app.get("/api/news/by-keyword/{palabra_clave}")
def get_news_by_keyword(
    palabra_clave: str,
    limit: int = Query(default=20, ge=1, le=100),
    days_back: int = Query(default=7, ge=1, le=30)
):
    """
    Obtiene noticias por palabra clave de la base de datos
    """
    if not obtener_noticias_por_palabra_clave:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    
    try:
        noticias = obtener_noticias_por_palabra_clave(palabra_clave, limit, days_back)
        return {
            "palabra_clave": palabra_clave,
            "total": len(noticias),
            "noticias": noticias
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo noticias: {str(e)}")

@app.get("/api/stats")
def get_sentiment_stats(
    palabra_clave: Optional[str] = Query(default=None, description="Filtrar por palabra clave"),
    days_back: int = Query(default=7, ge=1, le=30, description="Días hacia atrás")
):
    """
    Obtiene estadísticas de sentimientos
    """
    if not obtener_estadisticas_sentimiento:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    
    try:
        stats = obtener_estadisticas_sentimiento(palabra_clave, days_back)
        return {
            "palabra_clave": palabra_clave,
            "periodo_dias": days_back,
            "estadisticas": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@app.get("/api/health")
def health_check():
    """
    Health check con información del sistema
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "newsapi_key_configured": bool(NEWSAPI_KEY),
            "groq_key_configured": bool(GROQ_API_KEY),
            "database_available": bool(guardar_noticias),
            "crewai_available": True
        },
        "version": "2.0.0"
    }

@app.post("/api/analyze")
async def analyze_existing_news(
    background_tasks: BackgroundTasks,
    palabra_clave: str = Query(..., description="Palabra clave para reanalizar"),
    limit: int = Query(default=10, ge=1, le=50)
):
    """
    Reanálisis de noticias existentes con CrewAI
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada")
    
    if not obtener_noticias_por_palabra_clave:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    
    try:
        # Obtener noticias existentes
        noticias = obtener_noticias_por_palabra_clave(palabra_clave, limit)
        
        if not noticias:
            return {
                "status": "no_news",
                "message": f"No se encontraron noticias para '{palabra_clave}'",
                "processed_count": 0
            }
        
        # Procesar en background
        background_tasks.add_task(
            reanalyze_news_background,
            noticias,
            palabra_clave
        )
        
        return AnalysisStatus(
            status="processing",
            message=f"Iniciando reanálisis de {len(noticias)} noticias para '{palabra_clave}'",
            processed_count=0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error iniciando análisis: {str(e)}")

async def reanalyze_news_background(noticias_data: List[dict], palabra_clave: str):
    """
    Reanálisis de noticias en background
    """
    try:
        print(f"Iniciando reanálisis de {len(noticias_data)} noticias...")
        
        # Procesar con CrewAI
        loop = asyncio.get_event_loop()
        noticias_analizadas = await loop.run_in_executor(
            executor,
            process_news_with_llm,
            noticias_data
        )
        
        # Guardar resultados actualizados
        if guardar_noticias:
            guardadas = guardar_noticias(noticias_analizadas)
            print(f"Reanálisis completado: {guardadas} noticias actualizadas")
        
    except Exception as e:
        print(f"Error en reanálisis background: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)