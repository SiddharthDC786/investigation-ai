from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.risk_score_service import compute_risk_scores
from app.services.timeline_service import build_case_timeline
from app.services.network_analysis import get_community_clusters


def build_case_summary(db: Session, case_id: str) -> dict:
    started = time.perf_counter()

    case = db.execute(
        text("SELECT case_id, title, description FROM cases WHERE case_id = :cid"),
        {"cid": case_id},
    ).mappings().first()
    if not case:
        raise ValueError("Case not found")

    risk_scores = compute_risk_scores(db, case_id)
    timeline = build_case_timeline(db, case_id)
    communities = get_community_clusters(db, case_id)

    top = risk_scores[:5]
    top_subjects = [f"{s['label']} (score {s['composite_score']}, {s['role'] or 'unknown role'})" for s in top]

    timeline_highlights = [
        f"{ev.timestamp[:16]} — {ev.title}: {ev.description[:100]}"
        for ev in timeline[:5]
    ]

    person_count = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT pid) FROM (
                SELECT person_id_a AS pid FROM relationships WHERE case_id = :cid
                UNION SELECT person_id_b FROM relationships WHERE case_id = :cid
            ) x
            """
        ),
        {"cid": case_id},
    ).scalar() or 0

    cdr_count = db.execute(
        text("SELECT COUNT(*) FROM cdr WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    txn_count = db.execute(
        text("SELECT COUNT(*) FROM transactions WHERE case_id = :cid"),
        {"cid": case_id},
    ).scalar() or 0

    key_findings = [
        f"{person_count} persons linked in the relationship graph for this case.",
        f"{cdr_count} telecom records and {txn_count} financial transactions ingested.",
    ]
    if communities:
        key_findings.append(
            f"Community detection identified {len(communities)} clusters; "
            f"highest suspicion: {communities[0]['label']} (score {communities[0]['suspicion_score']})."
        )
    if top:
        key_findings.append(
            f"Priority triage subject: {top[0]['label']} with composite risk {top[0]['composite_score']}/99."
        )

    shared_phone = db.execute(
        text(
            """
            SELECT phone_number FROM (
                SELECT c.receiver_phone AS phone_number, COUNT(DISTINCT ph.person_id) AS cnt
                FROM cdr c
                JOIN phones ph ON ph.phone_number = c.receiver_phone
                WHERE c.case_id = :cid
                GROUP BY c.receiver_phone
                HAVING COUNT(DISTINCT ph.person_id) >= 2
            ) sub
            LIMIT 1
            """
        ),
        {"cid": case_id},
    ).scalar()
    if not shared_phone:
        shared_phone = db.execute(
            text(
                """
                SELECT recorded_phone FROM recorded_phones
                WHERE case_id = :cid AND person_id IS NOT NULL
                GROUP BY recorded_phone
                HAVING COUNT(DISTINCT person_id) >= 2
                LIMIT 1
                """
            ),
            {"cid": case_id},
        ).scalar()
    if shared_phone:
        key_findings.append(
            "Fusion analysis indicates a shared-contact bridge linking otherwise disconnected persons."
        )

    lead_subject = top[0]["label"] if top else "unknown subjects"
    narrative_parts = [
        f"Case {case_id} — {case['title']}.",
        case["description"] or "Synthetic investigation dataset for SIH demonstration.",
        (
            f"The inquiry currently tracks {person_count} named individuals across telecom, banking, "
            f"and FIR sources. Automated triage ranks {lead_subject} as the highest-priority interview target."
        ),
        (
            "Chronological reconstruction shows "
            + (timeline_highlights[0] if timeline_highlights else "no major events yet")
            + ", followed by corroborating financial and surveillance entries."
        ),
        (
            "Recommended next steps: confirm identity variants in recorded_names, expand CDR pivot on "
            "top-scored handsets, and document officer review decisions in the hash-chained audit log."
        ),
    ]
    narrative = " ".join(narrative_parts)

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "case_id": case_id,
        "title": case["title"],
        "narrative": narrative,
        "key_findings": key_findings,
        "top_subjects": top_subjects,
        "timeline_highlights": timeline_highlights,
        "generated_in_ms": elapsed_ms,
    }
