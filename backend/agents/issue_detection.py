from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.stats import detect_clusters
from utils.logger import logger
import pandas as pd

def detect_issues(db: Session, identifier: str) -> dict:
    logger.info(f"Detecting issues for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(100).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        return {"identifier": identifier, "issues": []}

    features = df[numeric_cols].values
    clusters = detect_clusters(features)
    issues = []
    if len(set(clusters)) > 1:  # Multiple clusters indicate potential issues
        issues.append({"description": "Performance degradation detected", "severity": "medium"})
    
    return {"identifier": identifier, "issues": issues}
