from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.session import get_db
from app.opds.auth import get_opds_user
from app.opds.templates import (
    build_atom_feed, build_navigation_entry, build_book_entry, build_opds2_publication
)
from app.books.models import Book
from app.users.models import User
from datetime import datetime, timezone

router = APIRouter(prefix="/opds", tags=["opds"])

OPDS_PAGE_SIZE = 50
ATOM_CONTENT_TYPE = "application/atom+xml;profile=opds-catalog;kind=acquisition"


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


# --- OPDS 1.2 (Atom XML) ---


@router.get("/v1/catalog")
async def opds_root(request: Request, user: User = Depends(get_opds_user)):
    base = _base_url(request)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = "\n".join([
        build_navigation_entry("Recent Additions", f"{base}/opds/v1/catalog/recent", "urn:inkisle:recent", "Recently added books"),
        build_navigation_entry("By Rating", f"{base}/opds/v1/catalog/popular", "urn:inkisle:popular", "Highest rated books"),
        build_navigation_entry("Search", f"{base}/opds/v1/catalog/search", "urn:inkisle:search", "Search the catalog"),
    ])

    links = f"""<link rel="self" href="{base}/opds/v1/catalog" type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="search" href="{base}/opds/v1/catalog/search?q={{searchTerms}}" type="application/atom+xml" title="Search"/>"""

    xml = build_atom_feed("InkIsle Library", "urn:inkisle:root", entries, links, now)
    return Response(content=xml, media_type=ATOM_CONTENT_TYPE)


@router.get("/v1/catalog/recent")
async def opds_recent(
    request: Request,
    page: int = Query(1, ge=1),
    user: User = Depends(get_opds_user),
    db: AsyncSession = Depends(get_db),
):
    base = _base_url(request)
    return await _paginated_feed(db, base, "Recent Additions", "urn:inkisle:recent",
                                  f"{base}/opds/v1/catalog/recent", page, Book.created_at.desc())


@router.get("/v1/catalog/popular")
async def opds_popular(
    request: Request,
    page: int = Query(1, ge=1),
    user: User = Depends(get_opds_user),
    db: AsyncSession = Depends(get_db),
):
    base = _base_url(request)
    return await _paginated_feed(db, base, "Popular Books", "urn:inkisle:popular",
                                  f"{base}/opds/v1/catalog/popular", page, Book.avg_rating.desc().nullslast())


@router.get("/v1/catalog/search")
async def opds_search(
    request: Request,
    q: str = Query(""),
    page: int = Query(1, ge=1),
    user: User = Depends(get_opds_user),
    db: AsyncSession = Depends(get_db),
):
    base = _base_url(request)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    query = select(Book).where(Book.is_available == True)
    count_q = select(func.count(Book.id)).where(Book.is_available == True)

    if q:
        ts = func.plainto_tsquery("english", q)
        query = query.where(Book.search_vector.op("@@")(ts))
        count_q = count_q.where(Book.search_vector.op("@@")(ts))

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * OPDS_PAGE_SIZE
    books = (await db.execute(query.order_by(Book.created_at.desc()).offset(offset).limit(OPDS_PAGE_SIZE))).scalars().all()

    entries = "\n".join(build_book_entry(b, base) for b in books)
    links = f'<link rel="self" href="{base}/opds/v1/catalog/search?q={q}&amp;page={page}" type="{ATOM_CONTENT_TYPE}"/>'
    if (page * OPDS_PAGE_SIZE) < total:
        links += f'\n  <link rel="next" href="{base}/opds/v1/catalog/search?q={q}&amp;page={page + 1}" type="{ATOM_CONTENT_TYPE}"/>'

    xml = build_atom_feed(f"Search: {q}", f"urn:inkisle:search:{q}:{page}", entries, links, now)
    return Response(content=xml, media_type=ATOM_CONTENT_TYPE)


# --- OPDS 2.0 (JSON) ---


@router.get("/v2/catalog.json")
async def opds2_root(request: Request, user: User = Depends(get_opds_user)):
    base = _base_url(request)
    return JSONResponse(content={
        "metadata": {"title": "InkIsle Library"},
        "links": [
            {"rel": "self", "href": f"{base}/opds/v2/catalog.json", "type": "application/opds+json"},
        ],
        "navigation": [
            {"href": f"{base}/opds/v2/publications.json", "title": "All Publications", "type": "application/opds+json"},
        ],
    }, media_type="application/opds+json")


@router.get("/v2/publications.json")
async def opds2_publications(
    request: Request,
    page: int = Query(1, ge=1),
    q: str | None = None,
    user: User = Depends(get_opds_user),
    db: AsyncSession = Depends(get_db),
):
    base = _base_url(request)
    query = select(Book).where(Book.is_available == True)
    count_q = select(func.count(Book.id)).where(Book.is_available == True)

    if q:
        ts = func.plainto_tsquery("english", q)
        query = query.where(Book.search_vector.op("@@")(ts))
        count_q = count_q.where(Book.search_vector.op("@@")(ts))

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * OPDS_PAGE_SIZE
    books = (await db.execute(query.order_by(Book.created_at.desc()).offset(offset).limit(OPDS_PAGE_SIZE))).scalars().all()

    publications = [build_opds2_publication(b, base) for b in books]

    result = {
        "metadata": {"title": "All Publications", "numberOfItems": total, "itemsPerPage": OPDS_PAGE_SIZE, "currentPage": page},
        "links": [{"rel": "self", "href": f"{base}/opds/v2/publications.json?page={page}", "type": "application/opds+json"}],
        "publications": publications,
    }
    if (page * OPDS_PAGE_SIZE) < total:
        result["links"].append({"rel": "next", "href": f"{base}/opds/v2/publications.json?page={page + 1}", "type": "application/opds+json"})

    return JSONResponse(content=result, media_type="application/opds+json")


# --- Helper ---


async def _paginated_feed(db: AsyncSession, base: str, title: str, feed_id: str, self_href: str, page: int, order_by):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total = (await db.execute(select(func.count(Book.id)).where(Book.is_available == True))).scalar() or 0
    offset = (page - 1) * OPDS_PAGE_SIZE
    books = (await db.execute(
        select(Book).where(Book.is_available == True).order_by(order_by).offset(offset).limit(OPDS_PAGE_SIZE)
    )).scalars().all()

    entries = "\n".join(build_book_entry(b, base) for b in books)
    links = f'<link rel="self" href="{self_href}?page={page}" type="{ATOM_CONTENT_TYPE}"/>'
    if (page * OPDS_PAGE_SIZE) < total:
        links += f'\n  <link rel="next" href="{self_href}?page={page + 1}" type="{ATOM_CONTENT_TYPE}"/>'

    xml = build_atom_feed(title, f"{feed_id}:{page}", entries, links, now)
    return Response(content=xml, media_type=ATOM_CONTENT_TYPE)
