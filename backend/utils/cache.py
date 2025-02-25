import redis
import json
from config.settings import load_settings  # Changed import
from utils.logger import logger
from typing import Any, Optional, Union, Dict
import backoff
from redis.exceptions import ConnectionError, TimeoutError

redis_client = None

def get_redis_client():
    global redis_client
    if redis_client is None:
        settings = load_settings()  # Load settings lazily
        redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
    return redis_client

# Cache key prefix to avoid collisions
CACHE_PREFIX = "multi_agent_cache:"

# Helper function to serialize data
def _serialize(value: Any) -> str:
    """Serialize data to a JSON string."""
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.error(f"Serialization failed: {e}")
        raise ValueError(f"Cannot serialize value: {e}")

# Helper function to deserialize data
def _deserialize(data: str) -> Any:
    """Deserialize JSON string to Python object."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Deserialization failed: {e}")
        return None

@backoff.on_exception(
    backoff.expo,
    (ConnectionError, TimeoutError),
    max_tries=3,
    on_backoff=lambda details: logger.debug(f"Retrying Redis operation: attempt {details['tries']}")
)
def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    full_key = f"{CACHE_PREFIX}{key}"
    try:
        serialized_value = _serialize(value)
        redis_client.setex(full_key, ttl, serialized_value)
        logger.debug(f"Cache set for {full_key} with TTL {ttl}")
        return True
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Cache set failed for {full_key} due to connection issue: {e}")
        return False
    except Exception as e:
        logger.error(f"Cache set failed for {full_key}: {e}")
        return False

@backoff.on_exception(
    backoff.expo,
    (ConnectionError, TimeoutError),
    max_tries=3,
    on_backoff=lambda details: logger.debug(f"Retrying Redis operation: attempt {details['tries']}")
)
def cache_get(key: str) -> Optional[Any]:
    full_key = f"{CACHE_PREFIX}{key}"
    try:
        result = redis_client.get(full_key)
        if result is None:
            logger.debug(f"Cache miss for {full_key}")
            return None
        value = _deserialize(result)
        if value is not None:
            logger.debug(f"Cache hit for {full_key}")
            return value
        logger.warning(f"Failed to deserialize cached value for {full_key}")
        return None
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Cache get failed for {full_key} due to connection issue: {e}")
        return None
    except Exception as e:
        logger.error(f"Cache get failed for {full_key}: {e}")
        return None

def cache_delete(key: str) -> bool:
    full_key = f"{CACHE_PREFIX}{key}"
    try:
        deleted = redis_client.delete(full_key)
        if deleted:
            logger.debug(f"Cache deleted for {full_key}")
        else:
            logger.debug(f"No cache entry to delete for {full_key}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"Cache delete failed for {full_key}: {e}")
        return False

def cache_health_check() -> Dict[str, Any]:
    """Check the health of the Redis connection."""
    try:
        redis_client.ping()
        info = redis_client.info("memory")
        return {
            "status": "healthy",
            "details": {
                "used_memory": info.get("used_memory_human", "unknown"),
                "max_memory": info.get("maxmemory_human", "unknown")
            }
        }
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "details": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in Redis health check: {e}")
        return {"status": "unhealthy", "details": str(e)}

if __name__ == "__main__":
    test_key = "test_key"
    test_value = {"data": [1, 2, 3], "status": "ok"}
    success = cache_set(test_key, test_value, ttl=10)
    print(f"Cache set: {success}")
    result = cache_get(test_key)
    print(f"Cache get: {result}")
    deleted = cache_delete(test_key)
    print(f"Cache deleted: {deleted}")
    health = cache_health_check()
    print(f"Cache health: {health}")