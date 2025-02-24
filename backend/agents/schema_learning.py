from sqlalchemy.orm import Session
from utils.eda import infer_field_types
from utils.cache import cache_set, cache_get
from utils.logger import logger
import pandas as pd

def learn_schema(db: Session, identifier: str, raw_data: list) -> dict:
    cache_key = f"schema_{identifier}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    df = pd.DataFrame(raw_data)
    field_types = infer_field_types(df)
    
    existing_data = db.query(DynamicData).filter(DynamicData.identifier == identifier).limit(1000).all()
    if existing_data:
        historical_df = pd.DataFrame([d.data for d in existing_data])
        historical_types = infer_field_types(historical_df)
        for col, t in historical_types.items():
            if col not in field_types or field_types[col] == "unknown":
                field_types[col] = t
            elif field_types[col] != t:
                field_types[col] = "mixed"  # Handle type conflicts

    result = {"identifier": identifier, "field_types": field_types}
    cache_set(cache_key, result, ttl=86400)  # 24-hour TTL
    logger.info(f"Schema learned for {identifier}: {field_types}")
    return result
