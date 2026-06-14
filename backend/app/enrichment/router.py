from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import require_admin
from app.users.models import User
from app.enrichment import schemas, service
from uuid import UUID

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.get("/{book_id}/candidates", response_model=schemas.EnrichmentCandidatesResponse)
async def get_candidates(
    book_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    results = await service.fetch_enrichment_candidates(db, book_id)
    return results


@router.post("/{book_id}/apply")
async def apply_enrichment(
    book_id: UUID,
    data: schemas.ApplyEnrichmentRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    meta = await service.apply_enrichment(db, book_id, data.provider, data.candidate_data, user.id)
    return {"detail": "Enrichment applied", "metadata_source": meta.metadata_source}
