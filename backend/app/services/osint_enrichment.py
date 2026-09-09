from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.audit_chain import LOOKUP_LABELS, append_audit_entry
from app.services.investigation_search import _fetch_person

SIMULATED_DISCLAIMER = (
    "SIMULATED OSINT — demo enrichments from synthetic public-record tables. "
    "Not verified government data. Suggestions are not added as confirmed graph links."
)

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


def _hit(
    *,
    title: str,
    detail: str,
    source_registry: str,
    relevance_score: int,
    link_target: str | None = None,
    match_quality: str = "none",
) -> dict[str, Any]:
    return {
        "title": title,
        "detail": detail,
        "source_registry": source_registry,
        "relevance_score": relevance_score,
        "match_quality": match_quality,
        "simulated": True,
        "source_type": "suggested",
        "link_target": link_target,
    }


def _enrich_business_registry(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    person = _fetch_person(db, entity_id) if entity_id.startswith("P") else None
    if not person:
        return [
            _hit(
                title="No registry match",
                detail=f"No corporate registry affiliation found for {label}.",
                source_registry="public_corporate_registry",
                relevance_score=0,
                match_quality="no_match",
            )
        ]

    tokens = [t.lower() for t in person.name.split() if len(t) > 2]
    rows = db.execute(
        text(
            """
            SELECT org_id, name, org_type, city FROM organizations
            WHERE city = :city
            ORDER BY org_id
            LIMIT 50
            """
        ),
        {"city": person.city},
    ).mappings().all()

    hits: list[dict[str, Any]] = []
    for org in rows:
        name_lower = org["name"].lower()
        matched_tokens = [t for t in tokens if t in name_lower]
        if not matched_tokens:
            continue
        relevance = min(85, 45 + len(matched_tokens) * 15)
        hits.append(
            _hit(
                title=f"Possible registry match: {org['name']}",
                detail=(
                    f"Synthetic registry lists {org['org_type']} in {org['city']} — "
                    f"name token overlap: {', '.join(matched_tokens)}"
                ),
                source_registry="public_corporate_registry",
                relevance_score=relevance,
                link_target=org["org_id"],
                match_quality="partial_name_token",
            )
        )

    if not hits:
        return [
            _hit(
                title="No registry match",
                detail=(
                    f"No corporate registry entry in {person.city} shares name tokens with {person.name}."
                ),
                source_registry="public_corporate_registry",
                relevance_score=0,
                match_quality="no_match",
            )
        ]
    return hits[:5]


def _enrich_court_bulletin(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    if not label.strip():
        return [
            _hit(
                title="No bulletin matches",
                detail="Entity label empty — cannot search court bulletin index.",
                source_registry="published_court_bulletin",
                relevance_score=0,
                match_quality="no_match",
            )
        ]

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
        {"cid": case_id, "pat": f"%{label}%"},
    ).mappings().all()

    if not rows:
        first_token = label.split()[0]
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
            {"cid": case_id, "pat": f"%{first_token}%"},
        ).mappings().all()

    if not rows:
        return [
            _hit(
                title="No bulletin matches",
                detail=f"No FIR text in case {case_id} mentions {label}.",
                source_registry="published_court_bulletin",
                relevance_score=0,
                match_quality="no_match",
            )
        ]

    hits = []
    for fir in rows:
        full_match = label.lower() in fir["complaint_text"].lower()
        relevance = 80 if full_match else 55
        hits.append(
            _hit(
                title=f"Case FIR reference: {fir['fir_id']}",
                detail=(
                    f"{fir['police_station']} ({fir['date']}): "
                    f"{fir['complaint_text'][:120]}…"
                ),
                source_registry="published_court_bulletin",
                relevance_score=relevance,
                link_target=fir["fir_id"],
                match_quality="full_name" if full_match else "partial_token",
            )
        )
    return hits


def _enrich_address_directory(
    db: Session, case_id: str, entity_id: str, label: str
) -> list[dict[str, Any]]:
    person = _fetch_person(db, entity_id) if entity_id.startswith("P") else None
    if not person:
        return [
            _hit(
                title="Address lookup inconclusive",
                detail="Person record not found — cannot query licensed directory.",
                source_registry="licensed_address_directory",
                relevance_score=0,
                match_quality="no_match",
            )
        ]

    return [
        _hit(
            title=f"Registered city index: {person.city}",
            detail=(
                f"Synthetic directory confirms {person.name} is indexed under city cluster "
                f"{person.city} (person_id {person.person_id})."
            ),
            source_registry="licensed_address_directory",
            relevance_score=70,
            match_quality="city_cluster",
        )
    ]


def _enrich_sanctions(db: Session, case_id: str, entity_id: str, label: str) -> list[dict[str, Any]]:
    label_lower = label.lower()
    flagged = [term for term in SANCTIONS_WATCHLIST if term in label_lower]

    if flagged:
        return [
            _hit(
                title="Watchlist token match (review required)",
                detail=f"Entity label matched demo watchlist token(s): {', '.join(flagged)}",
                source_registry="public_sanctions_watchlist",
                relevance_score=60,
                match_quality="token_match",
            )
        ]

    return [
        _hit(
            title="Clear — demo watchlist",
            detail=f"No demo sanctions tokens matched for {label}.",
            source_registry="public_sanctions_watchlist",
            relevance_score=10,
            match_quality="no_match",
        )
    ]


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

    label, _entity_type = _resolve_entity_label(db, entity_id)
    enricher = ENRICHERS[lookup_id]
    raw_hits = enricher(db, case_id, entity_id, label)

    enrichment_id = f"ENR-{uuid.uuid4().hex[:8].upper()}"
    lookup_label = LOOKUP_LABELS.get(lookup_id, lookup_id)
    audit = append_audit_entry(
        db,
        case_id=case_id,
        action=f"OSINT lookup (simulated): {lookup_label}",
        entity_id=entity_id,
        source=f"lawful_api://{lookup_id}",
        operator=f"{operator} ({operator_name})",
        lawful_basis=LOOKUP_LAWFUL_BASIS.get(lookup_id, "Public records enrichment"),
        payload={
            "enrichment_id": enrichment_id,
            "lookup_id": lookup_id,
            "simulated": True,
            "results_count": len(raw_hits),
            "disclaimer": SIMULATED_DISCLAIMER,
        },
    )

    public_hits = []
    for h in raw_hits:
        item = {k: v for k, v in h.items() if k != "link_target"}
        item["requires_officer_review"] = h.get("match_quality") != "no_match"
        public_hits.append(item)

    return {
        "enrichment_id": enrichment_id,
        "entity_id": entity_id,
        "lookup_id": lookup_id,
        "lookup_label": lookup_label,
        "case_id": case_id,
        "simulated": True,
        "disclaimer": SIMULATED_DISCLAIMER,
        "results": public_hits,
        "graph_links_added": [],
        "suggested_links": [
            h["link_target"]
            for h in raw_hits
            if h.get("link_target") and h.get("match_quality") != "no_match"
        ],
        "audit_entry_id": audit["entry_id"],
        "audit_hash": audit["entry_hash"],
    }
