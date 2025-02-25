import aiohttp
from config.settings import load_settings  # Changed import
from utils.logger import logger
from utils.cache import cache_get, cache_set
from typing import Dict, Any, Optional
import backoff
from aiohttp import ClientSession

settings = load_settings()  # Load settings locally

# Helper function to validate OpenAI response
def _validate_response(response: Dict[str, Any]) -> Optional[str]:
    """Validate and extract content from OpenAI API response."""
    try:
        if "choices" not in response or not response["choices"]:
            logger.warning("No choices in OpenAI response")
            return None
        content = response["choices"][0].get("message", {}).get("content")
        if not content:
            logger.warning("Empty content in OpenAI response")
            return None
        return content.strip()
    except Exception as e:
        logger.error(f"Failed to validate OpenAI response: {e}")
        return None

@backoff.on_exception(
    backoff.expo,
    (aiohttp.ClientError, aiohttp.ServerTimeoutError),
    max_tries=3,
    on_backoff=lambda details: logger.debug(f"Retrying OpenAI request: attempt {details['tries']}")
)
async def get_ai_insights(
    data: Dict[str, Any],
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    use_cache: bool = True
) -> str:
    config = config or {
        "model": "gpt-3.5-turbo",
        "max_tokens": 200,
        "temperature": 0.7,
        "timeout": 30
    }

    if not hasattr(settings, "OPENAI_API_KEY") or not settings.OPENAI_API_KEY:
        logger.error("OpenAI API key not configured in settings")
        return "AI insights unavailable: API key not configured"

    cache_key = f"ai_insights_{hash(frozenset(data.items()))}_{hash(prompt)}_{hash(frozenset(config.items()))}"
    if use_cache:
        cached_result = cache_get(cache_key)
        if cached_result:
            logger.debug(f"Returning cached AI insights for key: {cache_key}")
            return cached_result

    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": f"{prompt}: {data}"}],
        "max_tokens": config["max_tokens"],
        "temperature": config["temperature"]
    }
    url = "https://api.openai.com/v1/chat/completions"

    async with ClientSession() as session:
        try:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=config["timeout"])
            ) as resp:
                resp.raise_for_status()
                result = await resp.json()
                insights = _validate_response(result)
                
                if insights:
                    logger.info(f"Successfully retrieved AI insights for prompt: {prompt[:50]}...")
                    if use_cache:
                        cache_set(cache_key, insights, ttl=3600)
                    return insights
                else:
                    logger.warning("No valid insights returned from OpenAI")
                    return "No insights available"
        
        except aiohttp.ClientError as e:
            logger.error(f"AI insights request failed: {str(e)}")
            return f"Failed to retrieve AI insights: {str(e)}"
        except asyncio.TimeoutError:
            logger.error("AI insights request timed out")
            return f"Failed to retrieve AI insights: Request timed out after {config['timeout']} seconds"
        except Exception as e:
            logger.error(f"Unexpected error in AI insights request: {str(e)}")
            return f"Failed to retrieve AI insights: {str(e)}"

if __name__ == "__main__":
    async def test_ai_insights():
        data = {"value": [1, 2, 3], "load": [10, 20, 30]}
        prompt = "Analyze this data for trends"
        config = {"model": "gpt-3.5-turbo", "max_tokens": 100, "temperature": 0.5}
        
        result = await get_ai_insights(data, prompt, config)
        print("AI Insights:", result)

    import asyncio
    asyncio.run(test_ai_insights())