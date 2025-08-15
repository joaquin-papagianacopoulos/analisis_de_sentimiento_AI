import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.db import SessionLocal
from api.models import Noticia

client = TestClient(app)

def limpiar_tabla():
    """Vacía la tabla noticias antes de cada test."""
    db = SessionLocal()
    db.query(Noticia).delete()
    db.commit()
    db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    limpiar_tabla()
    yield
    limpiar_tabla()

def test_guardar_noticias_y_evitar_duplicados():
    # Primera llamada: debería insertar varias noticias
    resp1 = client.get("/api/news?q=python&days=1&lang=en")
    assert resp1.status_code == 200
    data1 = resp1.json()

    total_insertadas_1 = data1["nuevas_guardadas"]
    assert total_insertadas_1 > 0  # Tiene que guardar algo

    # Segunda llamada con mismo query: no debería insertar nada nuevo
    resp2 = client.get("/api/news?q=python&days=1&lang=en")
    assert resp2.status_code == 200
    data2 = resp2.json()

    total_insertadas_2 = data2["nuevas_guardadas"]
    assert total_insertadas_2 == 0  # No debería duplicar

    # Comprobar que en la base de datos hay la misma cantidad que en la primera inserción
    db = SessionLocal()
    count_db = db.query(Noticia).count()
    db.close()

    assert count_db == total_insertadas_1
