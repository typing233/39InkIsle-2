import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.enrichment.models import MetadataCache
from app.enrichment.rate_limiter import get_rate_limiter
from app.config import get_settings


async def search_comicvine(title: str | None = None) -> list[dict]:
    settings = get_settings()
    if not settings.comicvine_api_key or not title:
        return []

    limiter = await get_rate_limiter()
    if not await limiter.acquire("comicvine", 200, 900):
        return []

    url = "https://comicvine.gamespot.com/api/search/"
    params = {
        "api_key": settings.comicvine_api_key,
        "format": "json",
        "resource_type": "volume",
        "query": title,
        "limit": 5,
    }
    headers = {"User-Agent": "InkIsle/1.0"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            return []
        data = resp.json()

    results = []
    for item in data.get("results", [])[:5]:
        results.append({
            "external_id": str(item.get("id")),
            "title": item.get("name"),
            "description": item.get("deck") or item.get("description"),
            "publisher": item.get("publisher", {}).get("name") if item.get("publisher") else None,
            "start_year": item.get("start_year"),
            "issue_count": item.get("count_of_issues"),
            "image_url": item.get("image", {}).get("medium_url") if item.get("image") else None,
        })
    return results


async def get_cached_or_fetch_comicvine(db: AsyncSession, title: str | None = None) -> list[dict]:
    query_key = f"cv:{title or ''}"

    cached = await db.execute(
        select(MetadataCache).where(
            MetadataCache.provider == "comicvine",
            MetadataCache.query_key == query_key,
            MetadataCache.expires_at > datetime.now(timezone.utc),
        )
    )
    cache_hit = cached.scalar_one_or_none()
    if cache_hit:
        return cache_hit.response_data.get("results", [])

    results = await search_comicvine(title)

    settings = get_settings()
    ttl_hours = settings.enrichment_cache_ttl_hours if results else 1
    cache_entry = MetadataCache(
        provider="comicvine",
        query_key=query_key,
        external_id=results[0]["external_id"] if results else None,
        response_data={"results": results},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.add(cache_entry)
    await db.flush()

    return results
