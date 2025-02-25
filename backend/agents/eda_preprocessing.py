from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.eda import infer_field_types
from utils.websocket import ws_manager
from utils.cache import cache_set, cache_get
from utils.logger import logger
from utils.ai import get_ai_insights
from utils.stats import detect_clusters
import pandas as pd
import numpy as np
import hashlib
import json
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

# Event emitter for multi-agent communication
class AgentEventEmitter:
    """Simple event emitter for multi-agent communication."""
    @staticmethod
    async def emit(event_type: str, data: Dict[str, Any], target: Optional[str] = None):
        """Emit an event to the WebSocket manager or other agents."""
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "target_agent": target
        }
        await ws_manager.broadcast(payload)
        logger.debug(f"Emitted event: {event_type} to {target or 'all agents'}")

# Enhanced clean_data function
def clean_data(df: pd.DataFrame, field_types: Dict[str, str], config: Dict[str, Any]) -> pd.DataFrame:
    """Clean the dataframe based on field types and configuration."""
    impute_method = config.get("impute_method", "mean")
    outlier_threshold = config.get("outlier_threshold", 2.0)

    for col, col_type in field_types.items():
        try:
            if col_type == "numeric":
                if impute_method == "mean":
                    df[col].fillna(df[col].mean(), inplace=True)
                elif impute_method == "median":
                    df[col].fillna(df[col].median(), inplace=True)
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                df.loc[z_scores > outlier_threshold, col] = np.nan
            elif col_type == "categorical":
                df[col].fillna(df[col].mode()[0], inplace=True)
        except Exception as e:
            logger.warning(f"Error cleaning column {col}: {e}")
    return df

# Enhanced transform_data function
def transform_data(df: pd.DataFrame, field_types: Dict[str, str], config: Dict[str, Any]) -> pd.DataFrame:
    """Transform the dataframe with scaling and encoding."""
    try:
        numeric_cols = [col for col, t in field_types.items() if t == "numeric"]
        if numeric_cols:
            scaler = StandardScaler()
            df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

        categorical_cols = [col for col, t in field_types.items() if t == "categorical"]
        if categorical_cols and config.get("encode_categorical", True):
            df = pd.get_dummies(df, columns=categorical_cols, prefix=categorical_cols)
    except Exception as e:
        logger.error(f"Error transforming data: {e}")
    return df

# Enhanced detect_clusters function
def detect_clusters(features: np.ndarray, method: str = "kmeans", **kwargs) -> np.ndarray:
    """Detect clusters in the data using the specified method."""
    try:
        if method == "kmeans":
            clusterer = KMeans(**kwargs)
        elif method == "dbscan":
            clusterer = DBSCAN(**kwargs)
        else:
            raise ValueError(f"Unsupported clustering method: {method}")
        return clusterer.fit_predict(features)
    except Exception as e:
        logger.error(f"Error in clustering: {e}")
        return np.full(features.shape[0], -1)

# Helper function to generate cache key
def generate_cache_key(identifier: str, config: Dict[str, Any], agent_id: str) -> str:
    """Generate a unique cache key including agent ID."""
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()
    return f"eda_{identifier}_{agent_id}_{config_hash}"

# Configuration validation
def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and provide defaults for the configuration."""
    default_config = {
        "impute_method": "mean",
        "outlier_threshold": 2.0,
        "clustering_method": "kmeans",
        "clustering_params": {"n_clusters": 3},
        "batch_size": 1000,
        "encode_categorical": True,
        "agent_priority": "normal"  # For multi-agent scheduling
    }
    config = {**default_config, **(config or {})}

    if config["impute_method"] not in ["mean", "median"]:
        logger.warning(f"Unsupported impute method: {config['impute_method']}. Using 'mean'.")
        config["impute_method"] = "mean"
    if config["clustering_method"] not in ["kmeans", "dbscan"]:
        logger.warning(f"Unsupported clustering method: {config['clustering_method']}. Using 'kmeans'.")
        config["clustering_method"] = "kmeans"
    return config

# Main preprocessing agent function
async def preprocess_data(
    db: Session,
    raw_data: list,
    identifier: str,
    config: Dict[str, Any],
    agent_id: str = "eda_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """Preprocess raw data as part of a multi-agent system."""
    try:
        # Validate and prepare config
        config = validate_config(config)
        cache_key = generate_cache_key(identifier, config, agent_id)
        
        # Check cache first
        cached = cache_get(cache_key)
        if cached:
            logger.info(f"Agent {agent_id} returning cached result for {identifier}")
            await AgentEventEmitter.emit("eda_complete", cached, target=source_agent)
            return cached

        # Convert raw data to DataFrame
        df = pd.DataFrame(raw_data)
        if df.empty:
            logger.warning(f"Agent {agent_id}: No data provided for {identifier}")
            result = {"status": "no data", "identifier": identifier, "agent_id": agent_id}
            await AgentEventEmitter.emit("eda_error", result, target=source_agent)
            return result

        # Infer field types and extract columns
        field_types = infer_field_types(df)
        timestamp_col = next((col for col, t in field_types.items() if t == "timestamp"), "timestamp")
        numeric_cols = [col for col, t in field_types.items() if t == "numeric"]

        if not numeric_cols:
            logger.warning(f"Agent {agent_id}: No numeric columns found for {identifier}")
            result = {
                "status": "error",
                "message": "No numeric data to analyze",
                "identifier": identifier,
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("eda_error", result, target=source_agent)
            return result

        # Clean and transform data
        df = clean_data(df, field_types, config)
        df = transform_data(df, field_types, config)

        # Clustering
        features = df[numeric_cols].values
        clustering_method = config.get("clustering_method")
        clustering_params = config.get("clustering_params", {})
        clusters = detect_clusters(features, method=clustering_method, **clustering_params)
        df['cluster'] = clusters

        # AI Insights
        ai_prompt = (
            f"Analyze this network data for trends and anomalies from agent {agent_id}. "
            f"Summary statistics: {df[numeric_cols].describe().to_dict()}"
        )
        ai_insights = await get_ai_insights(df[numeric_cols].to_dict(), ai_prompt)

        # Prepare result with agent metadata
        result = {
            "identifier": identifier,
            "status": "success",
            "field_types": field_types,
            "summary": df.describe().to_dict(),
            "clusters": len(set(clusters)) - (1 if -1 in clusters else 0),
            "ai_insights": ai_insights,
            "agent_id": agent_id,
            "source_agent": source_agent,
            "processed_at": datetime.utcnow().isoformat()
        }

        # Emit event and cache result
        await AgentEventEmitter.emit("eda_complete", result, target=source_agent)
        cache_set(cache_key, result, ttl=3600)

        # Batch insert into database
        batch_size = config.get("batch_size")
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            logger.info(f"Agent {agent_id}: Processing batch {i // batch_size + 1} for {identifier}")
            for _, row in batch.iterrows():
                data_entry = DynamicData(
                    timestamp=pd.to_datetime(row[timestamp_col], errors='coerce') or pd.Timestamp.now(),
                    identifier=identifier,
                    data={**row.to_dict(), "agent_id": agent_id}
                )
                db.add(data_entry)
            db.commit()

        # Notify downstream agents (e.g., visualization or decision-making agents)
        await AgentEventEmitter.emit("data_ready", {
            "identifier": identifier,
            "numeric_cols": numeric_cols,
            "cluster_col": "cluster",
            "agent_id": agent_id
        }, target="visualization_agent")

        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error processing data for {identifier}: {e}")
        error_result = {
            "status": "error",
            "message": str(e),
            "identifier": identifier,
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("eda_error", error_result, target=source_agent)
        return error_result

# Example agent listener (for multi-agent integration)
async def listen_for_events(agent_id: str):
    """Example listener for incoming events from other agents."""
    while True:
        # Simulate receiving an event (e.g., via WebSocket or message queue)
        event = {"event_type": "raw_data_ready", "data": {"raw_data": [], "identifier": "test", "config": {}}}
        if event["event_type"] == "raw_data_ready":
            logger.info(f"Agent {agent_id} received event: {event['event_type']}")
            db = MagicMock(spec=Session)  # Replace with actual DB session
            await preprocess_data(
                db,
                event["data"]["raw_data"],
                event["data"]["identifier"],
                event["data"]["config"],
                agent_id=agent_id,
                source_agent=event.get("source_agent")
            )
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    from unittest.mock import MagicMock

    async def test_multi_agent():
        db = MagicMock(spec=Session)
        raw_data = [
            {"timestamp": "2023-01-01", "value": 10, "category": "A"},
            {"timestamp": "2023-01-02", "value": 20, "category": "B"},
            {"timestamp": "2023-01-03", "value": 15, "category": "A"}
        ]
        config = {"impute_method": "median", "clustering_method": "dbscan", "clustering_params": {"eps": 0.5}}
        result = await preprocess_data(db, raw_data, "test_data", config, agent_id="eda_agent_1", source_agent="ingestion_agent")
        print(result)

    asyncio.run(test_multi_agent())