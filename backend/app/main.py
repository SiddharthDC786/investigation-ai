from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, get_db
from app.routers import analyze, audit, case_summary, cases, entities, explain, graph, ingestion, leads, osint, search, timeline
from app.services.audit_chain import ensure_audit_table
from app.services.graph_sync import sync_postgres_to_neo4j
from app.services.neo4j_schema import ensure_schema

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_schema()
        ensure_audit_table(db)
        counts = sync_postgres_to_neo4j(db)
        logger.info("Startup graph sync: %s", counts)
    except Exception as exc:
        logger.warning("Startup sync skipped: %s", exc)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Investigation AI API",
    version="0.6.0",
    description="Vigil SIH PS 26189 — fusion, analytics, OSINT audit, explainability & triage",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health_check(db=Depends(get_db)):
    from ai.ner_pipeline import nlp_engine_name, spacy_available
    from app.services.neo4j_client import is_neo4j_available

    postgres_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        postgres_ok = False

    neo4j_ok = is_neo4j_available()
    status = "ok" if postgres_ok else "degraded"

    return {
        "status": status,
        "service": "backend",
        "postgres": postgres_ok,
        "neo4j": neo4j_ok,
        "nlp": {
            "engine": nlp_engine_name(),
            "spacy_model": "en_core_web_sm" if spacy_available() else None,
        },
    }


app.include_router(cases.router)
app.include_router(search.router)
app.include_router(ingestion.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(timeline.router)
app.include_router(analyze.router)
app.include_router(osint.router)
app.include_router(audit.router)
app.include_router(explain.router)
app.include_router(case_summary.router)
app.include_router(leads.router)
