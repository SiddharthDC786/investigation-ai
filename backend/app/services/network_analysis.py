from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.investigation_search import _account_entity_id, _phone_entity_id


@dataclass
class CaseAnalysis:
    betweenness: dict[str, float] = field(default_factory=dict)
    pagerank: dict[str, float] = field(default_factory=dict)
    communities: dict[str, str] = field(default_factory=dict)
    community_labels: dict[str, str] = field(default_factory=dict)


_CACHE: dict[str, CaseAnalysis] = {}


def invalidate_case_analysis(case_id: str) -> None:
    _CACHE.pop(case_id, None)


def _build_networkx_graph(db: Session, case_id: str) -> nx.Graph:
    g = nx.Graph()

    member_ids = db.execute(
        text(
            """
            SELECT person_id_a AS pid FROM relationships WHERE case_id = :cid
            UNION SELECT person_id_b FROM relationships WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).scalars().all()
    members = {p for p in member_ids if p}

    for pid in members:
        row = db.execute(
            text("SELECT name FROM people WHERE person_id = :pid"),
            {"pid": pid},
        ).mappings().first()
        g.add_node(pid, label=row["name"] if row else pid, type="person")

    phone_owner = {
        r["phone_number"]: r["person_id"]
        for r in db.execute(text("SELECT phone_number, person_id FROM phones")).mappings().all()
    }

    for pid in members:
        phones = db.execute(
            text("SELECT phone_number FROM phones WHERE person_id = :pid"),
            {"pid": pid},
        ).scalars().all()
        for num in phones:
            ph_id = _phone_entity_id(num)
            g.add_node(ph_id, label=num, type="phone")
            g.add_edge(pid, ph_id, label="owns")

        accts = db.execute(
            text("SELECT account_number FROM bank_accounts WHERE person_id = :pid"),
            {"pid": pid},
        ).scalars().all()
        for acct in accts:
            acct_id = _account_entity_id(acct)
            g.add_node(acct_id, label=acct, type="account")
            g.add_edge(pid, acct_id, label="account")

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
        if a in members and b in members:
            g.add_edge(a, b, label=rel["relationship_type"])

    cdr_rows = db.execute(
        text("SELECT caller_phone, receiver_phone FROM cdr WHERE case_id = :cid"),
        {"cid": case_id},
    ).mappings().all()
    for cdr in cdr_rows:
        caller = phone_owner.get(cdr["caller_phone"])
        receiver = phone_owner.get(cdr["receiver_phone"])
        if caller and receiver and caller in members and receiver in members:
            g.add_edge(caller, receiver, label="cdr")
        caller_ph = _phone_entity_id(cdr["caller_phone"])
        receiver_ph = _phone_entity_id(cdr["receiver_phone"])
        if g.has_node(caller_ph) and g.has_node(receiver_ph):
            g.add_edge(caller_ph, receiver_ph, label="call")

    acct_rows = db.execute(
        text("SELECT account_number, person_id FROM bank_accounts")
    ).mappings().all()
    acct_by_num = {a["account_number"]: a for a in acct_rows}
    txns = db.execute(
        text(
            """
            SELECT sender_account, receiver_account, amount
            FROM transactions WHERE case_id = :cid
            """
        ),
        {"cid": case_id},
    ).mappings().all()
    for txn in txns:
        sender = acct_by_num.get(txn["sender_account"])
        receiver = acct_by_num.get(txn["receiver_account"])
        if not sender or not receiver:
            continue
        s_pid, r_pid = sender["person_id"], receiver["person_id"]
        if s_pid in members and r_pid in members:
            g.add_edge(s_pid, r_pid, label="transaction")
        s_acct = _account_entity_id(txn["sender_account"])
        r_acct = _account_entity_id(txn["receiver_account"])
        if g.has_node(s_acct) and g.has_node(r_acct):
            g.add_edge(s_acct, r_acct, label=f"₹{txn['amount']}")

    return g


def _node_label(g: nx.Graph, node_id: str) -> str:
    data = g.nodes.get(node_id, {})
    return str(data.get("label", node_id))


def analyze_case(db: Session, case_id: str) -> CaseAnalysis:
    if case_id in _CACHE:
        return _CACHE[case_id]

    g = _build_networkx_graph(db, case_id)
    analysis = CaseAnalysis()

    if g.number_of_nodes() == 0:
        _CACHE[case_id] = analysis
        return analysis

    analysis.betweenness = nx.betweenness_centrality(g)
    try:
        analysis.pagerank = nx.pagerank(g, max_iter=100)
    except (ImportError, ModuleNotFoundError, nx.PowerIterationFailedConvergence):
        analysis.pagerank = nx.degree_centrality(g)

    try:
        communities = nx.algorithms.community.louvain_communities(g, seed=42)
    except Exception:
        communities = [set(g.nodes())]

    for idx, comm in enumerate(communities):
        comm_id = f"RING-{idx + 1:02d}"
        person_names = [
            _node_label(g, n) for n in comm if g.nodes[n].get("type") == "person"
        ]
        label = (
            f"Cluster {idx + 1}: {', '.join(person_names[:3])}"
            if person_names
            else f"Cluster {idx + 1} ({len(comm)} nodes)"
        )
        suspicion = min(95.0, 40.0 + len(comm) * 8 + sum(analysis.pagerank.get(n, 0) for n in comm) * 100)
        analysis.community_labels[comm_id] = label
        for node in comm:
            analysis.communities[node] = comm_id

    _CACHE[case_id] = analysis
    return analysis


def get_centrality_rankings(db: Session, case_id: str) -> list[dict[str, Any]]:
    g = _build_networkx_graph(db, case_id)
    analysis = analyze_case(db, case_id)

    rows: list[dict[str, Any]] = []
    for node in g.nodes():
        rows.append(
            {
                "entity_id": node,
                "label": _node_label(g, node),
                "entity_type": g.nodes[node].get("type", "person"),
                "betweenness": round(analysis.betweenness.get(node, 0.0), 6),
                "pagerank": round(analysis.pagerank.get(node, 0.0), 6),
            }
        )

    rows.sort(key=lambda r: (-r["pagerank"], -r["betweenness"]))
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def get_community_clusters(db: Session, case_id: str) -> list[dict[str, Any]]:
    g = _build_networkx_graph(db, case_id)
    analysis = analyze_case(db, case_id)

    grouped: dict[str, list[str]] = {}
    for node, comm_id in analysis.communities.items():
        grouped.setdefault(comm_id, []).append(node)

    clusters: list[dict[str, Any]] = []
    for comm_id, members in grouped.items():
        suspicion = min(
            95.0,
            40.0 + len(members) * 8 + sum(analysis.pagerank.get(n, 0) for n in members) * 100,
        )
        clusters.append(
            {
                "community_id": comm_id,
                "entity_ids": sorted(members),
                "label": analysis.community_labels.get(comm_id, comm_id),
                "member_count": len(members),
                "suspicion_score": round(suspicion, 1),
            }
        )

    clusters.sort(key=lambda c: -c["suspicion_score"])
    return clusters
