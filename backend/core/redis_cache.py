import hashlib
import json
import logging
import inspect
from functools import wraps
from typing import Any, Optional
import redis
from backend.config import REDIS_URL, CACHE_EXPIRE_SECONDS

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        try:
            self.client = redis.from_url(REDIS_URL, decode_responses=True)
            self.client.ping()
            logger.info("[REDIS] Cache backend connected.")
        except Exception as exc:
            logger.exception("[REDIS] Connection failed; caching disabled: %s", exc)
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            logger.warning("[REDIS] GET skipped because client is unavailable.")
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as exc:
            logger.exception("[REDIS] GET failed for key=%s: %s", key, exc)
            return None

    def set(self, key: str, value: Any, expire: int = CACHE_EXPIRE_SECONDS):
        if not self.client:
            logger.warning("[REDIS] SET skipped because client is unavailable.")
            return
        ttl = int(expire) if int(expire) > 0 else int(CACHE_EXPIRE_SECONDS)
        try:
            payload = json.dumps(value, default=str)
        except (TypeError, ValueError) as exc:
            logger.exception("[REDIS] Serialization failed for key=%s: %s", key, exc)
            return
        try:
            self.client.setex(key, ttl, payload)
        except Exception as exc:
            logger.exception(
                "[REDIS] SETEX failed for key=%s ttl=%s: %s", key, ttl, exc
            )


cache = RedisCache()


def _normalize_for_cache_key(value: Any) -> Any:
    """Convert runtime values into deterministic JSON-serializable key material."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [_normalize_for_cache_key(v) for v in value]
    if isinstance(value, set):
        normalized = [_normalize_for_cache_key(v) for v in value]
        return sorted(
            normalized, key=lambda x: json.dumps(x, sort_keys=True, default=str)
        )
    if isinstance(value, dict):
        return {
            str(k): _normalize_for_cache_key(v)
            for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    # Keep key deterministic without depending on memory addresses.
    return str(value)


def _build_cache_key(func, key_prefix: str, args: tuple, kwargs: dict) -> str:
    ignored_params = {"db", "request", "response", "background_tasks", "current_user"}
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        key_payload = {
            k: _normalize_for_cache_key(v)
            for k, v in bound.arguments.items()
            if k not in ignored_params
        }
    except Exception:
        key_payload = {
            "args": _normalize_for_cache_key(args),
            "kwargs": _normalize_for_cache_key(kwargs),
        }

    digest = hashlib.sha256(
        json.dumps(key_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return f"{key_prefix}:{digest}"


def cache_response(key_prefix: str, expire: int = CACHE_EXPIRE_SECONDS):
    """
    Cache decorator for FastAPI routes/services.

    - Deterministic key generation (no PYTHONHASHSEED dependence)
    - Works with sync and async wrapped functions
    - Enforces positive TTL
    - Fails open (request succeeds) but logs every cache failure path
    """
    ttl = int(expire) if int(expire) > 0 else int(CACHE_EXPIRE_SECONDS)

    def decorator(func):
        async def _cache_flow(*args, **kwargs):
            key = _build_cache_key(func, key_prefix, args, kwargs)
            cached_data = cache.get(key)
            if cached_data is not None:
                return cached_data

            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            cache.set(key, result, ttl)
            return result

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _cache_flow(*args, **kwargs)

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = _build_cache_key(func, key_prefix, args, kwargs)
            cached_data = cache.get(key)
            if cached_data is not None:
                return cached_data
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return sync_wrapper

    return decorator
