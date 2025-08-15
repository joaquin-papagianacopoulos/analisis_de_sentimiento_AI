from fastapi import FastAPI
import requests
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from textblob import TextBlob

from .db import engine
from .models import Base
from .repository import guardar_noticias

# Crear tablas si no existen (en este caso ya existe, pero por seguridad)
Base.metadata.create_all(bind=engine)

load_dotenv()
API_KEY = os.getenv("NEWSAPI_KEY")

app = FastAPI(title="News & Sentiment Tracker API")

@app.get("/api/news")
def get_news(q: str = "messi", days: int = 3, lang: str = "es"):
    url = "https://newsapi.org/v2/everything"

    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(days=days)

    params = {
        "q": q,
        "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sortBy": "popularity",
        "language": lang,
        "pageSize": 10,
        "apiKey": API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        noticias = []
        for art in data.get("articles", []):
            score = round(TextBlob(art["title"]).sentiment.polarity, 4)
            label = "positive" if score > 0 else "negative" if score < 0 else "neutral"

            noticias.append({
                "fecha": datetime.strptime(art["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"),
                "fuente": art["source"]["name"],
                "autor": art.get("author"),
                "url": art["url"],
                "titulo": art["title"],
                "descripcion": art.get("description"),
                "contenido": art.get("content"),
                "palabra_clave": q,
                "sentimiento_label": label,
                "sentimiento_score": score,
                "idioma": lang
            })

        guardadas = guardar_noticias(noticias)

        return {
            "totalResults": len(noticias),
            "nuevas_guardadas": guardadas,
            "noticias": noticias
        }

    return {"error": response.status_code, "message": response.text}
