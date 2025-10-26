import json
import logging
import redis.asyncio as redis
from typing import Optional, Any

logger = logging.getLogger(__name__)


class RedisService:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection"""
        try:
            self.client = redis.from_url(url=self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f'Redis connection failed: {e}')
            raise

    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.client:
                await self.connect()

            if value := await self.client.get(key):
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f'Redis get error for key: {key}: {e}')
            return None

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if not self.client:
                await self.connect()

            await self.client.delete(key)
            return True

        except Exception as e:
            logger.error(f'Redis delete error for key: {key}: {e}')
            return False

    async def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching from cache"""
        try:
            if not self.client:
                await self.connect()

            if keys := await self.client.keys(pattern):
                await self.client.delete(*keys)
            return True

        except Exception as e:
            logger.error(f'Redis delete error for pattern: {pattern}: {e}')
            return False

    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """Set value to cache with expiration"""
        try:
            if not self.client:
                await self.connect()

            await self.client.set(name=key, value=json.dumps(value, default=str), ex=expire_seconds)
            return True

        except Exception as e:
            logger.error(f'Redis set error for key: {key}: {e}')
            return False
