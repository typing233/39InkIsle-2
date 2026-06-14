from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.users.models import User
from app.reviews import schemas, service
from uuid import UUID

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/{book_id}", response_model=schemas.ReviewResponse)
async def create_review(
    book_id: UUID,
    data: schemas.ReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await service.create_review(db, user.id, book_id, data)
    return schemas.ReviewResponse(
        id=review.id, user_id=review.user_id, book_id=review.book_id,
        rating=review.rating, review_text=review.review_text, is_visible=review.is_visible,
        username=user.username, created_at=review.created_at, updated_at=review.updated_at,
    )


@router.get("/{book_id}", response_model=schemas.PaginatedReviewsResponse)
async def list_reviews(
    book_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.get_reviews_for_book(db, book_id, page, page_size)
    return schemas.PaginatedReviewsResponse(items=items, total=total, page=page, page_size=page_size)


@router.put("/{book_id}", response_model=schemas.ReviewResponse)
async def update_review(
    book_id: UUID,
    data: schemas.ReviewUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await service.update_review(db, user.id, book_id, data)
    return review


@router.delete("/{book_id}")
async def delete_own_review(
    book_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_review(db, user.id, book_id)
    return {"detail": "Review deleted"}


@router.delete("/{book_id}/{review_id}")
async def admin_delete_review(
    book_id: UUID,
    review_id: UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.admin_delete_review(db, book_id, review_id)
    return {"detail": "Review deleted"}


@router.get("/my/all", response_model=list[schemas.ReviewResponse])
async def my_reviews(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.reviews.models import Review
    q = select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc())
    results = (await db.execute(q)).scalars().all()
    return results
