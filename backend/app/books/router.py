from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.users.models import User
from app.books import schemas, service
from app.config import get_settings
from uuid import UUID
import os

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=schemas.PaginatedBooksResponse)
async def list_books(
    q: str | None = None,
    q_fuzzy: bool = False,
    author: str | None = None,
    tag: str | None = None,
    format: str | None = None,
    series: str | None = None,
    language: str | None = None,
    rating_min: float | None = None,
    rating_max: float | None = None,
    has_cover: bool | None = None,
    publish_date_from: str | None = None,
    publish_date_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type
    date_from = None
    date_to = None
    if publish_date_from:
        try:
            date_from = date_type.fromisoformat(publish_date_from)
        except ValueError:
            pass
    if publish_date_to:
        try:
            date_to = date_type.fromisoformat(publish_date_to)
        except ValueError:
            pass

    params = schemas.BookSearchParams(
        q=q, q_fuzzy=q_fuzzy, author=author, tag=tag, format=format,
        series=series, language=language,
        rating_min=rating_min, rating_max=rating_max,
        has_cover=has_cover,
        publish_date_from=date_from, publish_date_to=date_to,
        sort_by=sort_by, sort_order=sort_order,
        page=page, page_size=page_size,
    )
    books, total = await service.search_books(db, params)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return schemas.PaginatedBooksResponse(
        items=books, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/{book_id}", response_model=schemas.BookResponse)
async def get_book(
    book_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_book(db, book_id)


@router.get("/{book_id}/cover")
async def get_cover(
    book_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await service.get_book(db, book_id)
    if not book.cover_path:
        return FileResponse(status_code=404)
    settings = get_settings()
    cover_full_path = os.path.join(settings.covers_storage_path, book.cover_path)
    if not os.path.exists(cover_full_path):
        return FileResponse(status_code=404)
    return FileResponse(cover_full_path)


@router.get("/{book_id}/file")
async def download_file(
    book_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await service.get_book(db, book_id)
    return FileResponse(book.file_path, filename=f"{book.title}.{book.file_format}")


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_book(db, book_id, operator_id=admin.id)


@router.get("/tags/all", response_model=list[schemas.TagResponse])
async def list_tags(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_all_tags(db)


@router.post("/tags", response_model=schemas.TagResponse, status_code=201)
async def create_tag(
    data: schemas.TagCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_tag(db, data.name)


@router.post("/{book_id}/tags/{tag_id}", status_code=204)
async def add_tag(
    book_id: UUID,
    tag_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.add_tag_to_book(db, book_id, tag_id)


@router.delete("/{book_id}/tags/{tag_id}", status_code=204)
async def remove_tag(
    book_id: UUID,
    tag_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_tag_from_book(db, book_id, tag_id)


# --- Metadata endpoints ---
from app.books import metadata_schemas, metadata_service


@router.get("/{book_id}/metadata", response_model=metadata_schemas.MetadataResponse)
async def get_metadata(
    book_id: UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meta = await metadata_service.get_metadata(db, book_id)
    if not meta:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Metadata not found")
    return meta


@router.patch("/{book_id}/metadata", response_model=metadata_schemas.MetadataResponse)
async def calibrate_metadata(
    book_id: UUID,
    data: metadata_schemas.MetadataCalibrate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    updates = data.model_dump(exclude_none=True)
    return await metadata_service.calibrate_metadata(db, book_id, updates, operator_id=admin.id)
