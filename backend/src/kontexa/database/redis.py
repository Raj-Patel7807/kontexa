"""Redis client lifecycle and connectivity operations."""

from redis.asyncio import Redis

from kontexa.core.config import settings

redis_client: Redis = Redis.from_url(settings.redis_url, decode_responses=False)


async def check_redis_connection() -> None:
    """Verify Redis responds to a PING command using the application client."""
    await redis_client.ping()


async def close_redis_connection() -> None:
    """Close Redis connections during application shutdown."""
    await redis_client.aclose()
