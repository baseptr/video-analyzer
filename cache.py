"""
Redis cache wrapper for Video Analyzer.
"""

import os
from typing import Optional
import redis
from utils.logger import setup_logger

logger = setup_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")


class RedisCache:
    """Simple Redis cache wrapper."""

    def __init__(self):
        self.client = None
        self._connect()

    def _connect(self):
        """Connect to Redis."""
        try:
            self.client = redis.from_url(REDIS_URL)
            self.client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.client = None

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        if not self.client:
            return False
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False


# Singleton
_redis_cache: Optional[RedisCache] = None


def get_redis() -> RedisCache:
    """Get Redis cache singleton."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
