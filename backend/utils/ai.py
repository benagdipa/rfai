import aiohttp
from config.settings import settings
from utils.logger import logger

async def get_ai_insights(data: dict, prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": f"{prompt}: {data}"}],
            "max_tokens": 200
        }
        try:
            async with session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers) as resp:
                result = await resp.json()
                return result["choices"][0]["message"]["content"] if "choices" in result else "No insights available"
        except Exception as e:
            logger.error(f"AI insights request failed: {e}")
            return "Failed to retrieve AI insights"
