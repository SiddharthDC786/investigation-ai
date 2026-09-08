def get_entity_by_id(entity_id: str) -> dict | None:
    """
    Placeholder until Neo4j is connected. Returns fake entity data.
    """
    fake_data = {
        "P001": {"id": "P001", "type": "PERSON", "label": "Person 1"},
        "PH001": {"id": "PH001", "type": "PHONE", "label": "9876500001"},
    }
    return fake_data.get(entity_id)

def get_case_graph(case_id: str) -> dict:
    """
    Placeholder until Neo4j is connected. Returns fake graph.
    """
    return {
        "nodes": [
            {"id": "P001", "type": "PERSON", "label": "Person 1"},
            {"id": "PH001", "type": "PHONE", "label": "9876500001"},
        ],
        "edges": [
            {"source": "P001", "target": "PH001", "type": "USES_PHONE"},
        ],
    }

    def get_entity_connections(entity_id: str) -> list[dict]:
    """
    Placeholder - later this becomes a Neo4j query for direct neighbors.
    """
    return [
        {"connected_to": "PH001", "relationship": "USES_PHONE"},
    ]

def get_entity_history(entity_id: str) -> list[dict]:
    """
    Placeholder - later this shows all source records mentioning this entity.
    """
    return [
        {"source_id": "SRC001", "source_type": "FIR", "mentioned_at": "2026-01-15"},
    ]