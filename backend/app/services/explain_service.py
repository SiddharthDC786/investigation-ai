from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.entity_resolution import get_entity_from_neo4j
from app.services.investigation_search import (
    _case_roles,
    _fetch_person,
)
from app.services.neo4j_client import is_neo4j_available
from app.services.network_analysis import analyze_case
from app.services.provenance_service import list_entity_provenance


def build_entity_explanation(db: Session, case_id: str, entity_id: str) -> dict:
    roles = _case_roles(db, case_id)
    label = entity_id
    reasoning: list[str] = []
    citations: list[dict] = []
    relationships: list[dict] = []
    risk_factors: list[str] = []

    person = _fetch_person(db, entity_id) if entity_id.startswith("P") else None
    if person:
        label = person.name
        role = roles.get(entity_id)
        reasoning.append(
            f"{person.name} (DOB {person.dob}, {person.city}) appears in the canonical people registry."
        )
        citations.append(
            {
                "source_type": "people.csv",
                "source_id": entity_id,
                "excerpt": f"{person.name}, {person.city}",
            }
        )

        alias_rows = db.execute(
            text(
                """
                SELECT recorded_name, source_type, source_id, variant_type
                FROM recorded_names WHERE person_id = :pid
                ORDER BY record_id LIMIT 8
                """
            ),
            {"pid": entity_id},
        ).mappings().all()
        for alias in alias_rows:
            reasoning.append(
                f'Also recorded as "{alias["recorded_name"]}" ({alias["variant_type"]}) '
                f'via {alias["source_type"]} {alias["source_id"]}.'
            )
            citations.append(
                {
                    "source_type": alias["source_type"],
                    "source_id": alias["source_id"],
                    "excerpt": alias["recorded_name"],
                }
            )

        rel_rows = db.execute(
            text(
                """
                SELECT person_id_a, person_id_b, relationship_type
                FROM relationships
                WHERE case_id = :cid AND (person_id_a = :pid OR person_id_b = :pid)
                """
            ),
            {"cid": case_id, "pid": entity_id},
        ).mappings().all()
        for rel in rel_rows:
            other = rel["person_id_b"] if rel["person_id_a"] == entity_id else rel["person_id_a"]
            other_person = _fetch_person(db, other)
            other_label = other_person.name if other_person else other
            relationships.append(
                {
                    "related_entity_id": other,
                    "related_label": other_label,
                    "relationship": rel["relationship_type"],
                }
            )
            reasoning.append(
                f'Linked to {other_label} ({other}) as "{rel["relationship_type"]}" in case relationships.'
            )

        cdr_count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM cdr c
                JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
                WHERE c.case_id = :cid AND ph.person_id = :pid
                """
            ),
            {"cid": case_id, "pid": entity_id},
        ).scalar()
        if cdr_count and cdr_count > 0:
            risk_factors.append(f"{cdr_count} case-tagged call records involving registered handsets.")
            reasoning.append(
                f"Telecom analysis shows {cdr_count} CDR rows tied to this person's registered numbers."
            )
            citations.append(
                {
                    "source_type": "cdr",
                    "source_id": case_id,
                    "excerpt": f"{cdr_count} call records",
                }
            )

        if role:
            role_text = {
                "suspect": "classified as primary suspect based on relationship and call centrality",
                "handler": "classified as handler in the relationship graph",
                "facilitator": "classified as facilitator",
                "associate": "classified as associate in the network",
                "witness": "classified as witness — lower enforcement priority",
                "complainant": "classified as complainant",
            }.get(role, role)
            reasoning.append(f"Role inference: {role_text}.")
            if role in {"suspect", "handler", "facilitator"}:
                risk_factors.append(f"Active role tag: {role}.")

    if is_neo4j_available():
        neo = get_entity_from_neo4j(entity_id)
        if neo:
            for src in neo.get("sources", []):
                if src.get("source_id"):
                    citations.append(
                        {
                            "source_type": src.get("source_type") or "neo4j",
                            "source_id": src["source_id"],
                            "excerpt": src.get("excerpt"),
                        }
                    )
                    reasoning.append(
                        f"Graph provenance: mentioned in {src.get('source_type')} document {src.get('source_id')}."
                    )

    analysis = analyze_case(db, case_id)
    pr = analysis.pagerank.get(entity_id, 0.0)
    bt = analysis.betweenness.get(entity_id, 0.0)
    comm = analysis.communities.get(entity_id)
    if pr > 0.01 or bt > 0.01:
        reasoning.append(
            f"Network analytics rank this entity PageRank {pr:.4f}, betweenness {bt:.4f}."
        )
        risk_factors.append("Elevated graph centrality in the case network.")
    if comm:
        reasoning.append(f"Community detection assigns this entity to {comm}.")

    for row in list_entity_provenance(db, entity_id=entity_id, case_id=case_id):
        citations.append(
            {
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "excerpt": row["excerpt"],
                "record_id": row.get("record_id"),
                "extraction_method": row.get("extraction_method"),
                "timestamp": row.get("timestamp"),
            }
        )
        reasoning.append(
            f"Evidence trace: {row['extraction_method']} on {row['source_type']} "
            f"{row['source_id']} ({row['relationship_kind']}, {row['resolution_action']})."
        )

    fir_hits = db.execute(
        text(
            """
            SELECT fir_id, complaint_text FROM fir
            WHERE case_id = :cid AND complaint_text ILIKE :pat
            LIMIT 3
            """
        ),
        {"cid": case_id, "pat": f"%{label}%"},
    ).mappings().all()
    for fir in fir_hits:
        citations.append(
            {
                "source_type": "fir",
                "source_id": fir["fir_id"],
                "excerpt": fir["complaint_text"][:160],
            }
        )
        reasoning.append(f"Named in public FIR {fir['fir_id']} complaint text.")

    if not reasoning:
        reasoning.append(
            f"Entity {entity_id} is referenced in the investigation graph; limited structured provenance on file."
        )

    narrative = (
        f"Investigation briefing for {label} ({entity_id}) in case {case_id}: "
        + " ".join(reasoning[:4])
        + (" Additional factors noted in the reasoning chain." if len(reasoning) > 4 else "")
    )

    seen_citations: set[tuple[str, str]] = set()
    unique_citations = []
    for c in citations:
        key = (c["source_type"], c["source_id"])
        if key in seen_citations:
            continue
        seen_citations.add(key)
        unique_citations.append(c)

    return {
        "entity_id": entity_id,
        "case_id": case_id,
        "label": label,
        "narrative": narrative,
        "reasoning_steps": reasoning,
        "source_citations": unique_citations[:15],
        "relationships": relationships[:12],
        "risk_factors": risk_factors,
    }
