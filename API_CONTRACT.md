GET /health

GET /cases

GET /cases/{case_id}

GET /cases/{case_id}/entities

GET /cases/{case_id}/graph

GET /cases/{case_id}/leads

POST /cases

{
  "nodes": [
    {
      "id": "P001",
      "type": "PERSON",
      "label": "Person 1"
    }
  ],
  "edges": [
    {
      "source": "P001",
      "target": "PH001",
      "type": "USES_PHONE"
    }
  ]
}