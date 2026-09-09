from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date
from typing import Any

from rapidfuzz import fuzz
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.investigation import (
    Connection,
    InvestigationEntity,
    InvestigationSearchResult,
    NameMatchHit,
    NameMatchType,
    RelatedPersonHit,
)
from app.services.fulltext_search import cross_source_search

RELATIONSHIP_ROLE_MAP: dict[str, str] = {
    "facilitator": "facilitator",
    "handler": "handler",
    "associate": "associate",
    "family": "associate",
    "business_partner": "associate",
    "employer": "facilitator",
    "tenant": "witness",
}

ROLE_SORT_PRIORITY: dict[str, int] = {
    "suspect": 0,
    "handler": 1,
    "associate": 2,
    "facilitator": 3,
    "witness": 4,
    "complainant": 5,
}


@dataclass
class PersonRow:
    person_id: str
    name: str
    dob: date
    gender: str
    city: str


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _age_from_dob(dob: date, today: date | None = None) -> int:
    ref = today or date.today()
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years


def _person_entity_id(person_id: str) -> str:
    return person_id


def _phone_entity_id(phone_number: str) -> str:
    digits = "".join(c for c in phone_number if c.isdigit())
    return f"PH-{digits}"


def _account_entity_id(account_number: str) -> str:
    return f"AC-{account_number}"


def _score_person(case_id: str, person_id: str, role: str | None) -> tuple[int, str]:
    base = {"suspect": 92, "handler": 84, "facilitator": 71, "associate": 78, "witness": 34, "complainant": 30}
    score = base.get(role or "", 45)
    severity: str = "high" if score >= 75 else "medium" if score >= 50 else "low"
    return score, severity


def _fetch_person(db: Session, person_id: str) -> PersonRow | None:
    row = db.execute(
        text(
            "SELECT person_id, name, dob, gender, city FROM people WHERE person_id = :pid"
        ),
        {"pid": person_id},
    ).mappings().first()
    if not row:
        return None
    return PersonRow(**row)


def _fetch_aliases(db: Session, person_id: str) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT recorded_name FROM recorded_names
            WHERE person_id = :pid AND is_erroneous = true
            ORDER BY record_id
            """
        ),
        {"pid": person_id},
    ).scalars().all()
    return list(rows)


def _fetch_subtitle(db: Session, person_id: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT recorded_name, variant_type FROM recorded_names
            WHERE person_id = :pid
            ORDER BY record_id
            LIMIT 1
            """
        ),
        {"pid": person_id},
    ).mappings().first()
    if not row:
        return None
    return f"Also recorded as {row['recorded_name']} ({row['variant_type']})"


def _case_roles(db: Session, case_id: str) -> dict[str, str]:
    """Infer display roles from relationships + CDR centrality (public tables only)."""
    rel_rows = db.execute(
        text(
            """
            SELECT person_id_a AS pid, relationship_type FROM relationships WHERE case_id = :cid
            UNION ALL
            SELECT person_id_b, relationship_type FROM relationships WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()

    roles: dict[str, str] = {}
    for row in rel_rows:
        mapped = RELATIONSHIP_ROLE_MAP.get(row["relationship_type"], "associate")
        roles.setdefault(row["pid"], mapped)

    cdr_row = db.execute(
        text(
            """
            SELECT ph.person_id, COUNT(*) AS cnt
            FROM cdr c
            JOIN phones ph
              ON ph.phone_number = c.caller_phone OR ph.phone_number = c.receiver_phone
            WHERE c.case_id = :cid
            GROUP BY ph.person_id
            ORDER BY cnt DESC
            LIMIT 1
            """
        ),
        {"cid": case_id},
    ).mappings().first()
    if cdr_row:
        roles[cdr_row["person_id"]] = "suspect"

    return roles


def _build_person_entity(
    db: Session,
    case_id: str,
    person: PersonRow,
    roles: dict[str, str],
) -> InvestigationEntity:
    role = roles.get(person.person_id)
    if role and role not in {
        "suspect",
        "associate",
        "facilitator",
        "witness",
        "complainant",
        "handler",
    }:
        role = None
    score, severity = _score_person(case_id, person.person_id, role)
    aliases = _fetch_aliases(db, person.person_id)
    subtitle = _fetch_subtitle(db, person.person_id)

    phone_rows = db.execute(
        text(
            "SELECT phone_number FROM phones WHERE person_id = :pid ORDER BY phone_id LIMIT 3"
        ),
        {"pid": person.person_id},
    ).scalars().all()
    connections = [
        Connection(
            targetId=_phone_entity_id(num),
            reason="Registered handset",
        )
        for num in phone_rows
    ]

    explainability = [
        f"Identity record: {person.name}, DOB {person.dob}, {person.city}.",
    ]
    if aliases:
        explainability.append(
            f"Known name variants in recorded_names: {', '.join(aliases[:3])}."
        )

    return InvestigationEntity(
        id=_person_entity_id(person.person_id),
        label=person.name,
        type="person",
        role=role,  # type: ignore[arg-type]
        subtitle=subtitle,
        aliases=aliases,
        score=score,
        severity=severity,  # type: ignore[arg-type]
        sources=["people.csv", "recorded_names"],
        explainability=explainability,
        connections=connections,
        metadata={
            "person_id": person.person_id,
            "dob": str(person.dob),
            "age": str(_age_from_dob(person.dob)),
            "city": person.city,
            "gender": person.gender,
        },
    )


def _classify_name_match(query: str, person: PersonRow, aliases: list[str]) -> NameMatchHit | None:
    q = _norm(query)
    if not q:
        return None

    variants: list[tuple[str, NameMatchType]] = [(person.name, "exact")]
    for alias in aliases:
        variants.append((alias, "alias"))

    best: NameMatchHit | None = None
    for variant, default_type in variants:
        v = _norm(variant)
        if v == q:
            hit_type: NameMatchType = "exact"
            confidence = 100
        elif q in v or v in q:
            hit_type = "partial"
            confidence = 88
        else:
            ratio = fuzz.ratio(q, v)
            if ratio >= 92:
                hit_type = "exact"
                confidence = int(ratio)
            elif ratio >= 85:
                hit_type = "typo"
                confidence = int(ratio)
            elif any(
                fuzz.ratio(tok, vt) >= 85
                for tok in q.split()
                for vt in v.split()
                if len(tok) >= 3
            ):
                hit_type = "typo"
                confidence = 82
            else:
                continue

        entity_stub = InvestigationEntity(
            id=person.person_id,
            label=person.name,
            type="person",
            score=50,
            severity="medium",
            sources=[],
            explainability=[],
            connections=[],
            metadata={
                "person_id": person.person_id,
                "dob": str(person.dob),
                "city": person.city,
            },
        )
        candidate = NameMatchHit(
            entity=entity_stub,
            matchType=hit_type,
            matchedOn=variant,
            confidence=confidence,
        )
        if best is None or candidate.confidence > best.confidence:
            best = candidate

    return best


def _find_name_candidates(db: Session, case_id: str, name_query: str) -> list[NameMatchHit]:
    q = name_query.strip()
    if not q:
        return []

    rows = db.execute(
        text(
            """
            SELECT DISTINCT p.person_id, p.name, p.dob, p.gender, p.city
            FROM people p
            LEFT JOIN recorded_names rn ON rn.person_id = p.person_id
            WHERE p.name ILIKE :pattern OR rn.recorded_name ILIKE :pattern
            """
        ),
        {"pattern": f"%{q}%"},
    ).mappings().all()

    # Cross-source full-text (Neo4j or PostgreSQL FIR/chat fallback)
    fts_hits = cross_source_search(db, case_id, q, limit=15)
    for hit in fts_hits:
        if hit.get("entity_type") != "person":
            continue
        pid = hit.get("id", "")
        if not pid.startswith("P"):
            continue
        if any(r["person_id"] == pid for r in rows):
            continue
        person = _fetch_person(db, pid)
        if person:
            rows.append(
                {
                    "person_id": person.person_id,
                    "name": person.name,
                    "dob": person.dob,
                    "gender": person.gender,
                    "city": person.city,
                }
            )

    hits: list[NameMatchHit] = []
    seen: set[str] = set()
    roles = _case_roles(db, case_id)

    for row in rows:
        pid = row["person_id"]
        if pid in seen:
            continue
        seen.add(pid)
        person = PersonRow(**row)
        aliases = _fetch_aliases(db, pid)
        hit = _classify_name_match(q, person, aliases)
        if not hit:
            continue
        full = _build_person_entity(db, case_id, person, roles)
        if any(h.get("source_type") == "fir" for h in fts_hits):
            full.explainability.append(
                "Also matched via cross-source full-text search (FIR/chat documents)."
            )
            full.sources.append("fir")
        hit.entity = full
        hits.append(hit)

    hits.sort(key=lambda h: (-h.confidence, -h.entity.score))
    return hits


def _person_ids_from_area(db: Session, area_query: str) -> list[str]:
    aq = _norm(area_query)
    if not aq:
        return []
    rows = db.execute(
        text(
            """
            SELECT person_id FROM people
            WHERE LOWER(city) LIKE :pattern OR LOWER(name) LIKE :pattern
            """
        ),
        {"pattern": f"%{aq}%"},
    ).scalars().all()
    return [r for r in rows if r]


def _person_ids_from_gender(db: Session, gender_query: str) -> list[str]:
    gq = _norm(gender_query)
    if not gq:
        return []
    rows = db.execute(
        text(
            """
            SELECT person_id FROM people
            WHERE LOWER(gender) LIKE :pattern
            """
        ),
        {"pattern": f"%{gq}%"},
    ).scalars().all()
    return [r for r in rows if r]


def _person_ids_from_age(db: Session, age_query: str) -> list[str]:
    raw = age_query.strip()
    if not raw or not raw.isdigit():
        return []
    target = int(raw)
    rows = db.execute(text("SELECT person_id, dob FROM people")).mappings().all()
    return [r["person_id"] for r in rows if _age_from_dob(r["dob"]) == target]


_FATHER_KEYWORDS = (
    "s/o",
    "son of",
    "d/o",
    "daughter of",
    "w/o",
    "wife of",
    "father",
    "father's name",
    "fathers name",
)


def _fir_has_father_data(db: Session, case_id: str) -> bool:
    rows = db.execute(
        text("SELECT complaint_text FROM fir WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalars().all()
    for text_blob in rows:
        if not text_blob:
            continue
        lower = text_blob.lower()
        if any(kw in lower for kw in _FATHER_KEYWORDS):
            return True
    return False


def _person_ids_from_father_name(db: Session, case_id: str, father_query: str) -> list[str]:
    """Match father-name phrases in FIR text and link to persons mentioned in the same FIR."""
    fq = _norm(father_query)
    if not fq:
        return []

    fir_rows = db.execute(
        text("SELECT fir_id, complaint_text FROM fir WHERE case_id = :cid"),
        {"cid": case_id},
    ).mappings().all()
    people_rows = db.execute(text("SELECT person_id, name FROM people")).mappings().all()
    name_by_id = {r["person_id"]: r["name"] for r in people_rows}

    matched: set[str] = set()
    for fir in fir_rows:
        blob = fir.get("complaint_text") or ""
        lower = blob.lower()
        if fq not in lower:
            continue
        for pid, pname in name_by_id.items():
            if _norm(pname) and _norm(pname) in _norm(blob):
                matched.add(pid)
    return list(matched)


def _intersect_person_ids(id_sets: list[set[str]]) -> set[str]:
    if not id_sets:
        return set()
    result = id_sets[0].copy()
    for s in id_sets[1:]:
        result &= s
    return result


def _person_ids_from_phone(db: Session, phone_query: str) -> list[str]:
    digits = "".join(c for c in phone_query if c.isdigit())
    if not digits:
        return []
    rows = db.execute(
        text(
            """
            SELECT DISTINCT person_id FROM phones
            WHERE phone_number LIKE :pattern
            UNION
            SELECT DISTINCT person_id FROM recorded_phones
            WHERE recorded_phone LIKE :pattern AND person_id IS NOT NULL
            """
        ),
        {"pattern": f"%{digits}%"},
    ).scalars().all()
    return [r for r in rows if r]


def _apply_filters(
    db: Session,
    case_id: str,
    candidates: list[InvestigationEntity],
    *,
    area: str,
    phone: str,
    role: str,
    selected_person_id: str | None,
    face_person_id: str | None,
) -> list[InvestigationEntity]:
    if selected_person_id:
        person = _fetch_person(db, selected_person_id)
        if not person:
            return []
        roles = _case_roles(db, case_id)
        return [_build_person_entity(db, case_id, person, roles)]

    result = candidates

    if area.strip():
        aq = _norm(area)
        result = [
            e
            for e in result
            if aq in _norm(e.metadata.get("city", "")) or aq in _norm(e.label)
        ]

    if role and role != "all":
        result = [e for e in result if e.role == role]

    if phone.strip():
        phone_ids = set(_person_ids_from_phone(db, phone))
        result = [e for e in result if e.metadata.get("person_id") in phone_ids]

    if face_person_id:
        result = [e for e in result if e.id == face_person_id]

    return result


def _build_adjacency(db: Session, case_id: str) -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = {}

    def add(a: str, b: str, reason: str) -> None:
        adj.setdefault(a, []).append((b, reason))
        adj.setdefault(b, []).append((a, reason))

    rels = db.execute(
        text(
            """
            SELECT person_id_a, person_id_b, relationship_type
            FROM relationships WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for rel in rels:
        add(rel["person_id_a"], rel["person_id_b"], rel["relationship_type"])

    phone_rows = db.execute(
        text("SELECT phone_id, phone_number, person_id FROM phones"),
    ).mappings().all()
    phone_by_num = {r["phone_number"]: r for r in phone_rows}
    person_to_phones: dict[str, list[str]] = {}
    for r in phone_rows:
        pid = _person_entity_id(r["person_id"])
        ph_id = _phone_entity_id(r["phone_number"])
        person_to_phones.setdefault(pid, []).append(ph_id)
        add(pid, ph_id, "Registered handset")

    cdr_rows = db.execute(
        text(
            """
            SELECT caller_phone, receiver_phone FROM cdr
            WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for cdr in cdr_rows:
        caller = phone_by_num.get(cdr["caller_phone"])
        receiver = phone_by_num.get(cdr["receiver_phone"])
        if not caller or not receiver:
            continue
        a = _person_entity_id(caller["person_id"])
        b = _person_entity_id(receiver["person_id"])
        add(a, b, "CDR contact")
        add(a, _phone_entity_id(cdr["receiver_phone"]), "Called number")
        add(b, _phone_entity_id(cdr["caller_phone"]), "Incoming call")

    acct_rows = db.execute(
        text("SELECT account_id, account_number, person_id, bank_name FROM bank_accounts"),
    ).mappings().all()
    for acct in acct_rows:
        pid = _person_entity_id(acct["person_id"])
        acct_id = _account_entity_id(acct["account_number"])
        add(pid, acct_id, "Account holder")

    txns = db.execute(
        text(
            """
            SELECT sender_account, receiver_account FROM transactions
            WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    acct_by_num = {a["account_number"]: a for a in acct_rows}
    for txn in txns:
        sender = acct_by_num.get(txn["sender_account"])
        receiver = acct_by_num.get(txn["receiver_account"])
        if sender and receiver:
            add(
                _person_entity_id(sender["person_id"]),
                _person_entity_id(receiver["person_id"]),
                "Transaction chain",
            )

    return adj


def _find_related_people(
    db: Session,
    case_id: str,
    seed_person_ids: list[str],
    roles: dict[str, str],
    max_hops: int = 3,
) -> list[RelatedPersonHit]:
    adj = _build_adjacency(db, case_id)
    seen = set(seed_person_ids)
    results: list[RelatedPersonHit] = []

    for seed in seed_person_ids:
        frontier: deque[tuple[str, int, str]] = deque([(seed, 0, "Search match")])
        visited = {seed}

        while frontier:
            node_id, hops, reason = frontier.popleft()
            if hops >= max_hops:
                continue
            for neighbor, edge_reason in adj.get(node_id, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                next_hops = hops + 1
                person = _fetch_person(db, neighbor)
                if person and neighbor not in seen:
                    seen.add(neighbor)
                    entity = _build_person_entity(db, case_id, person, roles)
                    results.append(
                        RelatedPersonHit(
                            entity=entity,
                            hops=next_hops,
                            connectionReason=edge_reason,
                        )
                    )
                frontier.append((neighbor, next_hops, edge_reason))

    results.sort(
        key=lambda r: (
            r.hops,
            ROLE_SORT_PRIORITY.get(r.entity.role or "", 9),
            -r.entity.score,
        )
    )
    return results[:25]


def _linked_records(
    db: Session,
    person_ids: set[str],
    adj: dict[str, list[tuple[str, str]]],
    *,
    max_items: int = 8,
) -> list[InvestigationEntity]:
    phones: list[InvestigationEntity] = []
    accounts: list[InvestigationEntity] = []
    seen: set[str] = set()

    for pid in person_ids:
        for neighbor, reason in adj.get(pid, []):
            if neighbor in seen or neighbor.startswith("P"):
                continue
            seen.add(neighbor)
            if neighbor.startswith("PH-"):
                digits = neighbor[3:]
                row = db.execute(
                    text(
                        "SELECT phone_number, person_id FROM phones WHERE phone_number LIKE :d LIMIT 1"
                    ),
                    {"d": f"%{digits}%"},
                ).mappings().first()
                if row:
                    phones.append(
                        InvestigationEntity(
                            id=neighbor,
                            label=row["phone_number"],
                            type="phone",
                            subtitle=f"Registered to {row['person_id']}",
                            score=60,
                            severity="medium",
                            sources=["phones.csv"],
                            explainability=[reason],
                            connections=[],
                            metadata={"person_id": row["person_id"]},
                        )
                    )
            elif neighbor.startswith("AC-"):
                acct_num = neighbor[3:]
                row = db.execute(
                    text(
                        """
                        SELECT account_number, person_id, bank_name FROM bank_accounts
                        WHERE account_number = :num
                        """
                    ),
                    {"num": acct_num},
                ).mappings().first()
                if row:
                    accounts.append(
                        InvestigationEntity(
                            id=neighbor,
                            label=row["account_number"],
                            type="account",
                            subtitle=row["bank_name"],
                            score=65,
                            severity="medium",
                            sources=["bank_accounts.csv"],
                            explainability=[reason],
                            connections=[],
                            metadata={"person_id": row["person_id"], "bank": row["bank_name"]},
                        )
                    )

    remaining = max(0, max_items - len(phones))
    return phones + accounts[:remaining]


def run_investigation_search(
    db: Session,
    case_id: str,
    *,
    name: str = "",
    phone: str = "",
    area: str = "",
    role: str = "all",
    gender: str = "",
    age: str = "",
    father_name: str = "",
    selected_person_id: str | None = None,
    face_person_id: str | None = None,
) -> InvestigationSearchResult:
    has_query = any(
        [
            name.strip(),
            phone.strip(),
            area.strip(),
            gender.strip(),
            age.strip(),
            father_name.strip(),
            selected_person_id,
            face_person_id,
        ]
    )
    if not has_query:
        return InvestigationSearchResult(
            nameCandidates=[],
            needsDisambiguation=False,
            primaryMatches=[],
            relatedPeople=[],
            linkedRecords=[],
        )

    roles = _case_roles(db, case_id)
    message: str | None = None

    if selected_person_id:
        person = _fetch_person(db, selected_person_id)
        primary_matches = (
            [_build_person_entity(db, case_id, person, roles)] if person else []
        )
        name_candidates = _find_name_candidates(db, case_id, name) if name.strip() else []
        if name.strip():
            match_ids = {e.id for e in primary_matches}
            name_candidates = [h for h in name_candidates if h.entity.id in match_ids]
        return _finalize_search_result(
            db,
            case_id,
            roles,
            name_candidates,
            primary_matches,
            role,
            message,
        )

    if father_name.strip() and not _fir_has_father_data(db, case_id):
        return InvestigationSearchResult(
            nameCandidates=[],
            needsDisambiguation=False,
            primaryMatches=[],
            relatedPeople=[],
            linkedRecords=[],
            message="Father name is not available in the FIR database for this case.",
        )

    id_sets: list[set[str]] = []
    name_candidates: list[NameMatchHit] = []

    if name.strip():
        name_candidates = _find_name_candidates(db, case_id, name)
        name_ids = {h.entity.id for h in name_candidates}
        if name_ids:
            id_sets.append(name_ids)

    if area.strip():
        area_ids = set(_person_ids_from_area(db, area))
        if area_ids:
            id_sets.append(area_ids)

    if phone.strip():
        phone_ids = set(_person_ids_from_phone(db, phone))
        if not phone_ids:
            return InvestigationSearchResult(
                nameCandidates=name_candidates,
                needsDisambiguation=False,
                primaryMatches=[],
                relatedPeople=[],
                linkedRecords=[],
                message="No data available — no person is registered with this phone number.",
            )
        id_sets.append(phone_ids)

    if gender.strip():
        gender_ids = set(_person_ids_from_gender(db, gender))
        if gender_ids:
            id_sets.append(gender_ids)

    if age.strip():
        age_ids = set(_person_ids_from_age(db, age))
        if age_ids:
            id_sets.append(age_ids)

    if father_name.strip():
        father_ids = set(_person_ids_from_father_name(db, case_id, father_name))
        if father_ids:
            id_sets.append(father_ids)

    if face_person_id:
        id_sets.append({face_person_id})

    if not id_sets:
        return InvestigationSearchResult(
            nameCandidates=name_candidates,
            needsDisambiguation=False,
            primaryMatches=[],
            relatedPeople=[],
            linkedRecords=[],
            message=message,
        )

    final_ids = _intersect_person_ids(id_sets)
    primary_matches: list[InvestigationEntity] = []
    for pid in sorted(final_ids):
        person = _fetch_person(db, pid)
        if person:
            primary_matches.append(_build_person_entity(db, case_id, person, roles))

    if role and role != "all":
        primary_matches = [e for e in primary_matches if e.role == role]

    if name.strip():
        primary_id_set = {e.id for e in primary_matches}
        name_candidates = [h for h in name_candidates if h.entity.id in primary_id_set]
        name_candidates.sort(
            key=lambda h: (
                ROLE_SORT_PRIORITY.get(h.entity.role or "", 9),
                -h.confidence,
                -h.entity.score,
            )
        )

    if not primary_matches and not message:
        message = "No data available — no person matches all search filters."

    return _finalize_search_result(
        db,
        case_id,
        roles,
        name_candidates,
        primary_matches,
        role,
        message,
    )


def _finalize_search_result(
    db: Session,
    case_id: str,
    roles: dict[str, str],
    name_candidates: list[NameMatchHit],
    primary_matches: list[InvestigationEntity],
    role: str,
    message: str | None,
) -> InvestigationSearchResult:
    needs_disambiguation = len(primary_matches) > 1

    related: list[RelatedPersonHit] = []
    linked: list[InvestigationEntity] = []

    if not needs_disambiguation and len(primary_matches) == 1:
        seed_ids = [primary_matches[0].id]
        related = _find_related_people(db, case_id, seed_ids, roles)
        if role and role != "all":
            related = [r for r in related if r.entity.role == role]
        adj = _build_adjacency(db, case_id)
        person_ids = {primary_matches[0].id}
        linked = _linked_records(db, person_ids, adj)

    return InvestigationSearchResult(
        nameCandidates=name_candidates,
        needsDisambiguation=needs_disambiguation,
        primaryMatches=primary_matches,
        relatedPeople=related,
        linkedRecords=linked,
        message=message,
    )
