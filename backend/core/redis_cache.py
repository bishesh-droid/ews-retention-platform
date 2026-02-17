import json
from functools import wraps
from typing import Any, Optional
import redis
from backend.config import REDIS_URL, CACHE_EXPIRE_SECONDS

class RedisCache:
    def __init__(self):
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
        except Exception:
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client: return None
        data = self.client.get(key)
        return json.loads(data) if data else None

    def set(self, key: str, value: Any, expire: int = CACHE_EXPIRE_SECONDS):
        if not self.client: return
        self.client.setex(key, expire, json.dumps(value))

cache = RedisCache()

def cache_response(key_prefix: str, expire: int = CACHE_EXPIRE_SECONDS):
    """
    Decorator to cache FastAPI route responses in Redis.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create unique key based on arguments
            key = f"{key_prefix}:{hash(str(kwargs))}"
            cached_data = cache.get(key)
            if cached_data:
                return cached_data
            
            result = await func(*args, **kwargs)
            cache.set(key, result, expire)
            return result
        return wrapper
    return decorator
