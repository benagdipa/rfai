import redis
import json
from config.settings import settings
from utils.logger import logger

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def cache_set(key: str, value: dict, ttl: int = 3600):
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.error(f"Cache set failed for {key}: {e}")

def cache_get(key: str) -> dict:
    try:
        result = redis_client.get(key)
        return json.loads(result) if result else None
    except Exception as e:
        logger.error(f"Cache get failed for {key}: {e}")
        return None
