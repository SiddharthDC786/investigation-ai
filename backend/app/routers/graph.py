from fastapi import APIRouter

from app.schemas.graph import GraphResponse

router = APIRouter(tags=["graph"])

@router.get("/cases/{case_id}/graph", response_model=GraphResponse)
def get_graph(case_id: str):
    return {
        "nodes": [
            {"id": "P001", "type": "PERSON", "label": "Person 1"},
            {"id": "PH001", "type": "PHONE", "label": "9876500001"},
            {"id": "P002", "type": "PERSON", "label": "Person 2"},
        ],
        "edges": [
            {"source": "P001", "target": "PH001", "type": "USES_PHONE"},
            {"source": "PH001", "target": "P002", "type": "CALLED"},
        ],
    }