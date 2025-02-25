from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.ml import train_lstm_model, predict_with_lstm
from utils.logger import logger
from agents.eda_preprocessing import AgentEventEmitter
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error

# Helper function to prepare time series data
def prepare_time_series(
    series: np.ndarray,
    lookback: int,
    forecast_steps: int
) -> tuple[np.ndarray, np.ndarray]:
    """Prepare data for LSTM prediction with lookback window."""
    X, y = [], []
    for i in range(len(series) - lookback - forecast_steps + 1):
        X.append(series[i:i + lookback])
        y.append(series[i + lookback:i + lookback + forecast_steps])
    return np.array(X), np.array(y)

# Helper function to evaluate model performance
def evaluate_model(
    actual: np.ndarray,
    predicted: np.ndarray
) -> Dict[str, float]:
    """Evaluate prediction performance using RMSE."""
    try:
        rmse = np.sqrt(mean_squared_error(actual, predicted))
        return {"rmse": rmse}
    except Exception as e:
        logger.warning(f"Error evaluating model: {e}")
        return {"rmse": float("inf")}

# Main prediction function
async def predict_kpis(
    db: Session,
    identifier: str,
    config: Dict[str, Any] = None,
    agent_id: str = "prediction_agent_1",
    source_agent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict future KPIs for a given identifier and notify other agents.

    Args:
        db (Session): Database session.
        identifier (str): Unique identifier for the data.
        config (dict, optional): Configuration for prediction (e.g., lookback, steps).
        agent_id (str): Identifier for this prediction agent.
        source_agent (str, optional): Agent that triggered this prediction.

    Returns:
        dict: Predicted KPIs and metadata.
    """
    logger.info(f"Agent {agent_id}: Generating predictions for {identifier}")
    config = config or {
        "max_rows": 100,
        "lookback": 10,      # Number of past timesteps to use
        "forecast_steps": 5, # Number of future steps to predict
        "min_data_points": 20,
        "validation_split": 0.2  # Fraction of data for validation
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
                "predictions": {},
                "status": "no data",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("predictions_generated", result, target=source_agent)
            return result

        # Convert to DataFrame
        df = pd.DataFrame([d.data for d in data])
        if df.empty or len(df) < config["min_data_points"]:
            logger.warning(f"Agent {agent_id}: Insufficient data for {identifier}")
            result = {
                "identifier": identifier,
                "predictions": {},
                "status": "insufficient data",
                "message": f"Need at least {config['min_data_points']} rows",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("predictions_generated", result, target=source_agent)
            return result

        # Identify numeric columns
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_cols:
            logger.warning(f"Agent {agent_id}: No numeric columns found for {identifier}")
            result = {
                "identifier": identifier,
                "predictions": {},
                "status": "no numeric data",
                "message": "Ensure your data source contains numeric columns",
                "agent_id": agent_id
            }
            await AgentEventEmitter.emit("predictions_generated", result, target=source_agent)
            return result

        # Generate predictions for each numeric column
        predictions = {}
        performance = {}
        for col in numeric_cols:
            series = df[col].dropna().values
            if len(series) >= config["min_data_points"]:
                try:
                    # Prepare data with lookback window
                    series = series[-config["max_rows"]:]  # Limit to max_rows
                    X, y = prepare_time_series(series, config["lookback"], config["forecast_steps"])
                    if len(X) == 0:
                        logger.warning(f"Agent {agent_id}: Not enough data after lookback for {col}")
                        predictions[col] = [float(series.mean())] * config["forecast_steps"]
                        performance[col] = {"rmse": float("inf")}
                        continue

                    # Split into train and validation
                    split_idx = int(len(X) * (1 - config["validation_split"]))
                    X_train, X_val = X[:split_idx], X[split_idx:]
                    y_train, y_val = y[:split_idx], y[split_idx:]

                    # Train LSTM model
                    model = train_lstm_model(X_train.reshape(-1, config["lookback"], 1))
                    pred = predict_with_lstm(
                        model,
                        series[-config["lookback"]:].reshape(1, -1, 1),
                        steps=config["forecast_steps"]
                    )
                    predictions[col] = pred.flatten().tolist()

                    # Evaluate performance on validation set if available
                    if len(X_val) > 0:
                        val_pred = predict_with_lstm(
                            model,
                            X_val[:, -config["lookback"]:].reshape(-1, config["lookback"], 1),
                            steps=config["forecast_steps"]
                        )
                        performance[col] = evaluate_model(y_val.flatten(), val_pred.flatten())
                    else:
                        performance[col] = {"rmse": None}
                except Exception as e:
                    logger.error(f"Agent {agent_id}: Prediction failed for {col}: {e}")
                    predictions[col] = [float(series.mean())] * config["forecast_steps"]
                    performance[col] = {"rmse": float("inf")}
            else:
                logger.warning(f"Agent {agent_id}: Too few data points for {col}")
                predictions[col] = [float(series.mean())] * config["forecast_steps"]
                performance[col] = {"rmse": float("inf")}

        # Prepare result
        result = {
            "identifier": identifier,
            "predictions": predictions,
            "status": "success",
            "agent_id": agent_id,
            "source_agent": source_agent,
            "timestamp": datetime.utcnow().isoformat(),
            "data_summary": {
                "rows_analyzed": len(df),
                "numeric_columns": numeric_cols
            },
            "performance": performance
        }

        # Emit event to notify other agents
        await AgentEventEmitter.emit("predictions_generated", result, target=source_agent)

        # Notify downstream agents if predictions are meaningful
        if any(len(pred) > 0 and perf["rmse"] != float("inf") for col, perf in performance.items()):
            await AgentEventEmitter.emit(
                "predictions_available",
                {
                    "identifier": identifier,
                    "predictions": predictions,
                    "performance": performance,
                    "agent_id": agent_id
                },
                target="decision_making_agent"
            )

        logger.info(f"Agent {agent_id}: Predictions completed for {identifier}")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id}: Error generating predictions for {identifier}: {e}")
        error_result = {
            "identifier": identifier,
            "predictions": {},
            "status": "error",
            "message": str(e),
            "agent_id": agent_id,
            "source_agent": source_agent
        }
        await AgentEventEmitter.emit("prediction_error", error_result, target=source_agent)
        return error_result

# Listener for multi-agent integration
async def listen_for_data_ready(agent_id: str):
    """Listen for data readiness events from upstream agents."""
    while True:
        # Simulate receiving an event (e.g., from eda_preprocessing.py)
        event = {
            "event_type": "data_ready",
            "data": {"identifier": "test_data", "config": {"lookback": 5, "forecast_steps": 3}}
        }
        if event["event_type"] == "data_ready":
            logger.info(f"Agent {agent_id}: Received {event['event_type']} event")
            db = MagicMock(spec=Session)  # Replace with actual DB session
            result = await predict_kpis(
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

    async def test_prediction():
        db = MagicMock(spec=Session)
        # Mock data for testing
        mock_data = [
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 10, "load": 5}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 20, "load": 50}),
            DynamicData(timestamp=datetime.now(), identifier="test_data", data={"value": 15, "load": 10})
        ]
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data
        
        result = await predict_kpis(db, "test_data")
        print(result)

    asyncio.run(test_prediction())