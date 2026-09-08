from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.timeline import TimelineEvent
from app.services.investigation_search import _account_entity_id, _phone_entity_id


def build_case_timeline(db: Session, case_id: str) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []

    txns = db.execute(
        text(
            """
            SELECT transaction_id, sender_account, receiver_account, amount, timestamp
            FROM transactions WHERE case_id = :cid ORDER BY timestamp
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    acct_owners = {
        r["account_number"]: r["person_id"]
        for r in db.execute(
            text("SELECT account_number, person_id FROM bank_accounts")
        ).mappings().all()
    }
    for txn in txns:
        sender_acct = _account_entity_id(txn["sender_account"])
        receiver_acct = _account_entity_id(txn["receiver_account"])
        entity_ids = [sender_acct, receiver_acct]
        sender_pid = acct_owners.get(txn["sender_account"])
        receiver_pid = acct_owners.get(txn["receiver_account"])
        if sender_pid:
            entity_ids.append(sender_pid)
        if receiver_pid:
            entity_ids.append(receiver_pid)
        events.append(
            TimelineEvent(
                id=f"TL-TXN-{txn['transaction_id']}",
                timestamp=str(txn["timestamp"]),
                title="Fund movement",
                description=(
                    f"₹{txn['amount']} transferred from {txn['sender_account']} "
                    f"to {txn['receiver_account']}."
                ),
                entityIds=list(dict.fromkeys(entity_ids)),
                source=txn["transaction_id"],
            )
        )

    cdr_rows = db.execute(
        text(
            """
            SELECT cdr_id, caller_phone, receiver_phone, timestamp, tower_location
            FROM cdr WHERE case_id = :cid ORDER BY timestamp
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    phone_owner = {
        r["phone_number"]: r["person_id"]
        for r in db.execute(text("SELECT phone_number, person_id FROM phones")).mappings().all()
    }
    for cdr in cdr_rows:
        caller_ph = _phone_entity_id(cdr["caller_phone"])
        receiver_ph = _phone_entity_id(cdr["receiver_phone"])
        entity_ids = [caller_ph, receiver_ph]
        if phone_owner.get(cdr["caller_phone"]):
            entity_ids.append(phone_owner[cdr["caller_phone"]])
        if phone_owner.get(cdr["receiver_phone"]):
            entity_ids.append(phone_owner[cdr["receiver_phone"]])
        events.append(
            TimelineEvent(
                id=f"TL-CDR-{cdr['cdr_id']}",
                timestamp=str(cdr["timestamp"]),
                title="Call record",
                description=(
                    f"Call {cdr['caller_phone']} → {cdr['receiver_phone']} "
                    f"(tower: {cdr['tower_location']})."
                ),
                entityIds=list(dict.fromkeys(entity_ids)),
                source=cdr["cdr_id"],
            )
        )

    fir_rows = db.execute(
        text(
            """
            SELECT fir_id, date, police_station, complaint_text
            FROM fir WHERE case_id = :cid ORDER BY date
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for fir in fir_rows:
        events.append(
            TimelineEvent(
                id=f"TL-FIR-{fir['fir_id']}",
                timestamp=f"{fir['date']} 09:00:00",
                title="FIR filed",
                description=(
                    f"FIR at {fir['police_station']}: "
                    f"{fir['complaint_text'][:180]}…"
                    if len(fir["complaint_text"]) > 180
                    else f"FIR at {fir['police_station']}: {fir['complaint_text']}"
                ),
                entityIds=[],
                source=fir["fir_id"],
            )
        )

    surv_rows = db.execute(
        text(
            """
            SELECT surveillance_id, timestamp, location, report_text
            FROM surveillance WHERE case_id = :cid ORDER BY timestamp
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for surv in surv_rows:
        events.append(
            TimelineEvent(
                id=f"TL-SUR-{surv['surveillance_id']}",
                timestamp=str(surv["timestamp"]),
                title="Surveillance report",
                description=f"{surv['location']}: {surv['report_text'][:160]}",
                entityIds=[],
                source=surv["surveillance_id"],
            )
        )

    chats = db.execute(
        text(
            """
            SELECT message_id, sender_phone, receiver_phone, timestamp, message_text
            FROM chat_messages WHERE case_id = :cid ORDER BY timestamp
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for msg in chats:
        sender_ph = _phone_entity_id(msg["sender_phone"])
        receiver_ph = _phone_entity_id(msg["receiver_phone"])
        entity_ids = [sender_ph, receiver_ph]
        if phone_owner.get(msg["sender_phone"]):
            entity_ids.append(phone_owner[msg["sender_phone"]])
        events.append(
            TimelineEvent(
                id=f"TL-MSG-{msg['message_id']}",
                timestamp=str(msg["timestamp"]),
                title="Chat message",
                description=f'"{msg["message_text"][:120]}"',
                entityIds=list(dict.fromkeys(entity_ids)),
                source=msg["message_id"],
            )
        )

    events.sort(key=lambda e: e.timestamp)
    return events
