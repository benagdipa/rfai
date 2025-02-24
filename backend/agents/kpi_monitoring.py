from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.logger import logger
import pandas as pd

def monitor_kpis(db: Session, identifier: str) -> dict:
    logger.info(f"Monitoring KPIs for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(100).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        logger.warning(f"No numeric data found for {identifier}. Ensure your data source contains numeric columns.")
        return {"identifier": identifier, "anomalies_detected": False, "message": "No numeric data available"}
    
    anomalies = {col: len(df[col].dropna()) > 10 and df[col].std() > df[col].mean() * 0.5 for col in numeric_cols}
    return {"identifier": identifier, "anomalies_detected": any(anomalies.values()), "numeric_columns": numeric_cols}