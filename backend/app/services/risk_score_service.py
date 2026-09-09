from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.investigation_search import _case_roles, _fetch_person
from app.services.network_analysis import analyze_case, get_centrality_rankings

ROLE_WEIGHTS = {
    "suspect": 25.0,
    "handler": 22.0,
    "facilitator": 18.0,
    "associate": 15.0,
    "witness": 5.0,
    "complainant": 3.0,
}


def _severity(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _case_history_score(db: Session, case_id: str, person_id: str) -> tuple[float, list[str]]:
    notes: list[str] = []
    score = 0.0

    cdr = db.execute(
        text(
            """
            SELECT COUNT(*) FROM cdr c
            JOIN phones ph ON ph.phone_number IN (c.caller_phone, c.receiver_phone)
            WHERE c.case_id = :cid AND ph.person_id = :pid
            """
        ),
        {"cid": case_id, "pid": person_id},
    ).scalar() or 0
    if cdr:
        score += min(20.0, cdr / 2)
        notes.append(f"{cdr} case CDR records")

    txns = db.execute(
        text(
            """
            SELECT COUNT(*) FROM transactions t
            JOIN bank_accounts ba ON ba.account_number IN (t.sender_account, t.receiver_account)
            WHERE t.case_id = :cid AND ba.person_id = :pid
            """
        ),
        {"cid": case_id, "pid": person_id},
    ).scalar() or 0
    if txns:
        score += min(15.0, txns * 3)
        notes.append(f"{txns} financial transactions")

    fir = 0
    person = _fetch_person(db, person_id)
    if person:
        fir_full = db.execute(
            text(
                """
                SELECT COUNT(*) FROM fir
                WHERE case_id = :cid AND complaint_text ILIKE :pat
                """
            ),
            {"cid": case_id, "pat": f"%{person.name}%"},
        ).scalar() or 0
        if fir_full:
            fir = fir_full
            score += 12.0
            notes.append("full name in FIR complaint")
        else:
            fir_partial = db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM fir
                    WHERE case_id = :cid AND complaint_text ILIKE :pat
                    """
                ),
                {"cid": case_id, "pat": f"%{person.name.split()[0]}%"},
            ).scalar() or 0
            if fir_partial:
                fir = fir_partial
                score += 6.0
                notes.append("first name mentioned in FIR")

    return score, notes


def compute_risk_scores(db: Session, case_id: str) -> list[dict]:
    roles = _case_roles(db, case_id)
    analysis = analyze_case(db, case_id)
    centrality = {r["entity_id"]: r for r in get_centrality_rankings(db, case_id)}

    person_ids = db.execute(
        text(
            """
            SELECT DISTINCT person_id_a AS pid FROM relationships WHERE case_id = :cid
            UNION SELECT person_id_b FROM relationships WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).scalars().all()

    scores: list[dict] = []
    for pid in person_ids:
        if not pid or not pid.startswith("P"):
            continue
        person = _fetch_person(db, pid)
        if not person:
            continue

        role = roles.get(pid)
        cent = centrality.get(pid, {})
        pr = float(cent.get("pagerank", analysis.pagerank.get(pid, 0.0)))
        bt = float(cent.get("betweenness", analysis.betweenness.get(pid, 0.0)))
        centrality_component = min(40.0, pr * 800 + bt * 200)
        role_component = ROLE_WEIGHTS.get(role or "", 8.0)
        history_component, history_notes = _case_history_score(db, case_id, pid)

        composite = int(min(99, centrality_component + role_component + history_component))
        role_label = (role or "unknown").replace("_", " ")
        explain = [
            f"Evidence-based triage score {composite}/99 (rank assigned after sort).",
            f"Centrality {centrality_component:.1f}/40 (network position: PageRank {pr:.4f}).",
            f"Role weight {role_component:.1f}/25 ({role_label} in case).",
        ]
        if history_notes:
            explain.append(f"Case evidence {history_component:.1f}/43: {', '.join(history_notes)}.")
        else:
            explain.append("Case evidence: no CDR, transactions, or FIR mention linked yet.")

        scores.append(
            {
                "entity_id": pid,
                "label": person.name,
                "city": person.city,
                "role": role,
                "composite_score": composite,
                "severity": _severity(composite),
                "components": {
                    "centrality": round(centrality_component, 2),
                    "role": round(role_component, 2),
                    "case_history": round(history_component, 2),
                },
                "triage_rank": 0,
                "explainability": explain,
            }
        )

    scores.sort(key=lambda s: -s["composite_score"])
    for i, row in enumerate(scores, start=1):
        row["triage_rank"] = i
        row["explainability"][0] = (
            f"Priority #{i} — evidence score {row['composite_score']}/99 "
            f"(centrality {row['components']['centrality']}, role {row['components']['role']}, "
            f"evidence {row['components']['case_history']})."
        )
    return scores
