import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from utils.logger import logger
from typing import Dict, Any, Optional, Tuple
from sklearn.metrics import mean_squared_error

# Helper function to prepare time series data
def _prepare_time_series(
    data: np.ndarray,
    look_back: int,
    forecast_steps: int = 1
) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare data for LSTM training with lookback and forecast steps."""
    if not isinstance(data, np.ndarray) or data.size == 0:
        logger.error("Invalid data provided for time series preparation")
        raise ValueError("Data must be a non-empty NumPy array")
    if data.ndim != 1:
        logger.warning("Data should be 1D; flattening if necessary")
        data = data.flatten()

    X, y = [], []
    for i in range(len(data) - look_back - forecast_steps + 1):
        X.append(data[i:i + look_back])
        y.append(data[i + look_back:i + look_back + forecast_steps])
    X, y = np.array(X), np.array(y)
    
    if X.size == 0 or y.size == 0:
        logger.error("Insufficient data for given look_back and forecast_steps")
        raise ValueError("Not enough data points for training")
    
    return X, y

def train_lstm_model(
    data: np.ndarray,
    config: Optional[Dict[str, Any]] = None
) -> Sequential:
    """
    Train an LSTM model on the provided time series data.

    Args:
        data (np.ndarray): Input time series data (1D array).
        config (dict, optional): Configuration for LSTM training (e.g., look_back, units).

    Returns:
        Sequential: Trained LSTM model.
    """
    config = config or {
        "look_back": 10,
        "forecast_steps": 1,
        "units": [50, 50],      # Number of units in each LSTM layer
        "dropout": 0.2,         # Dropout rate for regularization
        "epochs": 10,
        "batch_size": 32,
        "validation_split": 0.2,
        "optimizer": "adam",
        "loss": "mse"
    }

    try:
        # Prepare data
        X, y = _prepare_time_series(data, config["look_back"], config["forecast_steps"])
        X = X.reshape((X.shape[0], X.shape[1], 1))  # Reshape to (samples, timesteps, features)
        if config["forecast_steps"] > 1:
            y = y.reshape((y.shape[0], y.shape[1], 1))

        # Build model
        model = Sequential()
        for i, units in enumerate(config["units"]):
            if i == 0:
                model.add(LSTM(
                    units,
                    input_shape=(config["look_back"], 1),
                    return_sequences=len(config["units"]) > 1 or config["forecast_steps"] > 1
                ))
            else:
                model.add(LSTM(units, return_sequences=i < len(config["units"]) - 1))
            model.add(Dropout(config["dropout"]))
        
        model.add(Dense(config["forecast_steps"]))  # Output layer matches forecast steps
        
        # Compile model
        model.compile(optimizer=config["optimizer"], loss=config["loss"])
        
        # Train model
        history = model.fit(
            X,
            y,
            epochs=config["epochs"],
            batch_size=config["batch_size"],
            validation_split=config["validation_split"],
            verbose=0,
            shuffle=False  # Preserve time series order
        )
        
        # Log training performance
        val_loss = history.history.get("val_loss", [None])[-1]
        train_loss = history.history["loss"][-1]
        logger.info(
            f"LSTM trained: look_back={config['look_back']}, "
            f"epochs={config['epochs']}, train_loss={train_loss:.4f}, "
            f"val_loss={val_loss:.4f if val_loss else 'N/A'}"
        )
        
        return model
    
    except Exception as e:
        logger.error(f"LSTM training failed: {e}")
        raise

def predict_with_lstm(
    model: Sequential,
    data: np.ndarray,
    steps: int,
    config: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Predict future values using a trained LSTM model.

    Args:
        model (Sequential): Trained LSTM model.
        data (np.ndarray): Input time series data (last look_back values).
        steps (int): Number of future steps to predict.
        config (dict, optional): Configuration for prediction (e.g., look_back).

    Returns:
        np.ndarray: Predicted values.
    """
    config = config or {"look_back": 10}
    look_back = config["look_back"]

    try:
        # Validate input
        if not isinstance(data, np.ndarray) or data.size < look_back:
            logger.error(f"Invalid input data; must be at least {look_back} values")
            raise ValueError(f"Data must be a NumPy array with at least {look_back} values")
        if data.ndim != 1:
            data = data.flatten()

        # Prepare initial input sequence
        input_seq = data[-look_back:].reshape((1, look_back, 1))
        predictions = []

        # Predict step-by-step
        for _ in range(steps):
            pred = model.predict(input_seq, verbose=0)
            predictions.append(pred[0, 0] if pred.shape[-1] == 1 else pred[0])
            input_seq = np.roll(input_seq, -1, axis=1)
            input_seq[0, -1, 0] = pred[0, 0] if pred.shape[-1] == 1 else pred[0][-1]

        predictions = np.array(predictions)
        logger.info(f"LSTM predicted {steps} steps with look_back={look_back}")
        return predictions

    except Exception as e:
        logger.error(f"LSTM prediction failed: {e}")
        return np.zeros(steps)

def evaluate_lstm_model(
    model: Sequential,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate the LSTM model's performance on test data.

    Args:
        model (Sequential): Trained LSTM model.
        X_test (np.ndarray): Test input sequences.
        y_test (np.ndarray): True target values.

    Returns:
        dict: Performance metrics (e.g., RMSE).
    """
    try:
        y_pred = model.predict(X_test, verbose=0)
        if y_pred.ndim == 3:
            y_pred = y_pred.reshape((y_pred.shape[0], y_pred.shape[1]))
            y_test = y_test.reshape((y_test.shape[0], y_test.shape[1]))
        
        rmse = np.sqrt(mean_squared_error(y_test.flatten(), y_pred.flatten()))
        logger.debug(f"LSTM evaluation: RMSE={rmse:.4f}")
        return {"rmse": rmse}
    except Exception as e:
        logger.error(f"LSTM evaluation failed: {e}")
        return {"rmse": float("inf")}

if __name__ == "__main__":
    # Test the functions
    np.random.seed(42)
    data = np.sin(np.linspace(0, 100, 100)) + np.random.normal(0, 0.1, 100)

    # Train model
    config = {"look_back": 5, "forecast_steps": 3, "units": [32, 16], "epochs": 5}
    model = train_lstm_model(data, config)

    # Predict
    predictions = predict_with_lstm(model, data[-10:], steps=5, config={"look_back": 5})
    print("Predictions:", predictions)

    # Evaluate
    X_test, y_test = _prepare_time_series(data, look_back=5, forecast_steps=3)
    X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))
    metrics = evaluate_lstm_model(model, X_test, y_test)
    print("Evaluation Metrics:", metrics)