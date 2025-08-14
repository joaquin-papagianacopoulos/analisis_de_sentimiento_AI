from fastapi import FastAPI

app = FastAPI(title="News & Sentiment Tracker API")

@app.get("/")
def root():
    return {"status": "running", "hint": "usá /api/health o /docs"}

@app.get("/api/health")
def health():
    return {"status": "ok"}
