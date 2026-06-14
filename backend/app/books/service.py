from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, text, or_
from app.books.models import Book, Tag, BookTag
from app.books.metadata_models import BookMetadata
from app.books.schemas import BookSearchParams
from app.core.exceptions import NotFoundError
from app.admin.service import log_action
import uuid


async def search_books(
    db: AsyncSession, params: BookSearchParams
) -> tuple[list[Book], int]:
    query = select(Book).where(Book.is_available == True)
    count_query = select(func.count(func.distinct(Book.id))).select_from(Book).where(Book.is_available == True)

    # Full-text or fuzzy search
    if params.q:
        if params.q_fuzzy:
            similarity_threshold = 0.3
            sim_filter = or_(
                func.similarity(Book.title, params.q) > similarity_threshold,
                func.similarity(Book.author, params.q) > similarity_threshold,
            )
            query = query.where(sim_filter)
            count_query = count_query.where(sim_filter)
        else:
            ts_query = func.plainto_tsquery("english", params.q)
            query = query.where(Book.search_vector.op("@@")(ts_query))
            count_query = count_query.where(Book.search_vector.op("@@")(ts_query))

    if params.author:
        query = query.where(Book.author.ilike(f"%{params.author}%"))
        count_query = count_query.where(Book.author.ilike(f"%{params.author}%"))

    if params.format:
        query = query.where(Book.file_format == params.format)
        count_query = count_query.where(Book.file_format == params.format)

    if params.language:
        query = query.where(Book.language == params.language)
        count_query = count_query.where(Book.language == params.language)

    if params.tag:
        query = query.join(BookTag, Book.id == BookTag.book_id).join(Tag, BookTag.tag_id == Tag.id).where(Tag.name == params.tag)
        count_query = count_query.join(BookTag, Book.id == BookTag.book_id).join(Tag, BookTag.tag_id == Tag.id).where(Tag.name == params.tag)

    if params.series:
        query = query.join(BookMetadata, Book.id == BookMetadata.book_id, isouter=True).where(
            BookMetadata.series_name.ilike(f"%{params.series}%")
        )
        count_query = count_query.join(BookMetadata, Book.id == BookMetadata.book_id, isouter=True).where(
            BookMetadata.series_name.ilike(f"%{params.series}%")
        )

    if params.rating_min is not None:
        query = query.where(Book.avg_rating >= params.rating_min)
        count_query = count_query.where(Book.avg_rating >= params.rating_min)

    if params.rating_max is not None:
        query = query.where(Book.avg_rating <= params.rating_max)
        count_query = count_query.where(Book.avg_rating <= params.rating_max)

    if params.has_cover is True:
        query = query.where(Book.cover_path.isnot(None))
        count_query = count_query.where(Book.cover_path.isnot(None))
    elif params.has_cover is False:
        query = query.where(Book.cover_path.is_(None))
        count_query = count_query.where(Book.cover_path.is_(None))

    if params.publish_date_from:
        query = query.where(Book.publish_date >= params.publish_date_from)
        count_query = count_query.where(Book.publish_date >= params.publish_date_from)

    if params.publish_date_to:
        query = query.where(Book.publish_date <= params.publish_date_to)
        count_query = count_query.where(Book.publish_date <= params.publish_date_to)

    # Sort: fuzzy search uses similarity, otherwise use specified column
    if params.q and params.q_fuzzy:
        query = query.distinct().order_by(func.similarity(Book.title, params.q).desc())
    else:
        sort_column = getattr(Book, params.sort_by, Book.created_at)
        order_fn = desc if params.sort_order == "desc" else asc
        query = query.distinct().order_by(order_fn(sort_column))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)
    result = await db.execute(query)
    books = list(result.scalars().all())

    return books, total


async def get_book(db: AsyncSession, book_id: uuid.UUID) -> Book:
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise NotFoundError("Book not found")
    return book


async def delete_book(db: AsyncSession, book_id: uuid.UUID, operator_id: uuid.UUID) -> None:
    book = await get_book(db, book_id)
    await log_action(
        db, operator_id, "book.delete",
        resource_type="book", resource_id=book_id,
        details={"title": book.title, "author": book.author},
    )
    await db.delete(book)


async def get_all_tags(db: AsyncSession) -> list[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


async def create_tag(db: AsyncSession, name: str) -> Tag:
    tag = Tag(name=name)
    db.add(tag)
    await db.flush()
    return tag


async def add_tag_to_book(db: AsyncSession, book_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    book_tag = BookTag(book_id=book_id, tag_id=tag_id)
    db.add(book_tag)
    await db.flush()


async def remove_tag_from_book(db: AsyncSession, book_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    result = await db.execute(
        select(BookTag).where(BookTag.book_id == book_id, BookTag.tag_id == tag_id)
    )
    bt = result.scalar_one_or_none()
    if bt:
        await db.delete(bt)
