from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, text
from app.books.models import Book, Tag, BookTag
from app.books.schemas import BookSearchParams
from app.core.exceptions import NotFoundError
import uuid


async def search_books(
    db: AsyncSession, params: BookSearchParams
) -> tuple[list[Book], int]:
    query = select(Book).where(Book.is_available == True)
    count_query = select(func.count(Book.id)).where(Book.is_available == True)

    if params.q:
        ts_query = func.plainto_tsquery("english", params.q)
        query = query.where(Book.search_vector.op("@@")(ts_query))
        count_query = count_query.where(Book.search_vector.op("@@")(ts_query))

    if params.author:
        query = query.where(Book.author.ilike(f"%{params.author}%"))
        count_query = count_query.where(Book.author.ilike(f"%{params.author}%"))

    if params.format:
        query = query.where(Book.file_format == params.format)
        count_query = count_query.where(Book.file_format == params.format)

    if params.tag:
        query = query.join(BookTag).join(Tag).where(Tag.name == params.tag)
        count_query = count_query.join(BookTag).join(Tag).where(Tag.name == params.tag)

    sort_column = getattr(Book, params.sort_by, Book.created_at)
    order_fn = desc if params.sort_order == "desc" else asc
    query = query.order_by(order_fn(sort_column))

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


async def delete_book(db: AsyncSession, book_id: uuid.UUID) -> None:
    book = await get_book(db, book_id)
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
