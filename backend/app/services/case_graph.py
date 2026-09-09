from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.graph import GraphLink, GraphResponse
from app.schemas.investigation import InvestigationEntity
from app.services.investigation_search import (
    _account_entity_id,
    _build_person_entity,
    _case_roles,
    _fetch_person,
    _phone_entity_id,
    _score_person,
)

# Core cast for CASE0001 demo narrative (CDR-heavy ring not in relationships table)
NARRATIVE_ROLES: dict[str, dict[str, str]] = {
    "CASE0001": {
        "P00014": "suspect",
        "P00052": "associate",
        "P00055": "facilitator",
        "P00089": "handler",
        "P00062": "witness",
    },
}


def _person_ids_for_case(db: Session, case_id: str) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT person_id_a AS pid FROM relationships WHERE case_id = :cid
            UNION
            SELECT person_id_b FROM relationships WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).scalars().all()
    return {r for r in rows if r}


def _resolve_focus_person(db: Session, case_id: str, center_person_id: str | None) -> str:
    if center_person_id and _fetch_person(db, center_person_id):
        return center_person_id

    row = db.execute(
        text(
            """
            SELECT ph.person_id
            FROM cdr c
            JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
            WHERE c.case_id = :cid
            GROUP BY ph.person_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """
        ),
        {"cid": case_id},
    ).scalar()
    if row:
        return row

    roles = NARRATIVE_ROLES.get(case_id, {})
    for pid, role in roles.items():
        if role == "suspect" and _fetch_person(db, pid):
            return pid
    return center_person_id or "P00014"


def _cdr_person_edges(db: Session, case_id: str) -> list[tuple[str, str, int]]:
    rows = db.execute(
        text(
            """
            SELECT p1.person_id AS a, p2.person_id AS b, COUNT(*) AS cnt
            FROM cdr c
            JOIN phones p1 ON p1.phone_number = c.caller_phone
            JOIN phones p2 ON p2.phone_number = c.receiver_phone
            WHERE c.case_id = :cid AND p1.person_id <> p2.person_id
            GROUP BY p1.person_id, p2.person_id
            HAVING COUNT(*) >= 3
            ORDER BY cnt DESC
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    return [(r["a"], r["b"], int(r["cnt"])) for r in rows]


def _shared_phones(db: Session, case_id: str, person_ids: set[str]) -> list[tuple[str, str, list[str]]]:
    """Return (phone_number, phone_entity_id, [person_ids]) for phones linking 2+ people."""
    rows = db.execute(
        text(
            """
            SELECT ph.phone_number, ph.person_id
            FROM cdr c
            JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
            WHERE c.case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()

    phone_to_people: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["person_id"] in person_ids:
            phone_to_people[row["phone_number"]].add(row["person_id"])

    out: list[tuple[str, str, list[str]]] = []
    for number, people in phone_to_people.items():
        if len(people) >= 2:
            out.append((number, _phone_entity_id(number), sorted(people)))
    out.sort(key=lambda x: -len(x[2]))
    return out[:3]


def _apply_narrative_role(case_id: str, person_id: str, roles: dict[str, str]) -> str | None:
    override = NARRATIVE_ROLES.get(case_id, {}).get(person_id)
    if override:
        return override
    return roles.get(person_id)


def _build_person_node(
    db: Session,
    case_id: str,
    person_id: str,
    roles: dict[str, str],
    *,
    is_focus: bool = False,
) -> InvestigationEntity | None:
    person = _fetch_person(db, person_id)
    if not person:
        return None
    entity = _build_person_entity(db, case_id, person, roles)
    role = _apply_narrative_role(case_id, person_id, roles)
    if role:
        entity.role = role  # type: ignore[assignment]
        score, severity = _score_person(case_id, person_id, role)
        entity.score = score + (8 if is_focus else 0)
        entity.severity = severity  # type: ignore[assignment]
    if is_focus:
        entity.subtitle = (entity.subtitle or "") + " · Primary suspect" if entity.subtitle else "Primary suspect in this case"
    return entity


def build_investigation_map(
    db: Session,
    case_id: str,
    center_person_id: str | None = None,
) -> GraphResponse:
    focus = _resolve_focus_person(db, case_id, center_person_id)
    roles = _case_roles(db, case_id)
    cdr_edges = _cdr_person_edges(db, case_id)

    included: set[str] = {focus}
    for a, b, cnt in cdr_edges:
        if a == focus or b == focus:
            included.add(a)
            included.add(b)

    # Second hop — strong links between first-ring contacts
    for a, b, cnt in cdr_edges:
        if cnt >= 20 and (a in included or b in included):
            included.add(a)
            included.add(b)

    # Cap size but always keep focus + top contacts by call volume to focus
    contact_weights: dict[str, int] = defaultdict(int)
    for a, b, cnt in cdr_edges:
        if a == focus:
            contact_weights[b] += cnt
        if b == focus:
            contact_weights[a] += cnt
    for pid, _ in sorted(contact_weights.items(), key=lambda x: -x[1])[:8]:
        included.add(pid)

    if len(included) > 14:
        keep = {focus, *list(sorted(contact_weights, key=contact_weights.get, reverse=True)[:10])}
        included = keep

    shared = _shared_phones(db, case_id, included)
    nodes: dict[str, InvestigationEntity] = {}
    links: list[GraphLink] = []
    seen_links: set[tuple[str, str]] = set()

    def add_link(source: str, target: str, label: str, weight: float = 1.0) -> None:
        key = (source, target) if source < target else (target, source)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append(GraphLink(source=source, target=target, label=label, weight=weight))

    for pid in included:
        node = _build_person_node(db, case_id, pid, roles, is_focus=(pid == focus))
        if node:
            nodes[pid] = node

    for a, b, cnt in cdr_edges:
        if a in included and b in included:
            add_link(a, b, f"{cnt} calls", float(cnt))

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
        a, b = rel["person_id_a"], rel["person_id_b"]
        if a in included and b in included:
            add_link(a, b, rel["relationship_type"], 2.0)

    for number, ph_id, people in shared:
        if ph_id in nodes:
            continue
        nodes[ph_id] = InvestigationEntity(
            id=ph_id,
            label=f"…{number[-4:]}",
            type="phone",
            subtitle="Shared contact number — links multiple suspects",
            score=88,
            severity="high",
            sources=["cdr fusion"],
            explainability=["Multiple persons in this case called the same number — hidden link."],
            connections=[],
            metadata={"phone_number": number, "bridge": "true"},
        )
        for pid in people:
            if pid in included:
                add_link(pid, ph_id, "called", 3.0)

    focus_name = nodes[focus].label if focus in nodes else focus
    direct_links = [l for l in links if l.source == focus or l.target == focus]
    direct = len(direct_links)
    top_contact = ""
    if direct_links:
        best = max(direct_links, key=lambda l: l.weight)
        other_id = best.target if best.source == focus else best.source
        if other_id in nodes:
            top_contact = f" Strongest contact: {nodes[other_id].label} ({best.label})."
    summary = (
        f"{focus_name} sits at the centre of this investigation map with {direct} direct phone links."
        f"{top_contact} Thicker lines mean more calls between those two people."
    )

    return GraphResponse(
        nodes=list(nodes.values()),
        links=links,
        focus_person_id=focus,
        summary=summary,
    )


def build_case_graph(
    db: Session,
    case_id: str,
    center_person_id: str | None = None,
) -> GraphResponse:
    roles = _case_roles(db, case_id)
    member_ids = _person_ids_for_case(db, case_id)

    if center_person_id:
        member_ids.add(center_person_id)
        hop_rows = db.execute(
            text(
                """
                SELECT person_id_b FROM relationships
                WHERE case_id = :cid AND person_id_a = :pid
                UNION
                SELECT person_id_a FROM relationships
                WHERE case_id = :cid AND person_id_b = :pid
                """
            ),
            {"cid": case_id, "pid": center_person_id},
        ).scalars().all()
        member_ids.update(hop_rows)

    nodes: dict[str, InvestigationEntity] = {}
    links: list[GraphLink] = []
    seen_links: set[tuple[str, str]] = set()

    def add_link(source: str, target: str, label: str, weight: float = 1.0) -> None:
        key = (source, target) if source < target else (target, source)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append(GraphLink(source=source, target=target, label=label, weight=weight))

    for pid in sorted(member_ids):
        person = _fetch_person(db, pid)
        if not person:
            continue
        nodes[pid] = _build_person_entity(db, case_id, person, roles)

        phone_rows = db.execute(
            text("SELECT phone_number FROM phones WHERE person_id = :pid ORDER BY phone_id"),
            {"pid": pid},
        ).scalars().all()
        for num in phone_rows:
            ph_id = _phone_entity_id(num)
            if ph_id not in nodes:
                nodes[ph_id] = InvestigationEntity(
                    id=ph_id,
                    label=num,
                    type="phone",
                    subtitle=f"Registered to {pid}",
                    score=55,
                    severity="medium",
                    sources=["phones.csv"],
                    explainability=["Handset registered to case network member."],
                    connections=[],
                    metadata={"person_id": pid},
                )
            add_link(pid, ph_id, "owns", 1.0)

        acct_rows = db.execute(
            text(
                """
                SELECT account_number, bank_name FROM bank_accounts
                WHERE person_id = :pid ORDER BY account_id
                """
            ),
            {"pid": pid},
        ).mappings().all()
        for acct in acct_rows:
            acct_id = _account_entity_id(acct["account_number"])
            if acct_id not in nodes:
                nodes[acct_id] = InvestigationEntity(
                    id=acct_id,
                    label=acct["account_number"],
                    type="account",
                    subtitle=acct["bank_name"],
                    score=60,
                    severity="medium",
                    sources=["bank_accounts.csv"],
                    explainability=["Bank account linked to case network member."],
                    connections=[],
                    metadata={"person_id": pid, "bank": acct["bank_name"]},
                )
            add_link(pid, acct_id, "account holder", 1.0)

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
        a, b = rel["person_id_a"], rel["person_id_b"]
        if a in member_ids and b in member_ids:
            add_link(a, b, rel["relationship_type"], 2.0)

    cdr_rows = db.execute(
        text("SELECT caller_phone, receiver_phone FROM cdr WHERE case_id = :cid"),
        {"cid": case_id},
    ).mappings().all()
    phone_owner = {
        r["phone_number"]: r["person_id"]
        for r in db.execute(text("SELECT phone_number, person_id FROM phones")).mappings().all()
    }
    for cdr in cdr_rows:
        caller_pid = phone_owner.get(cdr["caller_phone"])
        receiver_pid = phone_owner.get(cdr["receiver_phone"])
        if not caller_pid or not receiver_pid:
            continue
        if caller_pid in member_ids and receiver_pid in member_ids:
            add_link(caller_pid, receiver_pid, "CDR", 1.5)
        caller_ph = _phone_entity_id(cdr["caller_phone"])
        receiver_ph = _phone_entity_id(cdr["receiver_phone"])
        if caller_ph in nodes and receiver_ph in nodes:
            add_link(caller_ph, receiver_ph, "call", 1.0)

    from app.services.network_analysis import analyze_case

    analysis = analyze_case(db, case_id)
    for node_id, entity in nodes.items():
        pr = analysis.pagerank.get(node_id, 0.0)
        bt = analysis.betweenness.get(node_id, 0.0)
        comm = analysis.communities.get(node_id, "")
        entity.metadata["pagerank"] = f"{pr:.4f}"
        entity.metadata["betweenness"] = f"{bt:.4f}"
        if comm:
            entity.metadata["community"] = comm
        if pr > 0 and entity.type == "person":
            entity.score = min(99, max(entity.score, int(pr * 500) + 40))

    focus = _resolve_focus_person(db, case_id, center_person_id)
    return GraphResponse(nodes=list(nodes.values()), links=links, focus_person_id=focus)


def build_simplified_case_graph(
    db: Session,
    case_id: str,
    center_person_id: str | None = None,
) -> GraphResponse:
    return build_investigation_map(db, case_id, center_person_id=center_person_id)
