from fastapi import FastAPI
from app.routers import cases


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