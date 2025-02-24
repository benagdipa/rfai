import pandas as pd
import numpy as np
from utils.logger import logger

def infer_field_types(df: pd.DataFrame) -> dict:
    field_types = {}
    for col in df.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(df[col]) or "time" in col.lower():
                field_types[col] = "timestamp"
            elif pd.api.types.is_numeric_dtype(df[col]):
                field_types[col] = "numeric"
            elif pd.api.types.is_string_dtype(df[col]) and df[col].nunique() < len(df) * 0.1:
                field_types[col] = "identifier"
            else:
                field_types[col] = "categorical"
        except Exception as e:
            logger.warning(f"Field type inference failed for {col}: {e}")
            field_types[col] = "unknown"
    return field_types

def clean_data(df: pd.DataFrame, field_types: dict, config: dict) -> pd.DataFrame:
    df = df.copy()
    for col, col_type in field_types.items():
        if col_type == "numeric":
            if config["impute_method"] == "median":
                df[col] = df[col].fillna(df[col].median())
            elif config["impute_method"] == "mean":
                df[col] = df[col].fillna(df[col].mean())
            else:
                df[col] = df[col].fillna(0)
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower, upper = Q1 - config["outlier_threshold"] * IQR, Q3 + config["outlier_threshold"] * IQR
            df[col] = df[col].clip(lower=lower, upper=upper)
    return df

def transform_data(df: pd.DataFrame, field_types: dict) -> pd.DataFrame:
    df = df.copy()
    numeric_cols = [col for col, t in field_types.items() if t == "numeric"]
    for col in numeric_cols:
        df[f"{col}_roll_avg"] = df[col].rolling(window=10, min_periods=1).mean().fillna(df[col])
        df[f"{col}_trend"] = np.where(df[col].diff() > 0, 'up', 'down')
        df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min() + 1e-6)
    return df
