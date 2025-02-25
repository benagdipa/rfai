from loguru import logger
import sys
import os
from typing import Optional, Dict, Any
import json
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Custom formatter for structured JSON logging (optional)
def json_formatter(record: dict) -> str:
    """Format log records as JSON for structured logging."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "file": record["file"].path,
        "line": record["line"],
        "function": record["function"],
        "extra": record["extra"],
    }
    return json.dumps(log_entry) + "\n"

# Configure logger based on parameters (no settings import at module level)
def configure_logger(
    log_level: str = "INFO",
    log_file: str = os.path.join(LOG_DIR, "app.log"),
    rotation: str = "1 week",
    retention: str = "1 month",
    use_json: bool = False,
    environment: str = "prod",
) -> None:
    """
    Configure the Loguru logger with file and console sinks.

    Args:
        log_level (str): Logging level (e.g., 'DEBUG', 'INFO', 'ERROR').
        log_file (str): Path to the log file.
        rotation (str): Log rotation policy (e.g., '1 week', '500 MB').
        retention (str): Log retention policy (e.g., '1 month', '10 files').
        use_json (bool): Whether to use JSON formatting instead of default.
        environment (str): Environment (e.g., 'dev', 'prod') to determine console logging.
    """
    # Remove default handler
    logger.remove()

    # Configure file sink
    try:
        logger.add(
            log_file,
            level=log_level,
            format=json_formatter if use_json else "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {file}:{line}",
            rotation=rotation,
            retention=retention,
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )
    except Exception as e:
        print(f"Failed to configure file logger: {e}", file=sys.stderr)
        logger.add(sys.stderr, level="ERROR")  # Fallback to stderr

    # Add console sink for development or debugging
    if environment in ["dev", "development"]:
        logger.add(
            sys.stdout,
            level="DEBUG" if log_level == "DEBUG" else "INFO",
            format="{time:HH:mm:ss} | {level:<8} | {message}",
        )

    logger.info(f"Logger configured: level={log_level}, file={log_file}, JSON={use_json}")

# Utility function to log with context
def log_with_context(
    message: str,
    level: str = "INFO",
    agent_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a message with optional agent context and extra data.

    Args:
        message (str): Log message.
        level (str): Log level (e.g., 'DEBUG', 'INFO', 'ERROR').
        agent_id (str, optional): Identifier for the agent logging the message.
        extra (dict, optional): Additional context data.
    """
    extra = extra or {}
    if agent_id:
        extra["agent_id"] = agent_id
    
    logger.bind(**extra).log(level, message)

if __name__ == "__main__":
    # Test the logger
    configure_logger()  # Default config for testing
    log_with_context("Application starting", "INFO")
    log_with_context("Processing data", "DEBUG", agent_id="test_agent_1")
    log_with_context("Error occurred", "ERROR", extra={"error_code": 500})
    
    try:
        raise ValueError("Test exception")
    except ValueError as e:
        logger.exception("Caught an exception")