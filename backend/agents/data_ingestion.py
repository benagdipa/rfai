from sqlalchemy.orm import Session
from agents.eda_preprocessing import preprocess_data, AgentEventEmitter
from utils.connectors import get_connector
from utils.logger import logger
from fastapi import HTTPException
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

# Configuration validation for ingestion
def validate_source_config(source_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and provide defaults for source configuration."""
    required_fields = ["type"]
    default_config = {
        "timeout": 30,  # Default timeout in seconds for connectors
        "retry_attempts": 3,  # Default retry attempts for failed fetches
        "agent_id": "ingestion_agent_1"  # Default agent identifier
    }

    if not all(field in source_config for field in required_fields):
        missing = [field for field in required_fields if field not in source_config]
        logger.error(f"Missing required fields in source_config: {missing}")
        raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")

    source_config = {**default_config, **source_config}
    return source_config

# Retry wrapper for connector fetch
async def fetch_with_retries(
    connector: Any,
    config: Dict[str, Any],
    retries: int,
    timeout: int,
    agent_id: str
) -> list:
    """Fetch data with retries on failure."""
    attempt = 0
    while attempt < retries:
        try:
            raw_data = await asyncio.wait_for(
                connector.fetch_data(config),
                timeout=timeout
            )
            return raw_data
        except asyncio.TimeoutError:
            logger.warning(f"Agent {agent_id}: Fetch timeout on attempt {attempt + 1}")
            attempt += 1
        except Exception as e:
            logger.warning(f"Agent {agent_id}: Fetch failed on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt == retries:
                raise
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
    raise HTTPException(status_code=500, detail="Max retries exceeded for data fetch")

# Main ingestion function
async def ingest_data(
    db: Session,
    identifier: str,
    source_config: Dict[str, Any],
    config: Dict[str, Any],
    agent_id: str = "ingestion_agent_1",
    target_agent: Optional[str] = "eda_agent_1"
) -> Dict[str, Any]:
    """
    Ingests data from the specified source, preprocesses it, and notifies downstream agents.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        source_config (dict): Configuration for the data source.
        config (dict): Additional configuration for preprocessing.
        agent_id (str): Identifier for this ingestion agent.
        target_agent (str, optional): Target agent for preprocessing (default: eda_agent_1).

    Returns:
        dict: Result of the preprocessing step.

    Raises:
        HTTPException: If there's an error during data ingestion or preprocessing.
    """
    logger.info(f"Agent {agent_id}: Starting data ingestion for {identifier}")

    try:
        # Validate source_config
        source_config = validate_source_config(source_config)
        source_type = source_config["type"]
        source_specific_config = source_config.get("config", {})

        # Fetch data
        if source_type == "csv" and "data" in source_specific_config:
            # Handle uploaded CSV data directly
            raw_data = source_specific_config["data"]
            logger.debug(f"Agent {agent_id}: Using directly provided CSV data")
        else:
            connector = get_connector(source_type)
            if not connector:
                logger.error(f"Agent {agent_id}: Invalid source type: {source_type}")
                raise HTTPException(status_code=400, detail=f"Invalid source type: {source_type}")

            # Fetch data with retries
            raw_data = await fetch_with_retries(
                connector,
                source_specific_config,
                source_config["retry_attempts"],
                source_config["timeout"],
                agent_id
            )
            logger.info(f"Agent {agent_id}: Data fetched successfully from {source_type}")

        # Emit event to notify raw data availability
        await AgentEventEmitter.emit(
            "raw_data_ready",
            {
                "identifier": identifier,
                "raw_data": raw_data,
                "config": config,
                "source_agent": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            target=target_agent
        )

        # Delegate to EDA preprocessing agent
        result = await preprocess_data(
            db=db,
            raw_data=raw_data,
            identifier=identifier,
            config=config,
            agent_id=target_agent,
            source_agent=agent_id
        )

        # Log and return result
        if result["status"] == "success":
            logger.info(f"Agent {agent_id}: Data ingestion and preprocessing completed for {identifier}")
        else:
            logger.warning(f"Agent {agent_id}: Preprocessing returned non-success status: {result['status']}")

        return result

    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise e
    except Exception as e:
        # Log and raise a 500 error for other exceptions
        logger.error(f"Agent {agent_id}: Data ingestion failed for {identifier}: {str(e)}")
        await AgentEventEmitter.emit(
            "ingestion_error",
            {
                "identifier": identifier,
                "error": str(e),
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            target=target_agent
        )
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

# Example listener for external triggers (e.g., API or queue)
async def listen_for_ingestion_requests(agent_id: str):
    """Listen for ingestion requests from external sources or other agents."""
    while True:
        # Simulate an ingestion request (e.g., from FastAPI or message queue)
        request = {
            "identifier": "test_data",
            "source_config": {"type": "csv", "config": {"data": [{"value": 10}, {"value": 20}]}}),
            "config": {"impute_method": "mean"}
        }
        db = MagicMock(spec=Session)  # Replace with actual DB session
        try:
            result = await ingest_data(
                db=db,
                identifier=request["identifier"],
                source_config=request["source_config"],
                config=request["config"],
                agent_id=agent_id
            )
            logger.info(f"Agent {agent_id}: Processed ingestion request: {result}")
        except Exception as e:
            logger.error(f"Agent {agent_id}: Failed to process ingestion request: {e}")
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    from unittest.mock import MagicMock

    async def test_ingestion():
        db = MagicMock(spec=Session)
        source_config = {
            "type": "csv",
            "config": {"data": [{"timestamp": "2023-01-01", "value": 10}, {"timestamp": "2023-01-02", "value": 20}]}
        }
        config = {"impute_method": "median"}
        result = await ingest_data(db, "test_data", source_config, config)
        print(result)

    asyncio.run(test_ingestion())