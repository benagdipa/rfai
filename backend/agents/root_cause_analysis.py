from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.logger import logger
import pandas as pd

def analyze_root_cause(db: Session, identifier: str) -> dict:
    logger.info(f"Analyzing root cause for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(50).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        return {"identifier": identifier, "cause": "No numeric data available"}

    avg_values = {col: df[col].mean() for col in numeric_cols}
    if 'throughput' in avg_values and 'latency' in avg_values:
        if avg_values['throughput'] < 10 and avg_values['latency'] > 50:
            return {"identifier": identifier, "cause": "Possible interference or congestion"}
    return {"identifier": identifier, "cause": "Unknown"}
