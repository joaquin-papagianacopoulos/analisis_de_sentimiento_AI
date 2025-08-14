from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class NewsItem(BaseModel):
    id: int
    fecha: datetime
    fuente: Optional[str] = None
    titulo: str
    descripcion: Optional[str] = None
    url: str
    palabra_clave: str
    sentimiento_label: str
    sentimiento_score: float

class NewsResponse(BaseModel):
    items: List[NewsItem]
    total: int
    page: int
    page_size: int
