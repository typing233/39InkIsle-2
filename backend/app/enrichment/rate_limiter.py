import time
import redis.asyncio as redis
from app.config import get_settings


class RedisRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def acquire(self, key: str, max_tokens: int, window_seconds: int) -> bool:
        now = time.time()
        window_key = f"ratelimit:{key}:{int(now // window_seconds)}"

        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds + 1)
        results = await pipe.execute()

        current_count = results[0]
        return current_count <= max_tokens

    async def remaining(self, key: str, max_tokens: int, window_seconds: int) -> int:
        now = time.time()
        window_key = f"ratelimit:{key}:{int(now // window_seconds)}"
        current = await self.redis.get(window_key)
        if current is None:
            return max_tokens
        return max(0, max_tokens - int(current))


_limiter: RedisRateLimiter | None = None


async def get_rate_limiter() -> RedisRateLimiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        client = redis.from_url(settings.redis_url)
        _limiter = RedisRateLimiter(client)
    return _limiter
