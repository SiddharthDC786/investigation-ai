from __future__ import annotations

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
)


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

    def add_link(source: str, target: str, label: str) -> None:
        key = (source, target) if source < target else (target, source)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append(GraphLink(source=source, target=target, label=label))

    for pid in sorted(member_ids):
        person = _fetch_person(db, pid)
        if not person:
            continue
        nodes[pid] = _build_person_entity(db, case_id, person, roles)

        phone_rows = db.execute(
            text(
                "SELECT phone_number FROM phones WHERE person_id = :pid ORDER BY phone_id"
            ),
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
            add_link(pid, ph_id, "owns")

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
            add_link(pid, acct_id, "account holder")

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
            add_link(a, b, rel["relationship_type"])

    cdr_rows = db.execute(
        text(
            """
            SELECT caller_phone, receiver_phone FROM cdr WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    phone_owner = {
        r["phone_number"]: r["person_id"]
        for r in db.execute(
            text("SELECT phone_number, person_id FROM phones")
        ).mappings().all()
    }
    for cdr in cdr_rows:
        caller_pid = phone_owner.get(cdr["caller_phone"])
        receiver_pid = phone_owner.get(cdr["receiver_phone"])
        if not caller_pid or not receiver_pid:
            continue
        if caller_pid in member_ids and receiver_pid in member_ids:
            add_link(caller_pid, receiver_pid, "CDR")
        caller_ph = _phone_entity_id(cdr["caller_phone"])
        receiver_ph = _phone_entity_id(cdr["receiver_phone"])
        if caller_ph in nodes and receiver_ph in nodes:
            add_link(caller_ph, receiver_ph, "call")

    return GraphResponse(nodes=list(nodes.values()), links=links)
