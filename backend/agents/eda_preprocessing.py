from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.eda import infer_field_types, clean_data, transform_data
from utils.websocket import ws_manager
from utils.cache import cache_set, cache_get
from utils.logger import logger
from utils.ai import get_ai_insights
from utils.stats import detect_clusters
import pandas as pd
import numpy as np

async def preprocess_data(db: Session, raw_data: list, identifier: str, config: dict) -> dict:
    cache_key = f"eda_{identifier}"
    cached = cache_get(cache_key)
    if cached:
        await ws_manager.broadcast(cached)
        return cached

    df = pd.DataFrame(raw_data)
    if df.empty:
        logger.warning(f"No data for {identifier}")
        return {"status": "no data", "identifier": identifier}

    field_types = infer_field_types(df)
    timestamp_col = next((col for col, t in field_types.items() if t == "timestamp"), "timestamp")
    numeric_cols = [col for col, t in field_types.items() if t == "numeric"]

    config = config or {"impute_method": "mean", "outlier_threshold": 2.0}
    df = clean_data(df, field_types, config)
    df = transform_data(df, field_types)

    features = df[numeric_cols].values
    clusters = detect_clusters(features)
    df['cluster'] = clusters

    ai_prompt = f"Analyze this network data for trends and anomalies: {df[numeric_cols].tail(10).to_dict()}"
    ai_insights = await get_ai_insights(df[numeric_cols].tail(10).to_dict(), ai_prompt)

    result = {
        "identifier": identifier,
        "field_types": field_types,
        "summary": df.describe().to_dict(),
        "clusters": len(set(clusters)) - (1 if -1 in clusters else 0),
        "ai_insights": ai_insights
    }
    await ws_manager.broadcast(result)
    cache_set(cache_key, result, ttl=3600)

    batch_size = 1000
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        for _, row in batch.iterrows():
            data_entry = DynamicData(
                timestamp=pd.to_datetime(row[timestamp_col], errors='coerce') or pd.Timestamp.now(),
                identifier=identifier,
                data=row.to_dict()
            )
            db.add(data_entry)
        db.commit()
    return result
