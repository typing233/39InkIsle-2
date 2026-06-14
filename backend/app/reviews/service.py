from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.reviews.models import Review
from app.books.models import Book
from app.users.models import User
from app.core.exceptions import NotFoundError
from app.reviews.schemas import ReviewCreate, ReviewUpdate
import uuid


async def create_review(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID, data: ReviewCreate) -> Review:
    review = Review(
        user_id=user_id,
        book_id=book_id,
        rating=data.rating,
        review_text=data.review_text,
    )
    db.add(review)
    await db.flush()
    await _recalculate_rating(db, book_id)
    return review


async def get_reviews_for_book(
    db: AsyncSession, book_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    count_q = select(func.count(Review.id)).where(Review.book_id == book_id, Review.is_visible == True)
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    q = (
        select(Review, User.username)
        .join(User, Review.user_id == User.id)
        .where(Review.book_id == book_id, Review.is_visible == True)
        .order_by(Review.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    results = (await db.execute(q)).all()
    items = []
    for review, username in results:
        items.append({
            "id": review.id,
            "user_id": review.user_id,
            "book_id": review.book_id,
            "rating": review.rating,
            "review_text": review.review_text,
            "is_visible": review.is_visible,
            "username": username,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        })
    return items, total


async def get_user_review(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID) -> Review | None:
    q = select(Review).where(Review.user_id == user_id, Review.book_id == book_id)
    return (await db.execute(q)).scalar_one_or_none()


async def update_review(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID, data: ReviewUpdate) -> Review:
    review = await get_user_review(db, user_id, book_id)
    if not review:
        raise NotFoundError("Review not found")
    if data.rating is not None:
        review.rating = data.rating
    if data.review_text is not None:
        review.review_text = data.review_text
    await db.flush()
    await _recalculate_rating(db, book_id)
    return review


async def delete_review(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID) -> None:
    review = await get_user_review(db, user_id, book_id)
    if not review:
        raise NotFoundError("Review not found")
    await db.delete(review)
    await db.flush()
    await _recalculate_rating(db, book_id)


async def admin_delete_review(db: AsyncSession, book_id: uuid.UUID, review_id: uuid.UUID) -> None:
    q = select(Review).where(Review.id == review_id, Review.book_id == book_id)
    review = (await db.execute(q)).scalar_one_or_none()
    if not review:
        raise NotFoundError("Review not found")
    await db.delete(review)
    await db.flush()
    await _recalculate_rating(db, book_id)


async def _recalculate_rating(db: AsyncSession, book_id: uuid.UUID) -> None:
    q = select(func.avg(Review.rating), func.count(Review.id)).where(
        Review.book_id == book_id, Review.is_visible == True
    )
    result = (await db.execute(q)).one()
    avg_rating, count = result

    book_q = select(Book).where(Book.id == book_id)
    book = (await db.execute(book_q)).scalar_one_or_none()
    if book:
        book.avg_rating = round(float(avg_rating), 2) if avg_rating else None
        book.rating_count = count or 0
        await db.flush()
