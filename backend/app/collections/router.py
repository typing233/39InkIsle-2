from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.users.models import User
from app.collections import schemas, service
from uuid import UUID

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=list[schemas.CollectionResponse])
async def list_collections(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.ensure_system_collections(db, user.id)
    return await service.get_user_collections(db, user.id)


@router.post("", response_model=schemas.CollectionResponse)
async def create_collection(
    data: schemas.CollectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    col = await service.create_collection(db, user.id, data.name)
    return schemas.CollectionResponse(
        id=col.id, name=col.name, collection_type=col.collection_type,
        is_system=col.is_system, item_count=0, created_at=col.created_at,
    )


@router.put("/{collection_id}", response_model=schemas.CollectionResponse)
async def update_collection(
    collection_id: UUID,
    data: schemas.CollectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    col = await service.update_collection(db, user.id, collection_id, data.name)
    return col


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_collection(db, user.id, collection_id)
    return {"detail": "Collection deleted"}


@router.get("/{collection_id}/books")
async def list_collection_books(
    collection_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.get_collection_books(db, user.id, collection_id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/{collection_id}/books/{book_id}")
async def add_book(
    collection_id: UUID,
    book_id: UUID,
    device_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await service.add_book_to_collection(db, user.id, collection_id, book_id, device_id)
    return {"detail": "Book added", "item_id": item.id}


@router.delete("/{collection_id}/books/{book_id}")
async def remove_book(
    collection_id: UUID,
    book_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.remove_book_from_collection(db, user.id, collection_id, book_id)
    return {"detail": "Book removed"}


@router.get("/favorites/check/{book_id}")
async def check_favorite(
    book_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.ensure_system_collections(db, user.id)
    is_fav = await service.is_book_in_favorites(db, user.id, book_id)
    return {"is_favorite": is_fav}


@router.post("/sync", response_model=schemas.CollectionSyncResponse)
async def sync_collection(
    data: schemas.CollectionSyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-device sync endpoint. Client sends its local vector clock and book list.
    Server resolves conflicts using vector clock comparison:
    - If server is ahead: returns server state unchanged.
    - If client is ahead: applies client state.
    - If concurrent (neither dominates): merges with add-wins semantics (union).
    """
    merged_books, merged_vc, conflicts = await service.sync_collection(
        db, user.id, data.collection_id, data.device_id,
        data.vector_clock, data.book_ids,
    )
    return schemas.CollectionSyncResponse(
        merged_book_ids=merged_books,
        vector_clock=merged_vc,
        conflicts_resolved=conflicts,
    )
