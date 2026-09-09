from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal, get_db
from app.dependencies.auth import resolve_user
from app.routers import analyze, audit, auth, case_summary, cases, entities, explain, graph, ingestion, leads, osint, reviews, search, timeline
from app.services.audit_chain import ensure_audit_table
from app.services.graph_sync import sync_postgres_to_neo4j
from app.services.neo4j_schema import ensure_schema
from app.services.provenance_service import ensure_provenance_tables, reconcile_graph_counts
from app.services.review_service import ensure_reviews_table

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_schema()
        ensure_audit_table(db)
        ensure_provenance_tables(db)
        ensure_reviews_table(db)
        db.commit()
        counts = sync_postgres_to_neo4j(db)
        reconcile = reconcile_graph_counts(db)
        db.commit()
        logger.info("Startup graph sync: %s reconcile=%s", counts, reconcile.get("consistent"))
    except Exception as exc:
        logger.warning("Startup sync skipped: %s", exc)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Investigation AI API",
    version="0.7.0",
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
        "auth_enabled": settings.auth_enabled,
        "nlp": {
            "engine": nlp_engine_name(),
            "spacy_model": "en_core_web_sm" if spacy_available() else None,
        },
    }


_auth_dep = [Depends(resolve_user)] if settings.auth_enabled else []

app.include_router(auth.router)
app.include_router(cases.router, dependencies=_auth_dep)
app.include_router(search.router, dependencies=_auth_dep)
app.include_router(ingestion.router, dependencies=_auth_dep)
app.include_router(entities.router, dependencies=_auth_dep)
app.include_router(graph.router, dependencies=_auth_dep)
app.include_router(timeline.router, dependencies=_auth_dep)
app.include_router(analyze.router, dependencies=_auth_dep)
app.include_router(osint.router, dependencies=_auth_dep)
app.include_router(audit.router, dependencies=_auth_dep)
app.include_router(explain.router, dependencies=_auth_dep)
app.include_router(case_summary.router, dependencies=_auth_dep)
app.include_router(leads.router, dependencies=_auth_dep)
app.include_router(reviews.router, dependencies=_auth_dep)
