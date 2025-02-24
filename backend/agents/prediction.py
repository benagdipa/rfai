from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.ml import train_lstm_model, predict_with_lstm
from utils.logger import logger
import pandas as pd
import numpy as np

def predict_kpis(db: Session, identifier: str) -> dict:
    logger.info(f"Generating predictions for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(100).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        logger.warning(f"No numeric data found for prediction in {identifier}. Ensure your data source contains numeric columns.")
        return {"identifier": identifier, "predictions": {}, "message": "No numeric data available"}
    
    predictions = {}
    for col in numeric_cols:
        series = df[col].dropna().values[-50:]
        if len(series) >= 20:
            try:
                model = train_lstm_model(series.reshape(-1, 1))
                pred = predict_with_lstm(model, series[-10:], steps=5)
                predictions[col] = pred.tolist()
            except Exception as e:
                logger.error(f"Prediction failed for {col}: {e}")
                predictions[col] = [0] * 5
        else:
            predictions[col] = [df[col].mean()] * 5
    
    return {"identifier": identifier, "predictions": predictions}