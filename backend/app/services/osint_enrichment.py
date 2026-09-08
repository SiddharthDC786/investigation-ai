from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.audit_chain import LOOKUP_LABELS, append_audit_entry
from app.services.entity_resolution import merge_entity_in_neo4j
from app.services.investigation_search import _fetch_person

# Synthetic public sanctions/watchlist (demo-safe — no real PII)
SANCTIONS_WATCHLIST = {
    "shell company",
    "offshore",
    "sanctioned entity",
    "blocked party",
}

LOOKUP_LAWFUL_BASIS = {
    "OSINT-01": "Public corporate registry — synthetic demo dataset (lawful open records)",
    "OSINT-02": "Published court bulletin index — public FIR metadata only",
    "OSINT-03": "Licensed address directory — city/location public index",
    "OSINT-04": "Public sanctions/watchlist screening — OFAC-style demo list",
}


def _resolve_entity_label(db: Session, entity_id: str) -> tuple[str, str]:
    if entity_id.startswith("P"):
        person = _fetch_person(db, entity_id)
        if person:
            return person.name, "person"
    if entity_id.startswith("PH-"):
        digits = entity_id[3:]
        row = db.execute(
            text(
                """
                SELECT phone_number FROM phones
                WHERE phone_number LIKE :pat LIMIT 1
                """
            ),
            {"pat": f"%{digits}%"},
        ).scalar()
        return row or entity_id, "phone"
    if entity_id.startswith("AC-"):
        acct = entity_id[3:]
        row = db.execute(
            text("SELECT account_number, bank_name FROM bank_accounts WHERE account_number = :a"),
            {"a": acct},
        ).mappings().first()
        if row:
            return f"{row['account_number']} ({row['bank_name']})", "account"
    return entity_id, "unknown"


def _enrich_business_registry(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    person = _fetch_person(db, entity_id) if entity_id.startswith("P") else None
    city = person.city if person else None

    if city:
        rows = db.execute(
            text(
                """
                SELECT org_id, name, org_type, city FROM organizations
                WHERE city = :city
                ORDER BY org_id
                LIMIT 5
                """
            ),
            {"city": city},
        ).mappings().all()
    else:
        rows = db.execute(
            text(
                """
                SELECT org_id, name, org_type, city FROM organizations
                ORDER BY org_id
                LIMIT 5
                """
            )
        ).mappings().all()
    for org in rows:
        hits.append(
            {
                "title": f"Registry match: {org['name']}",
                "detail": f"{org['org_type']} registered in {org['city']} (org_id {org['org_id']})",
                "source_registry": "public_corporate_registry",
                "confidence": 0.78 if city and org["city"] == city else 0.55,
                "link_target": org["org_id"],
            }
        )
    if not hits:
        hits.append(
            {
                "title": "No public registry affiliation",
                "detail": f"No corporate registry link found for {label} in public index.",
                "source_registry": "public_corporate_registry",
                "confidence": 0.0,
            }
        )
    return hits


def _enrich_court_bulletin(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    pattern = f"%{label.split()[0]}%" if label else "%"
    rows = db.execute(
        text(
            """
            SELECT fir_id, police_station, complaint_text, date
            FROM fir
            WHERE case_id = :cid AND complaint_text ILIKE :pat
            ORDER BY date DESC
            LIMIT 5
            """
        ),
        {"cid": case_id, "pat": pattern},
    ).mappings().all()

    if not rows:
        rows = db.execute(
            text(
                """
                SELECT fir_id, police_station, complaint_text, date
                FROM fir WHERE case_id = :cid ORDER BY date DESC LIMIT 3
                """
            ),
            {"cid": case_id},
        ).mappings().all()

    hits = []
    for fir in rows:
        hits.append(
            {
                "title": f"Court bulletin ref: {fir['fir_id']}",
                "detail": (
                    f"{fir['police_station']} ({fir['date']}): "
                    f"{fir['complaint_text'][:120]}…"
                ),
                "source_registry": "published_court_bulletin",
                "confidence": 0.82 if label.lower() in fir["complaint_text"].lower() else 0.45,
                "link_target": fir["fir_id"],
            }
        )
    return hits or [
        {
            "title": "No bulletin matches",
            "detail": "No public court bulletin entries matched this entity.",
            "source_registry": "published_court_bulletin",
            "confidence": 0.0,
        }
    ]


def _enrich_address_directory(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    person = _fetch_person(db, entity_id) if entity_id.startswith("P") else None
    if person:
        locs = db.execute(
            text(
                """
                SELECT location_id, name, city FROM locations
                WHERE city = :city ORDER BY location_id LIMIT 5
                """
            ),
            {"city": person.city},
        ).mappings().all()
        for loc in locs:
            hits.append(
                {
                    "title": f"Directory: {loc['name']}",
                    "detail": f"Licensed directory lists {loc['name']} in {loc['city']}",
                    "source_registry": "licensed_address_directory",
                    "confidence": 0.74,
                    "link_target": loc["location_id"],
                }
            )
        hits.insert(
            0,
            {
                "title": f"Registered city: {person.city}",
                "detail": f"Public index confirms residence cluster for {person.name}",
                "source_registry": "licensed_address_directory",
                "confidence": 0.88,
            },
        )
    return hits or [
        {
            "title": "Address lookup inconclusive",
            "detail": "Entity not found in licensed public directory index.",
            "source_registry": "licensed_address_directory",
            "confidence": 0.0,
        }
    ]


def _enrich_sanctions(db: Session, case_id: str, entity_id: str, label: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    label_lower = label.lower()
    flagged = [term for term in SANCTIONS_WATCHLIST if term in label_lower]

    org_rows = db.execute(
        text("SELECT org_id, name, org_type FROM organizations LIMIT 200")
    ).mappings().all()
    for org in org_rows:
        name_lower = org["name"].lower()
        if any(term in name_lower for term in SANCTIONS_WATCHLIST):
            hits.append(
                {
                    "title": f"Watchlist proximity: {org['name']}",
                    "detail": f"Public watchlist pattern match near entity network ({org['org_type']})",
                    "source_registry": "public_sanctions_watchlist",
                    "confidence": 0.61,
                    "link_target": org["org_id"],
                }
            )

    if flagged:
        hits.insert(
            0,
            {
                "title": "Sanctions screening flag",
                "detail": f"Entity label matched public watchlist token(s): {', '.join(flagged)}",
                "source_registry": "public_sanctions_watchlist",
                "confidence": 0.71,
            },
        )

    if not hits:
        hits.append(
            {
                "title": "Clear — public watchlist",
                "detail": f"No matches on public sanctions index for {label}",
                "source_registry": "public_sanctions_watchlist",
                "confidence": 0.95,
            }
        )
    return hits


ENRICHERS = {
    "OSINT-01": _enrich_business_registry,
    "OSINT-02": _enrich_court_bulletin,
    "OSINT-03": _enrich_address_directory,
    "OSINT-04": _enrich_sanctions,
}


def run_osint_enrichment(
    db: Session,
    *,
    case_id: str,
    entity_id: str,
    lookup_id: str,
    operator: str,
    operator_name: str,
) -> dict[str, Any]:
    if lookup_id not in ENRICHERS:
        raise ValueError(f"Unknown lookup_id: {lookup_id}")

    label, entity_type = _resolve_entity_label(db, entity_id)
    enricher = ENRICHERS[lookup_id]
    raw_hits = enricher(db, case_id, entity_id, label)

    enrichment_id = f"ENR-{uuid.uuid4().hex[:8].upper()}"
    graph_links: list[str] = []

    merge_entity_in_neo4j(
        entity_id=entity_id,
        entity_type=entity_type if entity_type in {"person", "phone", "account"} else "person",
        label=label,
        case_id=case_id,
        source_type="osint",
        source_id=enrichment_id,
        excerpt=f"OSINT {lookup_id} enrichment on {label}",
        action="enriched",
    )

    for hit in raw_hits:
        target = hit.get("link_target")
        if not target:
            continue
        target_type = (
            "organization"
            if str(target).startswith("O")
            else "location"
            if str(target).startswith("L")
            else "person"
        )
        graph_links.append(f"{entity_id}->{target}")
        merge_entity_in_neo4j(
            entity_id=str(target),
            entity_type=target_type,
            label=hit["title"].replace("Registry match: ", "").replace("Directory: ", "")[:128],
            case_id=case_id,
            source_type="osint",
            source_id=enrichment_id,
            excerpt=hit["detail"][:500],
            action="linked",
        )
        from app.services.neo4j_client import get_session, is_neo4j_available

        if is_neo4j_available():
            with get_session() as session:
                session.run(
                    """
                    MATCH (a {id: $from_id}), (b {id: $to_id})
                    MERGE (a)-[:ENRICHED_WITH {lookup_id: $lookup}]->(b)
                    """,
                    {
                        "from_id": entity_id,
                        "to_id": str(target),
                        "lookup": lookup_id,
                    },
                ).consume()

    lookup_label = LOOKUP_LABELS.get(lookup_id, lookup_id)
    audit = append_audit_entry(
        db,
        case_id=case_id,
        action=f"OSINT lookup: {lookup_label}",
        entity_id=entity_id,
        source=f"lawful_api://{lookup_id}",
        operator=f"{operator} ({operator_name})",
        lawful_basis=LOOKUP_LAWFUL_BASIS.get(lookup_id, "Public records enrichment"),
        payload={
            "enrichment_id": enrichment_id,
            "lookup_id": lookup_id,
            "results_count": len(raw_hits),
            "graph_links": graph_links,
        },
    )

    return {
        "enrichment_id": enrichment_id,
        "entity_id": entity_id,
        "lookup_id": lookup_id,
        "lookup_label": lookup_label,
        "case_id": case_id,
        "results": [
            {k: v for k, v in h.items() if k != "link_target"} for h in raw_hits
        ],
        "graph_links_added": graph_links,
        "audit_entry_id": audit["entry_id"],
        "audit_hash": audit["entry_hash"],
    }
