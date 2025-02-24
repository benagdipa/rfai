import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from utils.logger import logger

def train_lstm_model(data: np.ndarray, look_back: int = 10) -> Sequential:
    X, y = [], []
    for i in range(len(data) - look_back):
        X.append(data[i:i + look_back])
        y.append(data[i + look_back])
    X, y = np.array(X), np.array(y)
    
    model = Sequential()
    model.add(LSTM(50, input_shape=(look_back, 1), return_sequences=True))
    model.add(LSTM(50))
    model.add(Dense(1))
    try:
        model.compile(optimizer='adam', loss='mse')
        model.fit(X, y, epochs=10, batch_size=1, verbose=0)
        return model
    except Exception as e:
        logger.error(f"LSTM training failed: {e}")
        raise

def predict_with_lstm(model: Sequential, data: np.ndarray, steps: int = 5) -> np.ndarray:
    predictions = []
    input_seq = data[-10:].reshape(1, 10, 1)
    try:
        for _ in range(steps):
            pred = model.predict(input_seq, verbose=0)
            predictions.append(pred[0, 0])
            input_seq = np.roll(input_seq, -1, axis=1)
            input_seq[0, -1, 0] = pred[0, 0]
        return np.array(predictions)
    except Exception as e:
        logger.error(f"LSTM prediction failed: {e}")
        return np.zeros(steps)
