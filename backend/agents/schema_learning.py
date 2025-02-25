from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.eda import infer_field_types
from utils.cache import cache_set, cache_get
from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import hashlib
import json

# Helper function to merge field types
def merge_field_types(new_types: Dict[str, str], historical_types: Dict[str, str]) -> Dict[str, str]:
    """Merge new and historical field types, handling conflicts."""
    merged = new_types.copy()
    for col, hist_type in historical_types.items():
        if col not in merged or merged[col] == "unknown":
            merged[col] = hist_type
        elif merged[col] != hist_type:
            # Handle type conflicts by marking as 'mixed' or choosing the more specific type
            if merged[col] in ["numeric", "timestamp"] and hist_type in ["numeric", "timestamp"]:
                merged[col] = "numeric"  # Prefer numeric over timestamp if ambiguous
            else:
                merged[col] = "mixed"
    return merged

# Helper function to detect schema evolution
def detect_schema_changes(
    current_types: Dict[str, str],
    previous_types: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Detect changes in schema between current and previous states."""
    changes = []
    all_cols = set(current_types.keys()).union(previous_types.keys())
    for col in all_cols:
        curr_type = current_types.get(col, "missing")
        prev_type = previous_types.get(col, "missing")
        if curr_type != prev_type:
            changes.append({
                "column": col,
                "previous_type": prev_type,
                "current_type": curr_type,
                "change_type": "added" if prev_type == "missing" else "removed" if curr_type == "missing" else "modified"
            })
    return changes

# Main schema learning function
async def learn_schema(
    db: Session,
    identifier: str,
    raw_data: List[Dict[str, Any]],
    config: Dict[str, Any] = None,
    agent_id: str = "schema_learning_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Learn and update the schema for a given identifier, integrating with historical data.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        raw_data (list): Raw data to infer schema from.
        config (dict, optional): Configuration for schema learning (e.g., sample size).
        agent_id (str): Identifier for this schema learning agent.
        source_agent (str, optional): Agent that triggered this schema learning.

    Returns:
        dict: Learned schema and metadata.
    """
    logger.info(f"Agent {agent_id}: Learning schema for {identifier}")
    config = config or {
        "max_historical_rows": 1000,
        "cache_ttl": 86400,  # 24 hours
        "min_rows_for_inference": 5
    }

    # Generate cache key with config hash for uniqueness
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()
    cache_key = f"schema_{identifier}_{agent_id}_{config_hash}"
    cached = cache_get(cache_key)
    if cached:
        logger.info(f"Agent {agent_id}: Returning cached schema for {identifier}")
        await AgentEventEmitter.emit("schema_learned", cached, target=source_agent)
        return cached

    try:
        # Convert raw data to DataFrame
        df = pd.DataFrame(raw_data)
        if df.empty or len(df) < config["min_rows_for_inference"]:
            logger.warning(f"Agent {agent_id}: Insufficient data for schema inference for {identifier}")
            result = {
                "identifier": identifier,
                "field_types": {},
                "schema_changes": [],
                "status": "insufficient data",
                "message": f"Need at least {config['min_rows_for_inference']} rows",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("schema_learned", result, target=source_agent)
            return result

        # Infer field types from new data
        field_types = infer_field_types(df)

        # Fetch historical data for schema enrichment
        existing_data = (
            db.query(DynamicData)
            .filter(DynamicData.identifier == identifier)
            .order_by(DynamicData.timestamp.desc())
            .limit(config["max_historical_rows"])
            .all()
        )
        schema_changes = []
        if existing_data:
            historical_df = pd.DataFrame([d.data for d in existing_data])
            historical_types = infer_field_types(historical_df)
            field_types = merge_field_types(field_types, historical_types)
            schema_changes = detect_schema_changes(field_types, historical_types)
            logger.debug(f"Agent {agent_id}: Merged historical schema for {identifier}")

        # Prepare result
        result = {
            "identifier": identifier,
            "field_types": field_types,
            "schema_changes": schema_changes,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "new_rows": len(df),
                "historical_rows": len(existing_data) if existing_data else 0,
                "columns": list(field_types.keys())
            }
        }

        # Cache and emit event
        cache_set(cache_key, result, ttl=config["cache_ttl"])
        await AgentEventEmitter.emit("schema_learned", result, target=source_agent)

        # Notify downstream agents if schema changes are detected
        if schema_changes:
            await AgentEventEmitter.emit(
                "schema_evolved",
                {
                    "identifier": identifier,
                    "schema_changes": schema_changes,
                    "field_types": field_types,
                    "agent_id": agent_id
                },
                target="eda_agent_1"  # Inform EDA agent to adapt preprocessing
            )

        logger.info(f"Agent {agent_id}: Schema learned for {identifier}: {field_types}")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error learning schema for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "field_types": {},
            "schema_changes": [],
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("schema_learning_error", error_result, target=source_agent)
        return error_result

# Listener for multi-agent integration
async def listen_for_raw_data(agent_id: str):
    """Listen for raw data events from upstream agents."""
    while True:
        # Simulate receiving an event (e.g., from data_ingestion.py)
        event = {
            "event_type": "raw_data_ready",
            "data": {
                "identifier": "test_data",
                "raw_data": [{"value": 10, "time": "2023-01-01"}, {"value": 20, "time": "2023-01-02"}],
                "config": {"max_historical_rows": 500}
            }
        }
        if event["event_type"] == "raw_data_ready":
            logger.info(f"Agent {agent_id}: Received {event['event_type']} event")
            db = MagicMock(spec=Session)  # Replace with actual DB session
            result = await learn_schema(
                db=db,
                identifier=event["data"]["identifier"],
                raw_data=event["data"]["raw_data"],
                config=event["data"].get("config", {}),
                agent_id=agent_id,
                source_agent=event.get("source_agent", "ingestion_agent_1")
            )
            logger.info(f"Agent {agent_id}: Processed event result: {result['status']}")
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    from unittest.mock import MagicMock

    async def test_schema_learning():
        db = MagicMock(spec=Session)
        raw_data = [
            {"value": 10, "time": "2023-01-01"},
            {"value": 20, "time": "2023-01-02"}
        ]
        # Mock historical data
        mock_data = [
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": "15", "time": "2022-12-31"})
        ]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        
        result = await learn_schema(db, "test_data", raw_data)
        print(result)

    asyncio.run(test_schema_learning())