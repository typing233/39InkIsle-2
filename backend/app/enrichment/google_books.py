import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.enrichment.models import MetadataCache
from app.enrichment.rate_limiter import get_rate_limiter
from app.config import get_settings


async def search_google_books(isbn: str | None = None, title: str | None = None, author: str | None = None) -> list[dict]:
    settings = get_settings()
    if not settings.google_books_api_key:
        return []

    limiter = await get_rate_limiter()
    if not await limiter.acquire("google_books", 100, 3600):
        return []

    parts = []
    if isbn:
        parts.append(f"isbn:{isbn}")
    else:
        if title:
            parts.append(f"intitle:{title}")
        if author:
            parts.append(f"inauthor:{author}")

    if not parts:
        return []

    query = "+".join(parts)
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5&key={settings.google_books_api_key}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()

    results = []
    for item in data.get("items", [])[:5]:
        vol = item.get("volumeInfo", {})
        results.append({
            "external_id": item.get("id"),
            "title": vol.get("title"),
            "authors": vol.get("authors", []),
            "description": vol.get("description"),
            "publisher": vol.get("publisher"),
            "published_date": vol.get("publishedDate"),
            "isbn_13": next((i["identifier"] for i in vol.get("industryIdentifiers", []) if i["type"] == "ISBN_13"), None),
            "isbn_10": next((i["identifier"] for i in vol.get("industryIdentifiers", []) if i["type"] == "ISBN_10"), None),
            "categories": vol.get("categories", []),
            "image_url": vol.get("imageLinks", {}).get("thumbnail"),
            "language": vol.get("language"),
            "page_count": vol.get("pageCount"),
        })
    return results


async def get_cached_or_fetch_google(
    db: AsyncSession, isbn: str | None = None, title: str | None = None, author: str | None = None
) -> list[dict]:
    query_key = f"gb:{isbn or ''}:{title or ''}:{author or ''}"

    cached = await db.execute(
        select(MetadataCache).where(
            MetadataCache.provider == "google_books",
            MetadataCache.query_key == query_key,
            MetadataCache.expires_at > datetime.now(timezone.utc),
        )
    )
    cache_hit = cached.scalar_one_or_none()
    if cache_hit:
        return cache_hit.response_data.get("results", [])

    results = await search_google_books(isbn, title, author)

    settings = get_settings()
    ttl_hours = settings.enrichment_cache_ttl_hours if results else 1
    cache_entry = MetadataCache(
        provider="google_books",
        query_key=query_key,
        external_id=results[0]["external_id"] if results else None,
        response_data={"results": results},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.add(cache_entry)
    await db.flush()

    return results
