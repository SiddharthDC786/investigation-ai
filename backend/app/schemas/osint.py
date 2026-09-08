from pydantic import BaseModel, Field


class OsintEnrichRequest(BaseModel):
    case_id: str
    entity_id: str
    lookup_id: str
    operator: str = "system"
    operator_name: str = "Investigator"


class OsintEnrichmentHit(BaseModel):
    title: str
    detail: str
    source_registry: str
    confidence: float


class OsintEnrichResponse(BaseModel):
    enrichment_id: str
    entity_id: str
    lookup_id: str
    lookup_label: str
    case_id: str
    results: list[OsintEnrichmentHit] = Field(default_factory=list)
    graph_links_added: list[str] = Field(default_factory=list)
    audit_entry_id: str
    audit_hash: str


class AuditChainEntry(BaseModel):
    id: str
    timestamp: str
    action: str
    entityId: str
    source: str
    operator: str
    lawfulBasis: str
    entryHash: str
    prevHash: str


class OsintAuditLogResponse(BaseModel):
    case_id: str | None = None
    entries: list[AuditChainEntry] = Field(default_factory=list)
    chain_status: str = "unknown"


class AuditVerifyResponse(BaseModel):
    status: str
    entries_checked: int
    broken_entry_id: str | None = None
    message: str
