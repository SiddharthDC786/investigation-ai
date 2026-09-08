from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import cases, entities, graph, ingestion, leads, search

app = FastAPI(
    title="Investigation AI API",
    version="0.2.0",
    description="Vigil-compatible investigation API (search + cases + graph)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend",
    }


app.include_router(cases.router)
app.include_router(search.router)
app.include_router(ingestion.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(leads.router)
