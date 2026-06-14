from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.users.models import User
from app.books.service import get_book
from app.reader import schemas, service
from uuid import UUID

router = APIRouter(prefix="/reader", tags=["reader"])


@router.get("/{book_id}/progress", response_model=list[schemas.ProgressResponse])
async def get_progress(
    book_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_progress(db, user.id, book_id)


@router.put("/{book_id}/progress", response_model=schemas.ProgressResponse)
async def update_progress(
    book_id: UUID,
    data: schemas.ProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_progress(db, user.id, book_id, data)


@router.get("/{book_id}/toc", response_model=list[schemas.TOCItem])
async def get_toc(
    book_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await get_book(db, book_id)
    if book.file_format != "epub":
        return []
    return service.get_epub_toc(book.file_path)


@router.get("/{book_id}/content/{chapter}")
async def get_chapter_content(
    book_id: UUID,
    chapter: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await get_book(db, book_id)
    if book.file_format != "epub":
        return Response(content="Not an EPUB", status_code=400)

    import ebooklib
    from ebooklib import epub as ep

    epub_book = ep.read_epub(book.file_path)
    spine_items = [epub_book.get_item_with_id(item_id) for item_id, _ in epub_book.spine]
    spine_items = [item for item in spine_items if item is not None]

    if chapter < 0 or chapter >= len(spine_items):
        return Response(content="Chapter not found", status_code=404)

    item = spine_items[chapter]
    content = item.get_content()
    return Response(content=content, media_type="text/html")
