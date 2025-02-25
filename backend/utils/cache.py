import redis
import json
from config.settings import settings
from utils.logger import logger
from typing import Any, Optional, Union
import backoff
from redis.exceptions import ConnectionError, TimeoutError

# Redis client with connection pooling
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    max_connections=20,         # Connection pool size
    decode_responses=True,      # Return strings instead of bytes
    socket_timeout=5,           # Timeout for socket operations
    socket_connect_timeout=5    # Timeout for initial connection
)

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

# Retry decorator for Redis operations
@backoff.on_exception(
    backoff.expo,
    (ConnectionError, TimeoutError),
    max_tries=3,
    on_backoff=lambda details: logger.debug(f"Retrying Redis operation: attempt {details['tries']}")
)
def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    Set a value in the Redis cache with an optional TTL.

    Args:
        key (str): Cache key.
        value (Any): Value to cache (must be JSON-serializable).
        ttl (int): Time-to-live in seconds (default: 3600).

    Returns:
        bool: True if successful, False otherwise.
    """
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
    """
    Retrieve a value from the Redis cache.

    Args:
        key (str): Cache key.

    Returns:
        Any: Cached value if found and deserializable, None otherwise.
    """
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
    """
    Delete a key from the Redis cache.

    Args:
        key (str): Cache key.

    Returns:
        bool: True if deleted, False otherwise.
    """
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
    """
    Check the health of the Redis connection.

    Returns:
        dict: Health status and details.
    """
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
    # Test the cache functions
    test_key = "test_key"
    test_value = {"data": [1, 2, 3], "status": "ok"}

    # Set cache
    success = cache_set(test_key, test_value, ttl=10)
    print(f"Cache set: {success}")

    # Get cache
    result = cache_get(test_key)
    print(f"Cache get: {result}")

    # Delete cache
    deleted = cache_delete(test_key)
    print(f"Cache deleted: {deleted}")

    # Health check
    health = cache_health_check()
    print(f"Cache health: {health}")