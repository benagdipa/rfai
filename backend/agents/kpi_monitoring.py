from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

# Helper function to calculate KPIs
def calculate_kpis(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Dict[str, float]]:
    """Calculate basic KPIs for numeric columns."""
    kpis = {}
    for col in numeric_cols:
        try:
            series = df[col].dropna()
            if len(series) < 5:  # Minimum data points for meaningful stats
                continue
            kpis[col] = {
                "mean": series.mean(),
                "std": series.std(),
                "min": series.min(),
                "max": series.max(),
                "skew": stats.skew(series),
                "recent_value": series.iloc[-1],
                "trend": (series.iloc[-1] - series.iloc[0]) / len(series) if len(series) > 1 else 0
            }
        except Exception as e:
            logger.warning(f"Error calculating KPIs for {col}: {e}")
    return kpis

# Helper function to detect KPI anomalies
def detect_kpi_anomalies(
    df: pd.DataFrame,
    kpis: Dict[str, Dict[str, float]],
    thresholds: Dict[str, float]
) -> Dict[str, List[Dict[str, Any]]]:
    """Detect anomalies in KPIs based on thresholds."""
    anomalies = {}
    for col, kpi in kpis.items():
        anomalies[col] = []
        try:
            # High standard deviation relative to mean
            if kpi["std"] > kpi["mean"] * thresholds["std_to_mean_ratio"]:
                anomalies[col].append({
                    "description": f"High variability (std: {kpi['std']:.2f}, mean: {kpi['mean']:.2f})",
                    "severity": "medium"
                })

            # Extreme recent value (Z-score based)
            z_score = (kpi["recent_value"] - kpi["mean"]) / kpi["std"] if kpi["std"] > 0 else 0
            if abs(z_score) > thresholds["z_score_threshold"]:
                anomalies[col].append({
                    "description": f"Recent value anomaly (value: {kpi['recent_value']:.2f}, Z-score: {z_score:.2f})",
                    "severity": "high" if abs(z_score) > 4 else "medium"
                })

            # Significant trend
            if abs(kpi["trend"]) > thresholds["trend_threshold"]:
                anomalies[col].append({
                    "description": f"Significant trend detected (rate: {kpi['trend']:.4f})",
                    "severity": "medium"
                })

            # Skewness indicating distribution issues
            if abs(kpi["skew"]) > thresholds["skew_threshold"]:
                anomalies[col].append({
                    "description": f"Highly skewed distribution (skew: {kpi['skew']:.2f})",
                    "severity": "low"
                })
        except Exception as e:
            logger.warning(f"Error detecting anomalies for {col}: {e}")
    return anomalies

# Main KPI monitoring function
async def monitor_kpis(
    db: Session,
    identifier: str,
    config: Dict[str, Any] = None,
    agent_id: str = "kpi_monitoring_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Monitor KPIs for a given identifier and notify other agents of anomalies.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        config (dict, optional): Configuration for KPI monitoring (e.g., thresholds).
        agent_id (str): Identifier for this KPI monitoring agent.
        source_agent (str, optional): Agent that triggered this monitoring.

    Returns:
        dict: KPI monitoring results and anomalies.
    """
    logger.info(f"Agent {agent_id}: Monitoring KPIs for {identifier}")
    config = config or {
        "max_rows": 100,
        "thresholds": {
            "std_to_mean_ratio": 0.5,  # Std > 50% of mean
            "z_score_threshold": 3.0,  # Z-score > 3 for anomaly
            "trend_threshold": 0.1,    # Trend rate per data point
            "skew_threshold": 1.5      # Skewness threshold
        },
        "min_data_points": 10
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
            result = {
                "identifier": identifier,
                "anomalies_detected": False,
                "kpis": {},
                "anomalies": {},
                "status": "no data",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("kpis_monitored", result, target=source_agent)
            return result

        # Convert to DataFrame
        df = pd.DataFrame([d.data for d in data])
        if df.empty:
            logger.warning(f"Agent {agent_id}: Empty dataframe for {identifier}")
            result = {
                "identifier": identifier,
                "anomalies_detected": False,
                "kpis": {},
                "anomalies": {},
                "status": "empty data",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("kpis_monitored", result, target=source_agent)
            return result

        # Identify numeric columns
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_cols:
            logger.warning(f"Agent {agent_id}: No numeric columns found for {identifier}")
            result = {
                "identifier": identifier,
                "anomalies_detected": False,
                "kpis": {},
                "anomalies": {},
                "status": "no numeric data",
                "message": "Ensure your data source contains numeric columns",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("kpis_monitored", result, target=source_agent)
            return result

        # Calculate KPIs
        kpis = calculate_kpis(df, numeric_cols)
        if not kpis:
            logger.warning(f"Agent {agent_id}: Insufficient data for KPI calculation for {identifier}")
            result = {
                "identifier": identifier,
                "anomalies_detected": False,
                "kpis": {},
                "anomalies": {},
                "status": "insufficient data",
                "message": f"Need at least {config['min_data_points']} data points",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("kpis_monitored", result, target=source_agent)
            return result

        # Detect anomalies
        anomalies = detect_kpi_anomalies(df, kpis, config["thresholds"])
        anomalies_detected = any(len(anomaly_list) > 0 for anomaly_list in anomalies.values())

        # Prepare result
        result = {
            "identifier": identifier,
            "anomalies_detected": anomalies_detected,
            "kpis": kpis,
            "anomalies": anomalies,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "rows_analyzed": len(df),
                "numeric_columns": numeric_cols
            }
        }

        # Emit event to notify other agents
        await AgentEventEmitter.emit("kpis_monitored", result, target=source_agent)

        # Notify downstream agents if anomalies are detected
        if anomalies_detected:
            await AgentEventEmitter.emit(
                "kpi_alert",
                {
                    "identifier": identifier,
                    "anomalies": anomalies,
                    "kpis": kpis,
                    "agent_id": agent_id
                },
                target="decision_making_agent"
            )

        logger.info(f"Agent {agent_id}: KPI monitoring completed for {identifier} with anomalies: {anomalies_detected}")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error monitoring KPIs for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "anomalies_detected": False,
            "kpis": {},
            "anomalies": {},
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("kpi_monitoring_error", error_result, target=source_agent)
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
            result = await monitor_kpis(
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

    async def test_kpi_monitoring():
        db = MagicMock(spec=Session)
        # Mock data for testing
        mock_data = [
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 10, "load": 5}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 20, "load": 50}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 100, "load": 10})
        ]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        
        result = await monitor_kpis(db, "test_data")
        print(result)

    asyncio.run(test_kpi_monitoring())