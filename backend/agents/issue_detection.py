from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.stats import detect_clusters
from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Helper function to detect anomalies
def detect_anomalies(df: pd.DataFrame, numeric_cols: List[str], contamination: float = 0.1) -> np.ndarray:
    """Detect anomalies using Isolation Forest."""
    try:
        features = df[numeric_cols].values
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        model = IsolationForest(contamination=contamination, random_state=42)
        predictions = model.fit_predict(scaled_features)
        return predictions  # -1 for anomalies, 1 for normal
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return np.ones(len(df))  # Default to normal if detection fails

# Helper function to analyze trends
def detect_trends(df: pd.DataFrame, numeric_cols: List[str], window: int = 10) -> List[Dict[str, Any]]:
    """Detect trends in numeric columns."""
    trends = []
    for col in numeric_cols:
        try:
            rolling_mean = df[col].rolling(window=window, min_periods=1).mean()
            diff = rolling_mean.diff()
            if diff.iloc[-1] > 0 and (diff > 0).sum() > window * 0.7:
                trends.append({"column": col, "trend": "increasing", "magnitude": diff.iloc[-1]})
            elif diff.iloc[-1] < 0 and (diff < 0).sum() > window * 0.7:
                trends.append({"column": col, "trend": "decreasing", "magnitude": diff.iloc[-1]})
        except Exception as e:
            logger.warning(f"Error detecting trend in {col}: {e}")
    return trends

# Main issue detection function
async def detect_issues(
    db: Session,
    identifier: str,
    config: Dict[str, Any] = None,
    agent_id: str = "issue_detection_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect issues in the data for a given identifier and notify other agents.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        config (dict, optional): Configuration for issue detection (e.g., thresholds).
        agent_id (str): Identifier for this issue detection agent.
        source_agent (str, optional): Agent that triggered this detection.

    Returns:
        dict: Detected issues and metadata.
    """
    logger.info(f"Agent {agent_id}: Detecting issues for {identifier}")
    config = config or {
        "max_rows": 100,
        "contamination": 0.1,  # For anomaly detection
        "trend_window": 10,
        "cluster_threshold": 2  # Min number of clusters to flag an issue
    }

    try:
        # Fetch recent data from the database
        data = (
            db.query(DynamicData)
            .filter(DynamicData.identifier == identifier)
            .order_by(DynamicData.timestamp.desc())
            .limit(config["max_rows"])
            .all()
        )
        if not data:
            logger.warning(f"Agent {agent_id}: No data found for {identifier}")
            result = {"identifier": identifier, "issues": [], "status": "no data", "agent_id": agent_id}
            await AgentEventEmitter.emit("issues_detected", result, target=source_agent)
            return result

        # Convert to DataFrame
        df = pd.DataFrame([d.data for d in data])
        if df.empty:
            logger.warning(f"Agent {agent_id}: Empty dataframe for {identifier}")
            result = {"identifier": identifier, "issues": [], "status": "empty data", "agent_id": agent_id}
            await AgentEventEmitter.emit("issues_detected", result, target=source_agent)
            return result

        # Identify numeric columns
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_cols:
            logger.info(f"Agent {agent_id}: No numeric columns found for {identifier}")
            result = {"identifier": identifier, "issues": [], "status": "no numeric data", "agent_id": agent_id}
            await AgentEventEmitter.emit("issues_detected", result, target=source_agent)
            return result

        # Initialize issues list
        issues = []

        # 1. Cluster-based issue detection
        features = df[numeric_cols].values
        clusters = detect_clusters(features, method="dbscan", eps=0.5, min_samples=3)
        n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)  # Exclude noise (-1)
        if n_clusters >= config["cluster_threshold"]:
            issues.append({
                "description": f"Detected {n_clusters} distinct clusters indicating potential performance degradation",
                "severity": "medium",
                "details": {"n_clusters": n_clusters}
            })

        # 2. Anomaly detection
        anomaly_predictions = detect_anomalies(df, numeric_cols, config["contamination"])
        anomaly_count = (anomaly_predictions == -1).sum()
        if anomaly_count > 0:
            issues.append({
                "description": f"Detected {anomaly_count} anomalies in numeric data",
                "severity": "high" if anomaly_count > len(df) * 0.2 else "medium",
                "details": {"anomaly_indices": np.where(anomaly_predictions == -1)[0].tolist()}
            })

        # 3. Trend detection
        trends = detect_trends(df, numeric_cols, config["trend_window"])
        for trend in trends:
            severity = "low" if abs(trend["magnitude"]) < 1 else "medium"
            issues.append({
                "description": f"Trend detected in {trend['column']}: {trend['trend']} (magnitude: {trend['magnitude']:.2f})",
                "severity": severity,
                "details": trend
            })

        # Prepare result
        result = {
            "identifier": identifier,
            "issues": issues,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "rows_analyzed": len(df),
                "numeric_columns": numeric_cols,
                "cluster_count": n_clusters,
                "anomaly_count": anomaly_count
            }
        }

        # Emit event to notify other agents
        await AgentEventEmitter.emit("issues_detected", result, target=source_agent)
        
        # Notify downstream agents if issues are found
        if issues:
            await AgentEventEmitter.emit(
                "action_required",
                {
                    "identifier": identifier,
                    "issues": issues,
                    "agent_id": agent_id
                },
                target="decision_making_agent"
            )

        logger.info(f"Agent {agent_id}: Issue detection completed for {identifier} with {len(issues)} issues")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error detecting issues for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "issues": [],
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("issue_detection_error", error_result, target=source_agent)
        return error_result

# Listener for multi-agent integration
async def listen_for_data_ready(agent_id: str):
    """Listen for data readiness events from upstream agents."""
    while True:
        # Simulate receiving an event (e.g., from eda_preprocessing.py)
        event = {
            "event_type": "data_ready",
            "data": {"identifier": "test_data", "config": {"max_rows": 50}}
        }
        if event["event_type"] == "data_ready":
            logger.info(f"Agent {agent_id}: Received {event['event_type']} event")
            db = MagicMock(spec=Session)  # Replace with actual DB session
            result = await detect_issues(
                db=db,
                identifier=event["data"]["identifier"],
                config=event["data"].get("config", {}),
                agent_id=agent_id,
                source_agent=event.get("source_agent", "eda_agent_1")
            )
            logger.info(f"Agent {agent_id}: Processed event result: {result['status']}")
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    from unittest.mock import MagicMock

    async def test_issue_detection():
        db = MagicMock(spec=Session)
        # Mock data for testing
        mock_data = [
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 10, "load": 5}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 20, "load": 50}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 15, "load": 10})
        ]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        
        result = await detect_issues(db, "test_data")
        print(result)

    asyncio.run(test_issue_detection())