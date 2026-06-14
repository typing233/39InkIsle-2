from pydantic import BaseModel
import uuid


class EnrichmentCandidatesResponse(BaseModel):
    google_books: list[dict]
    comicvine: list[dict]


class ApplyEnrichmentRequest(BaseModel):
    provider: str
    candidate_data: dict
