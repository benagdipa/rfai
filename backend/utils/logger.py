from loguru import logger

logger.add("logs/app.log", rotation="1 week", retention="1 month", level="INFO")
