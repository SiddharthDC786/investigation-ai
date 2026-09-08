from fastapi import APIRouter, HTTPException

from app.schemas.entity import Entity

router = APIRouter(prefix="/entities", tags=["entities"])

# Temporary fake data — will come from Neo4j later
fake_entities: dict[str, Entity] = {
    "P001": Entity(id="P001", type="PERSON", label="Person 1"),
    "PH001": Entity(id="PH001", type="PHONE", label="9876500001"),
    "VEH001": Entity(id="VEH001", type="VEHICLE", label="MH12AB1234"),
}

@router.get("/{entity_id}", response_model=Entity)
def get_entity(entity_id: str):
    if entity_id not in fake_entities:
        raise HTTPException(status_code=404, detail="Entity not found")
    return fake_entities[entity_id]

    from app.services.entity_service import get_entity_by_id, get_entity_connections, get_entity_history

@router.get("/{entity_id}/connections")
def entity_connections(entity_id: str):
    return get_entity_connections(entity_id)

@router.get("/{entity_id}/history")
def entity_history(entity_id: str):
    return get_entity_history(entity_id)