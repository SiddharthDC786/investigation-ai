from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.entity import Entity, EntitySourceRef
from app.services.entity_resolution import get_entity_from_neo4j
from app.services.neo4j_client import is_neo4j_available

router = APIRouter(prefix="/entities", tags=["entities"])


def _entity_from_postgres(db: Session, entity_id: str) -> Entity | None:
    if entity_id.startswith("P") and len(entity_id) <= 8:
        row = db.execute(
            text("SELECT person_id, name FROM people WHERE person_id = :id"),
            {"id": entity_id},
        ).mappings().first()
        if row:
            sources = db.execute(
                text(
                    """
                    SELECT source_type, source_id, recorded_name
                    FROM recorded_names WHERE person_id = :pid
                    LIMIT 10
                    """
                ),
                {"pid": entity_id},
            ).mappings().all()
            return Entity(
                id=row["person_id"],
                type="PERSON",
                label=row["name"],
                sources=[
                    EntitySourceRef(
                        source_type=s["source_type"],
                        source_id=s["source_id"],
                        excerpt=s["recorded_name"],
                    )
                    for s in sources
                ],
            )

    if entity_id.startswith("PH-"):
        digits = entity_id[3:]
        row = db.execute(
            text(
                """
                SELECT phone_number, person_id FROM phones
                WHERE phone_number LIKE :pattern LIMIT 1
                """
            ),
            {"pattern": f"%{digits}%"},
        ).mappings().first()
        if row:
            return Entity(
                id=entity_id,
                type="PHONE",
                label=row["phone_number"],
                sources=[
                    EntitySourceRef(
                        source_type="phones.csv",
                        source_id=row["person_id"],
                        excerpt=f"Registered to {row['person_id']}",
                    )
                ],
            )

    return None


@router.get("/{entity_id}", response_model=Entity)
def get_entity(entity_id: str, db: Session = Depends(get_db)):
    if is_neo4j_available():
        neo = get_entity_from_neo4j(entity_id)
        if neo:
            return Entity(
                id=neo["id"],
                type=neo["type"],
                label=neo["label"],
                sources=[
                    EntitySourceRef(
                        source_type=s.get("source_type") or "unknown",
                        source_id=s.get("source_id") or "",
                        excerpt=s.get("excerpt"),
                    )
                    for s in neo.get("sources", [])
                    if s.get("source_id")
                ],
                resolved_aliases=neo.get("resolved_aliases", []),
            )

    pg_entity = _entity_from_postgres(db, entity_id)
    if pg_entity:
        return pg_entity

    raise HTTPException(status_code=404, detail="Entity not found")
