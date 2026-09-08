from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import cases, entities, graph, ingestion, leads, resolution

app = FastAPI(
    title="Investigation AI API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "backend"}

app.include_router(cases.router)
app.include_router(ingestion.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(leads.router)
app.include_router(resolution.router)