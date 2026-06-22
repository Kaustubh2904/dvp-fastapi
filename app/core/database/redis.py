import logging
import sys
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config.settings import settings

logger = logging.getLogger(__name__)

# Global flag for Redis availability
redis_client: Optional[aioredis.Redis] = None
is_redis_available = False

# Simple in-memory fallback cache when Redis is down
in_memory_cache: dict[str, str] = {}


async def init_redis():
    global redis_client, is_redis_available
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        # Verify connection by pinging
        await redis_client.ping()
        is_redis_available = True
        print("INFO:  Redis is available and connected successfully.", file=sys.stderr)
    except Exception as e:
        is_redis_available = False
        redis_client = None
        print(f"WARNING: Redis is not available ({e}). Falling back to in-memory/database operations.", file=sys.stderr)
        logger.warning(f"Redis is not available: {e}")


async def redis_set(key: str, value: str, expire_seconds: Optional[int] = None) -> bool:
    if is_redis_available and redis_client:
        try:
            await redis_client.set(key, value, ex=expire_seconds)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            # Fallback to in-memory
    
    in_memory_cache[key] = value
    # Expire is mocked (we don't implement full background eviction here, but it's fine for fallback)
    return True


async def redis_get(key: str) -> Optional[str]:
    if is_redis_available and redis_client:
        try:
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            # Fallback to in-memory
            
    return in_memory_cache.get(key)


async def redis_delete(key: str) -> bool:
    if is_redis_available and redis_client:
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            # Fallback to in-memory
            
    if key in in_memory_cache:
        del in_memory_cache[key]
        return True
    return False
