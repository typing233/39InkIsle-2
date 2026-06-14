from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.collections.models import Collection, CollectionItem
from app.core.exceptions import NotFoundError
import uuid


async def ensure_system_collections(db: AsyncSession, user_id: uuid.UUID) -> None:
    for name, ctype in [("Favorites", "favorites"), ("To Read", "to_read")]:
        existing = await db.execute(
            select(Collection).where(
                Collection.user_id == user_id,
                Collection.collection_type == ctype,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(Collection(
                user_id=user_id, name=name,
                collection_type=ctype, is_system=True,
            ))
    await db.flush()


async def get_user_collections(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    q = select(Collection).where(Collection.user_id == user_id).order_by(Collection.created_at)
    collections = (await db.execute(q)).scalars().all()

    results = []
    for col in collections:
        count_q = select(func.count(CollectionItem.id)).where(CollectionItem.collection_id == col.id)
        count = (await db.execute(count_q)).scalar() or 0
        results.append({
            "id": col.id,
            "name": col.name,
            "collection_type": col.collection_type,
            "is_system": col.is_system,
            "item_count": count,
            "vector_clock": col.vector_clock or {},
            "created_at": col.created_at,
        })
    return results


async def create_collection(db: AsyncSession, user_id: uuid.UUID, name: str) -> Collection:
    col = Collection(user_id=user_id, name=name, collection_type="custom")
    db.add(col)
    await db.flush()
    return col


async def update_collection(db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID, name: str) -> Collection:
    col = await _get_collection(db, user_id, collection_id)
    if col.is_system:
        raise ValueError("Cannot rename system collections")
    col.name = name
    await db.flush()
    return col


async def delete_collection(db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID) -> None:
    col = await _get_collection(db, user_id, collection_id)
    if col.is_system:
        raise ValueError("Cannot delete system collections")
    await db.delete(col)
    await db.flush()


async def add_book_to_collection(
    db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID, book_id: uuid.UUID, device_id: str | None = None
) -> CollectionItem:
    col = await _get_collection(db, user_id, collection_id)

    existing = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.book_id == book_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Book already in collection")

    max_pos = (await db.execute(
        select(func.max(CollectionItem.position)).where(CollectionItem.collection_id == collection_id)
    )).scalar() or 0

    item = CollectionItem(
        collection_id=collection_id,
        book_id=book_id,
        position=max_pos + 1,
        device_id=device_id,
    )
    db.add(item)

    # Update vector clock
    if device_id:
        vc = dict(col.vector_clock or {})
        vc[device_id] = vc.get(device_id, 0) + 1
        col.vector_clock = vc

    await db.flush()
    return item


async def remove_book_from_collection(
    db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID, book_id: uuid.UUID
) -> None:
    await _get_collection(db, user_id, collection_id)
    item = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.book_id == book_id,
        )
    )
    ci = item.scalar_one_or_none()
    if not ci:
        raise NotFoundError("Book not in collection")
    await db.delete(ci)
    await db.flush()


async def get_collection_books(
    db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> tuple[list[CollectionItem], int]:
    await _get_collection(db, user_id, collection_id)

    count_q = select(func.count(CollectionItem.id)).where(CollectionItem.collection_id == collection_id)
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    q = (
        select(CollectionItem)
        .where(CollectionItem.collection_id == collection_id)
        .order_by(CollectionItem.position)
        .offset(offset)
        .limit(page_size)
    )
    items = (await db.execute(q)).scalars().all()
    return items, total


async def is_book_in_favorites(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID) -> bool:
    fav = await db.execute(
        select(Collection).where(
            Collection.user_id == user_id,
            Collection.collection_type == "favorites",
        )
    )
    fav_col = fav.scalar_one_or_none()
    if not fav_col:
        return False
    item = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == fav_col.id,
            CollectionItem.book_id == book_id,
        )
    )
    return item.scalar_one_or_none() is not None


async def _get_collection(db: AsyncSession, user_id: uuid.UUID, collection_id: uuid.UUID) -> Collection:
    q = select(Collection).where(Collection.id == collection_id, Collection.user_id == user_id)
    col = (await db.execute(q)).scalar_one_or_none()
    if not col:
        raise NotFoundError("Collection not found")
    return col


def _vector_clock_dominates(vc_a: dict[str, int], vc_b: dict[str, int]) -> bool:
    """Return True if vc_a causally dominates vc_b (all entries >= and at least one >)."""
    all_keys = set(vc_a.keys()) | set(vc_b.keys())
    at_least_one_greater = False
    for k in all_keys:
        a_val = vc_a.get(k, 0)
        b_val = vc_b.get(k, 0)
        if a_val < b_val:
            return False
        if a_val > b_val:
            at_least_one_greater = True
    return at_least_one_greater


def _merge_vector_clocks(vc_a: dict[str, int], vc_b: dict[str, int]) -> dict[str, int]:
    """Merge two vector clocks by taking the max of each entry."""
    merged = dict(vc_a)
    for k, v in vc_b.items():
        merged[k] = max(merged.get(k, 0), v)
    return merged


async def sync_collection(
    db: AsyncSession,
    user_id: uuid.UUID,
    collection_id: uuid.UUID,
    device_id: str,
    client_vector_clock: dict[str, int],
    client_book_ids: list[uuid.UUID],
) -> tuple[list[uuid.UUID], dict[str, int], int]:
    """
    Cross-device sync with vector-clock conflict resolution.

    Strategy:
    - If server VC dominates client VC: server wins, return server state.
    - If client VC dominates server VC: client wins, apply client state.
    - Concurrent (neither dominates): merge with union of books (add-wins).

    Returns (merged_book_ids, merged_vector_clock, conflicts_resolved_count).
    """
    col = await _get_collection(db, user_id, collection_id)
    server_vc = dict(col.vector_clock or {})

    # Get current server book IDs
    items_q = select(CollectionItem.book_id).where(CollectionItem.collection_id == collection_id)
    server_book_ids = set((await db.execute(items_q)).scalars().all())
    client_book_set = set(client_book_ids)

    conflicts_resolved = 0

    if _vector_clock_dominates(server_vc, client_vector_clock):
        # Server is strictly ahead — client gets server state, no writes needed
        merged_books = list(server_book_ids)
        merged_vc = server_vc
    elif _vector_clock_dominates(client_vector_clock, server_vc):
        # Client is strictly ahead — apply client state to server
        merged_books = list(client_book_set)
        merged_vc = dict(client_vector_clock)

        # Remove books not in client set
        to_remove = server_book_ids - client_book_set
        for bid in to_remove:
            item = (await db.execute(
                select(CollectionItem).where(
                    CollectionItem.collection_id == collection_id,
                    CollectionItem.book_id == bid,
                )
            )).scalar_one_or_none()
            if item:
                await db.delete(item)

        # Add books in client but not in server
        max_pos = (await db.execute(
            select(func.max(CollectionItem.position)).where(CollectionItem.collection_id == collection_id)
        )).scalar() or 0
        to_add = client_book_set - server_book_ids
        for i, bid in enumerate(to_add):
            db.add(CollectionItem(
                collection_id=collection_id,
                book_id=bid,
                position=max_pos + i + 1,
                device_id=device_id,
            ))
    else:
        # Concurrent modifications — union merge (add-wins CRDT semantics)
        merged_books_set = server_book_ids | client_book_set
        merged_books = list(merged_books_set)
        merged_vc = _merge_vector_clocks(server_vc, client_vector_clock)
        conflicts_resolved = len(client_book_set - server_book_ids) + len(server_book_ids - client_book_set)

        # Add items that are only in the client
        max_pos = (await db.execute(
            select(func.max(CollectionItem.position)).where(CollectionItem.collection_id == collection_id)
        )).scalar() or 0
        to_add = client_book_set - server_book_ids
        for i, bid in enumerate(to_add):
            db.add(CollectionItem(
                collection_id=collection_id,
                book_id=bid,
                position=max_pos + i + 1,
                device_id=device_id,
            ))

    # Increment this device's clock entry
    merged_vc[device_id] = merged_vc.get(device_id, 0) + 1

    # Persist merged vector clock
    col.vector_clock = merged_vc
    await db.flush()

    # Return stable ordering by position
    final_items_q = (
        select(CollectionItem.book_id)
        .where(CollectionItem.collection_id == collection_id)
        .order_by(CollectionItem.position)
    )
    stable_book_ids = list((await db.execute(final_items_q)).scalars().all())

    return stable_book_ids, merged_vc, conflicts_resolved
