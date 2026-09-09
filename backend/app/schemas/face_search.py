from pydantic import BaseModel, Field


class FaceSearchResponse(BaseModel):
    person_id: str | None = None
    similarity_score: int = Field(
        ge=0,
        le=100,
        description="Demo similarity rank — not biometric probability",
    )
    score_type: str = "demo_similarity"
    simulated: bool = True
    match_quality: str = "demo_stub"
    requires_officer_review: bool = True
    disclaimer: str = (
        "DEMO FACE SEARCH — no biometric engine connected. "
        "Returns a training-case suspect for workflow demo only. "
        "Production requires NCRB/state face API with legal authorization."
    )
    message: str = "Demo stub: photo accepted; officer must confirm identity manually."
