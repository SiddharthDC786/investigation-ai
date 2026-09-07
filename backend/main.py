from fastapi import FastAPI, HTTPException
from schemas import CaseCreate

app = FastAPI(
    title="Investigation AI API",
    version="0.1.0"
)

cases = []


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "backend"
    }


@app.post("/cases")
def create_case(case: CaseCreate):
    cases.append(case)
    return case


@app.get("/cases")
def get_cases():
    return cases


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    for case in cases:
        if case.case_id == case_id:
            return case

    raise HTTPException(
        status_code=404,
        detail="Case not found"
    )