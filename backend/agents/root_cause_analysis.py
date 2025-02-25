from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

# Helper function to calculate correlations
def calculate_correlations(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Dict[str, float]]:
    """Calculate Pearson correlations between numeric columns."""
    correlations = {}
    for col1 in numeric_cols:
        correlations[col1] = {}
        for col2 in numeric_cols:
            if col1 != col2:
                try:
                    series1, series2 = df[col1].dropna(), df[col2].dropna()
                    common_idx = series1.index.intersection(series2.index)
                    if len(common_idx) > 5:  # Minimum data points for correlation
                        corr, _ = pearsonr(series1.loc[common_idx], series2.loc[common_idx])
                        correlations[col1][col2] = corr
                    else:
                        correlations[col1][col2] = 0.0
                except Exception as e:
                    logger.warning(f"Error calculating correlation between {col1} and {col2}: {e}")
                    correlations[col1][col2] = 0.0
    return correlations

# Helper function to detect anomalies
def detect_anomalies(df: pd.DataFrame, numeric_cols: List[str], threshold: float = 2.0) -> Dict[str, List[int]]:
    """Detect anomalies in numeric columns using Z-scores."""
    anomalies = {}
    for col in numeric_cols:
        try:
            series = df[col].dropna()
            if len(series) < 5:
                continue
            z_scores = np.abs((series - series.mean()) / series.std())
            anomaly_indices = series.index[z_scores > threshold].tolist()
            if anomaly_indices:
                anomalies[col] = anomaly_indices
        except Exception as e:
            logger.warning(f"Error detecting anomalies in {col}: {e}")
    return anomalies

# Helper function to infer root causes
def infer_root_causes(
    df: pd.DataFrame,
    numeric_cols: List[str],
    correlations: Dict[str, Dict[str, float]],
    anomalies: Dict[str, List[int]],
    thresholds: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Infer potential root causes based on data analysis."""
    causes = []
    
    # Check throughput and latency
    if "throughput" in numeric_cols and "latency" in numeric_cols:
        throughput_avg = df["throughput"].mean()
        latency_avg = df["latency"].mean()
        if throughput_avg < thresholds["throughput_low"] and latency_avg > thresholds["latency_high"]:
            causes.append({
                "description": "Possible interference or congestion",
                "confidence": 0.9,
                "details": {
                    "throughput_avg": throughput_avg,
                    "latency_avg": latency_avg
                }
            })

    # Correlation-based causes
    for col1, corr_dict in correlations.items():
        for col2, corr in corr_dict.items():
            if abs(corr) > thresholds["correlation_threshold"] and col1 in anomalies and col2 in anomalies:
                causes.append({
                    "description": f"Strong correlation between {col1} and {col2} (corr: {corr:.2f}) suggesting a common cause",
                    "confidence": min(0.95, abs(corr)),
                    "details": {
                        "correlated_columns": [col1, col2],
                        "correlation": corr,
                        "anomaly_overlap": len(set(anomalies[col1]).intersection(anomalies[col2]))
                    }
                })

    # Anomaly-based causes
    for col, anomaly_indices in anomalies.items():
        if len(anomaly_indices) > len(df) * 0.1:  # More than 10% anomalies
            causes.append({
                "description": f"Persistent anomalies in {col} indicating a potential root issue",
                "confidence": 0.85,
                "details": {
                    "anomaly_count": len(anomaly_indices),
                    "recent_value": df[col].iloc[-1] if not df[col].empty else None
                }
            })

    return causes if causes else [{"description": "Unknown", "confidence": 0.5, "details": {}}]

# Main root cause analysis function
async def analyze_root_cause(
    db: Session,
    identifier: str,
    config: Dict[str, Any] = None,
    agent_id: str = "root_cause_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze root causes for a given identifier and notify other agents.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        config (dict, optional): Configuration for root cause analysis (e.g., thresholds).
        agent_id (str): Identifier for this root cause analysis agent.
        source_agent (str, optional): Agent that triggered this analysis.

    Returns:
        dict: Root cause analysis results.
    """
    logger.info(f"Agent {agent_id}: Analyzing root cause for {identifier}")
    config = config or {
        "max_rows": 50,
        "thresholds": {
            "throughput_low": 10.0,
            "latency_high": 50.0,
            "correlation_threshold": 0.7,
            "z_score_threshold": 2.0
        },
        "min_data_points": 5
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
                "causes": [],
                "status": "no data",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("root_cause_analyzed", result, target=source_agent)
            return result

        # Convert to DataFrame
        df = pd.DataFrame([d.data for d in data])
        if df.empty or len(df) < config["min_data_points"]:
            logger.warning(f"Agent {agent_id}: Insufficient data for {identifier}")
            result = {
                "identifier": identifier,
                "causes": [],
                "status": "insufficient data",
                "message": f"Need at least {config['min_data_points']} rows",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("root_cause_analyzed", result, target=source_agent)
            return result

        # Identify numeric columns
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_cols:
            logger.warning(f"Agent {agent_id}: No numeric columns found for {identifier}")
            result = {
                "identifier": identifier,
                "causes": [{"description": "No numeric data available", "confidence": 1.0, "details": {}}],
                "status": "no numeric data",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("root_cause_analyzed", result, target=source_agent)
            return result

        # Calculate correlations and detect anomalies
        correlations = calculate_correlations(df, numeric_cols)
        anomalies = detect_anomalies(df, numeric_cols, config["thresholds"]["z_score_threshold"])
        causes = infer_root_causes(df, numeric_cols, correlations, anomalies, config["thresholds"])

        # Prepare result
        result = {
            "identifier": identifier,
            "causes": causes,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "rows_analyzed": len(df),
                "numeric_columns": numeric_cols,
                "anomaly_counts": {col: len(indices) for col, indices in anomalies.items()}
            },
            "correlations": correlations
        }

        # Emit event to notify other agents
        await AgentEventEmitter.emit("root_cause_analyzed", result, target=source_agent)

        # Notify downstream agents if causes are identified
        if any(cause["description"] != "Unknown" for cause in causes):
            await AgentEventEmitter.emit(
                "root_cause_identified",
                {
                    "identifier": identifier,
                    "causes": causes,
                    "agent_id": agent_id
                },
                target="decision_making_agent"
            )

        logger.info(f"Agent {agent_id}: Root cause analysis completed for {identifier} with {len(causes)} causes")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error analyzing root cause for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "causes": [{"description": "Analysis failed", "confidence": 0.0, "details": {"error": str(e)}}],
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("root_cause_analysis_error", error_result, target=source_agent)
        return error_result

# Listener for multi-agent integration
async def listen_for_alerts(agent_id: str):
    """Listen for alert events from upstream agents."""
    while True:
        # Simulate receiving an event (e.g., from issue_detection.py or kpi_monitoring.py)
        event = {
            "event_type": "kpi_alert",
            "data": {"identifier": "test_data", "config": {"max_rows": 30}}
        }
        if event["event_type"] in ["kpi_alert", "action_required"]:
            logger.info(f"Agent {agent_id}: Received {event['event_type']} event")
            db = MagicMock(spec=Session)  # Replace with actual DB session
            result = await analyze_root_cause(
                db=db,
                identifier=event["data"]["identifier"],
                config=event["data"].get("config", {}),
                agent_id=agent_id,
                source_agent=event.get("source_agent", "kpi_monitoring_agent_1")
            )
            logger.info(f"Agent {agent_id}: Processed event result: {result['status']}")
        await asyncio.sleep(1)  # Polling interval

if __name__ == "__main__":
    from unittest.mock import MagicMock

    async def test_root_cause_analysis():
        db = MagicMock(spec=Session)
        # Mock data for testing
        mock_data = [
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"throughput": 5, "latency": 60}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"throughput": 8, "latency": 55}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"throughput": 15, "latency": 20})
        ]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        
        result = await analyze_root_cause(db, "test_data")
        print(result)

    asyncio.run(test_root_cause_analysis())