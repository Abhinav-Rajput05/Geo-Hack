"""
Redis Cache and Queue Client
"""
import redis.asyncio as redis
from typing import Optional, Any, Dict, List
import json
from loguru import logger

from app.config import settings


class RedisClient:
    """Async Redis client for caching and task queue"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.url = settings.REDIS_URL
    
    async def connect(self) -> None:
        """Establish connection to Redis"""
        try:
            self.client = redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            if not self.client:
                return False
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    # String operations
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set a key-value pair with optional expiration"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        try:
            value = await self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis GET failed: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS failed: {e}")
            return False
    
    # Hash operations
    async def hset(
        self, 
        name: str, 
        key: str, 
        value: Any
    ) -> bool:
        """Set a hash field"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Redis HSET failed: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get a hash field value"""
        try:
            value = await self.client.hget(name, key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis HGET failed: {e}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            data = await self.client.hgetall(name)
            result = {}
            for key, value in data.items():
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Redis HGETALL failed: {e}")
            return {}
    
    # List operations
    async def lpush(self, name: str, value: Any) -> bool:
        """Push value to left of list"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.lpush(name, value)
            return True
        except Exception as e:
            logger.error(f"Redis LPUSH failed: {e}")
            return False
    
    async def rpush(self, name: str, value: Any) -> bool:
        """Push value to right of list"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.client.rpush(name, value)
            return True
        except Exception as e:
            logger.error(f"Redis RPUSH failed: {e}")
            return False
    
    async def lrange(
        self, 
        name: str, 
        start: int = 0, 
        end: int = -1
    ) -> List[Any]:
        """Get range of list elements"""
        try:
            values = await self.client.lrange(name, start, end)
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)
            return result
        except Exception as e:
            logger.error(f"Redis LRANGE failed: {e}")
            return []
    
    # Pub/Sub operations
    async def publish(self, channel: str, message: Any) -> bool:
        """Publish a message to a channel"""
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            await self.client.publish(channel, message)
            return True
        except Exception as e:
            logger.error(f"Redis PUBLISH failed: {e}")
            return False
    
    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub


# Global Redis client instance
redis_client = RedisClient()
