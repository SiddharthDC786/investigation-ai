from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.graph import GraphLink, GraphResponse, GraphStats
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


def _cdr_person_edges(
    db: Session,
    case_id: str,
    *,
    min_calls: int = 3,
) -> list[tuple[str, str, int]]:
    rows = db.execute(
        text(
            """
            SELECT p1.person_id AS a, p2.person_id AS b, COUNT(*) AS cnt
            FROM cdr c
            JOIN phones p1 ON p1.phone_number = c.caller_phone
            JOIN phones p2 ON p2.phone_number = c.receiver_phone
            WHERE c.case_id = :cid AND p1.person_id <> p2.person_id
            GROUP BY p1.person_id, p2.person_id
            HAVING COUNT(*) >= :min_calls
            ORDER BY cnt DESC
            """
        ),
        {"cid": case_id, "min_calls": min_calls},
    ).mappings().all()
    return [(r["a"], r["b"], int(r["cnt"])) for r in rows]


def _connected_person_ids_for_case(
    db: Session,
    case_id: str,
    *,
    min_calls: int = 1,
) -> set[str]:
    """Everyone in the case network: relationships, narrative cast, and CDR-linked people."""
    included = _person_ids_for_case(db, case_id)
    included.update(NARRATIVE_ROLES.get(case_id, {}).keys())

    cdr_people = db.execute(
        text(
            """
            SELECT DISTINCT ph.person_id
            FROM cdr c
            JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
            WHERE c.case_id = :cid AND ph.person_id IS NOT NULL
            """
        ),
        {"cid": case_id},
    ).scalars().all()
    included.update(pid for pid in cdr_people if pid)

    cdr_edges = _cdr_person_edges(db, case_id, min_calls=min_calls)
    changed = True
    while changed:
        changed = False
        before = len(included)
        for a, b, _cnt in cdr_edges:
            if a in included or b in included:
                included.add(a)
                included.add(b)
        changed = len(included) > before

    return {pid for pid in included if _fetch_person(db, pid)}


def _shared_contact_bridges(
    db: Session,
    case_id: str,
    person_ids: set[str],
) -> list[tuple[str, str, dict[str, int], str | None]]:
    """
    Numbers that 2+ people in the map called (outbound CDR).
    Returns (phone_number, phone_entity_id, {person_id: call_count}, owner_person_id).
    """
    if len(person_ids) < 2:
        return []

    rows = db.execute(
        text(
            """
            SELECT p1.person_id AS caller, c.receiver_phone AS target, COUNT(*) AS cnt
            FROM cdr c
            JOIN phones p1 ON p1.phone_number = c.caller_phone
            WHERE c.case_id = :cid AND p1.person_id = ANY(:pids)
            GROUP BY p1.person_id, c.receiver_phone
            HAVING COUNT(*) >= 1
            """
        ),
        {"cid": case_id, "pids": list(person_ids)},
    ).mappings().all()

    by_target: dict[str, dict[str, int]] = defaultdict(dict)
    for row in rows:
        by_target[row["target"]][row["caller"]] = int(row["cnt"])

    owners = {
        r["phone_number"]: r["person_id"]
        for r in db.execute(text("SELECT phone_number, person_id FROM phones")).mappings().all()
    }

    bridges: list[tuple[str, str, dict[str, int], str | None]] = []
    for number, callers in by_target.items():
        if len(callers) < 2:
            continue
        bridges.append((number, _phone_entity_id(number), callers, owners.get(number)))

    bridges.sort(key=lambda x: (-len(x[2]), -sum(x[2].values())))
    return bridges[:2]


def _role_label(role: str | None) -> str:
    return {
        "suspect": "primary suspect",
        "associate": "associate",
        "facilitator": "facilitator",
        "witness": "witness",
        "handler": "financial handler",
        "complainant": "complainant",
    }.get(role or "", "contact")


def _build_connection_story(
    focus: str,
    nodes: dict[str, InvestigationEntity],
    links: list[GraphLink],
) -> list[str]:
    focus_node = nodes.get(focus)
    if not focus_node:
        return []

    focus_name = focus_node.label
    stories: list[str] = [
        f"{focus_name} is the investigation focus. Every connection below is supported by call records — not guesswork.",
    ]

    direct = [
        l
        for l in links
        if l.link_type == "phone_call" and focus in (l.source, l.target)
    ]
    for link in sorted(direct, key=lambda l: -l.weight):
        other_id = link.target if link.source == focus else link.source
        other = nodes.get(other_id)
        if not other or other.type != "person":
            continue
        role = _role_label(other.role)
        stories.append(
            f"{other.label} ({role}) — {link.label} with {focus_name}. {link.evidence or 'CDR records'}."
        )

    inner = [
        l
        for l in links
        if l.link_type == "phone_call"
        and focus not in (l.source, l.target)
        and (nodes.get(l.source) and nodes.get(l.source).type == "person")
        and (nodes.get(l.target) and nodes.get(l.target).type == "person")
    ]
    for link in sorted(inner, key=lambda l: -l.weight):
        a = nodes.get(link.source)
        b = nodes.get(link.target)
        if not a or not b:
            continue
        stories.append(
            f"{a.label} and {b.label} also spoke directly ({link.label}) — inner ring link. {link.evidence or 'CDR records'}."
        )

    bridges = [l for l in links if l.link_type == "shared_contact"]
    if bridges:
        stories.append(
            "Shared contact numbers (diamond nodes) were called by multiple people — a hidden link when they never called each other directly."
        )

    if len(stories) == 1:
        stories.append("No strong phone links found yet — ingest CDR or expand the search focus.")

    return stories


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
        focus_label = _role_label(role or roles.get(person_id))
        suffix = f" · Investigation focus ({focus_label})"
        entity.subtitle = (entity.subtitle or "") + suffix if entity.subtitle else f"Investigation focus ({focus_label})"
    return entity


def build_investigation_map(
    db: Session,
    case_id: str,
    center_person_id: str | None = None,
) -> GraphResponse:
    focus = _resolve_focus_person(db, case_id, center_person_id)
    roles = _case_roles(db, case_id)
    included = _connected_person_ids_for_case(db, case_id, min_calls=1)
    included.add(focus)
    cdr_edges = _cdr_person_edges(db, case_id, min_calls=1)

    bridges = _shared_contact_bridges(db, case_id, included)
    nodes: dict[str, InvestigationEntity] = {}
    links: list[GraphLink] = []
    seen_links: set[tuple[str, str]] = set()

    def add_link(
        source: str,
        target: str,
        label: str,
        weight: float = 1.0,
        *,
        link_type: str = "phone_call",
        evidence: str | None = None,
    ) -> None:
        key = (source, target) if source < target else (target, source)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append(
            GraphLink(
                source=source,
                target=target,
                label=label,
                weight=weight,
                link_type=link_type,
                evidence=evidence,
            )
        )

    for pid in included:
        node = _build_person_node(db, case_id, pid, roles, is_focus=(pid == focus))
        if node:
            nodes[pid] = node

    for a, b, cnt in cdr_edges:
        if a in included and b in included:
            add_link(
                a,
                b,
                f"{cnt} calls",
                float(cnt),
                link_type="phone_call",
                evidence=f"CDR: {cnt} recorded calls between registered handsets in case {case_id}.",
            )

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
            add_link(
                a,
                b,
                rel["relationship_type"],
                2.0,
                link_type="relationship",
                evidence=f"Case relationship file: {rel['relationship_type']}.",
            )

    for number, ph_id, callers, owner_pid in bridges:
        if ph_id in nodes:
            continue
        owner_name = nodes[owner_pid].label if owner_pid and owner_pid in nodes else "unknown party"
        nodes[ph_id] = InvestigationEntity(
            id=ph_id,
            label=f"…{number[-4:]}",
            type="phone",
            subtitle=f"Shared contact · {len(callers)} people called this number",
            score=88,
            severity="high",
            sources=["cdr"],
            explainability=[
                f"Multiple case subjects called {number[-4:]} — registered to {owner_name}.",
                "This reveals a link even when those people never called each other directly.",
            ],
            connections=[],
            metadata={"phone_number": number, "bridge": "true", "owner_id": owner_pid or ""},
        )
        for pid, call_cnt in callers.items():
            if pid in included:
                add_link(
                    pid,
                    ph_id,
                    f"{call_cnt} calls",
                    float(call_cnt),
                    link_type="shared_contact",
                    evidence=f"CDR: {nodes[pid].label} called …{number[-4:]} {call_cnt} time(s).",
                )

    focus_name = nodes[focus].label if focus in nodes else focus
    focus_role = _role_label(nodes[focus].role if focus in nodes else roles.get(focus))
    person_count = sum(1 for n in nodes.values() if n.type == "person")
    direct_links = [
        l for l in links if l.source == focus or l.target == focus
    ]
    direct = len([l for l in direct_links if l.link_type == "phone_call"])
    top_contact = ""
    phone_direct = [l for l in direct_links if l.link_type == "phone_call"]
    if phone_direct:
        best = max(phone_direct, key=lambda l: l.weight)
        other_id = best.target if best.source == focus else best.source
        if other_id in nodes and nodes[other_id].type == "person":
            top_contact = f" Strongest phone contact: {nodes[other_id].label} ({best.label})."
    bridge_count = sum(1 for n in nodes.values() if n.type == "phone")
    summary = (
        f"Case connection map — {person_count} connected people, {len(links)} link(s). "
        f"Focus: {focus_name} ({focus_role}), {direct} direct phone link(s) to them."
        f"{top_contact} Red lines = calls; gold diamonds = shared numbers."
    )

    story = _build_connection_story(focus, nodes, links)

    return GraphResponse(
        nodes=list(nodes.values()),
        links=links,
        focus_person_id=focus,
        summary=summary,
        connection_story=story,
        stats=GraphStats(
            person_count=person_count,
            link_count=len(links),
            shared_contact_count=bridge_count,
        ),
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
