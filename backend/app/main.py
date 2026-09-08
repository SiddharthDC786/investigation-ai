from fastapi import FastAPI

from app.routers import cases, entities, graph, ingestion, leads

app = FastAPI(
    title="Investigation AI API",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend"
    }

app.include_router(cases.router)
app.include_router(ingestion.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(leads.router)