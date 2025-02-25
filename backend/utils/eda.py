import pandas as pd
import numpy as np
from utils.logger import logger
from typing import Dict, Any, Optional
from scipy import stats

# Helper function to refine type inference
def _refine_type_inference(series: pd.Series, col_name: str) -> str:
    """Refine field type inference with additional checks."""
    try:
        if pd.api.types.is_datetime64_any_dtype(series) or "time" in col_name.lower():
            return "timestamp"
        elif pd.api.types.is_numeric_dtype(series):
            # Check if it’s more likely an identifier (e.g., low cardinality, integer-like)
            if series.nunique() < len(series) * 0.1 and pd.api.types.is_integer_dtype(series):
                return "identifier"
            return "numeric"
        elif pd.api.types.is_string_dtype(series):
            # Check cardinality to distinguish identifiers from categorical
            if series.nunique() < len(series) * 0.1:
                return "identifier"
            return "categorical"
        elif pd.api.types.is_bool_dtype(series):
            return "boolean"
        else:
            return "unknown"
    except Exception as e:
        logger.warning(f"Type inference refinement failed for {col_name}: {e}")
        return "unknown"

def infer_field_types(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Infer field types for each column in the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.
        config (dict, optional): Configuration for inference (e.g., custom rules).

    Returns:
        dict: Mapping of column names to inferred types.
    """
    config = config or {}
    field_types = {}
    
    if df.empty:
        logger.warning("Empty DataFrame provided for type inference")
        return field_types

    for col in df.columns:
        try:
            field_type = _refine_type_inference(df[col], col)
            field_types[col] = field_type
            logger.debug(f"Inferred type for {col}: {field_type}")
        except Exception as e:
            logger.warning(f"Field type inference failed for {col}: {e}")
            field_types[col] = "unknown"
    
    return field_types

def clean_data(df: pd.DataFrame, field_types: Dict[str, str], config: Dict[str, Any]) -> pd.DataFrame:
    """
    Clean the DataFrame based on field types and configuration.

    Args:
        df (pd.DataFrame): Input DataFrame.
        field_types (dict): Mapping of column names to types.
        config (dict): Cleaning configuration (e.g., impute_method, outlier_threshold).

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """
    df = df.copy()
    config = {
        "impute_method": config.get("impute_method", "mean"),
        "outlier_threshold": config.get("outlier_threshold", 1.5),  # Default IQR multiplier
        "outlier_method": config.get("outlier_method", "iqr")       # Options: 'iqr', 'zscore'
    }

    for col, col_type in field_types.items():
        try:
            if col_type == "numeric":
                # Imputation
                if config["impute_method"] == "median":
                    df[col] = df[col].fillna(df[col].median())
                elif config["impute_method"] == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif config["impute_method"] == "mode":
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 0)
                else:
                    df[col] = df[col].fillna(0)
                    logger.debug(f"Unknown impute_method '{config['impute_method']}' for {col}, using 0")

                # Outlier handling
                if config["outlier_method"] == "iqr":
                    Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower, upper = Q1 - config["outlier_threshold"] * IQR, Q3 + config["outlier_threshold"] * IQR
                    df[col] = df[col].clip(lower=lower, upper=upper)
                elif config["outlier_method"] == "zscore":
                    z_scores = np.abs(stats.zscore(df[col].dropna()))
                    threshold = config["outlier_threshold"]
                    mask = df[col].index.isin(df[col].dropna().index[z_scores <= threshold])
                    df.loc[~mask, col] = np.nan  # Replace outliers with NaN, re-impute later if needed
                    df[col] = df[col].fillna(df[col].mean())  # Re-impute after outlier removal
                logger.debug(f"Cleaned {col} with {config['impute_method']} imputation and {config['outlier_method']} outlier handling")
            
            elif col_type == "categorical" or col_type == "identifier":
                df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "unknown")
        except Exception as e:
            logger.warning(f"Cleaning failed for {col}: {e}")
    
    return df

def transform_data(df: pd.DataFrame, field_types: Dict[str, str], config: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Transform the DataFrame by adding derived features and normalizing data.

    Args:
        df (pd.DataFrame): Input DataFrame.
        field_types (dict): Mapping of column names to types.
        config (dict, optional): Transformation configuration (e.g., window size, normalization).

    Returns:
        pd.DataFrame: Transformed DataFrame.
    """
    df = df.copy()
    config = config or {
        "rolling_window": 10,
        "min_periods": 1,
        "normalize": True,
        "add_trend": True,
        "add_roll_stats": True
    }

    numeric_cols = [col for col, t in field_types.items() if t == "numeric"]
    
    for col in numeric_cols:
        try:
            # Rolling statistics
            if config["add_roll_stats"]:
                df[f"{col}_roll_avg"] = df[col].rolling(
                    window=config["rolling_window"],
                    min_periods=config["min_periods"]
                ).mean().fillna(df[col].mean())
                df[f"{col}_roll_std"] = df[col].rolling(
                    window=config["rolling_window"],
                    min_periods=config["min_periods"]
                ).std().fillna(df[col].std())

            # Trend detection
            if config["add_trend"]:
                diff = df[col].diff()
                df[f"{col}_trend"] = np.select(
                    [diff > 0, diff < 0, diff == 0],
                    ["up", "down", "stable"],
                    default="unknown"
                )

            # Normalization
            if config["normalize"]:
                col_min, col_max = df[col].min(), df[col].max()
                if col_max - col_min > 1e-6:  # Avoid division by zero
                    df[col] = (df[col] - col_min) / (col_max - col_min)
                else:
                    df[col] = 0.0  # If range is too small, set to zero
                logger.debug(f"Normalized {col} with min: {col_min}, max: {col_max}")
                
        except Exception as e:
            logger.warning(f"Transformation failed for {col}: {e}")
    
    return df

if __name__ == "__main__":
    # Test the functions
    data = {
        "time": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "value": [10, 20, 15],
        "category": ["A", "B", "A"],
        "id": [1, 1, 1]
    }
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])

    # Test infer_field_types
    types = infer_field_types(df)
    print("Field Types:", types)

    # Test clean_data
    config = {"impute_method": "median", "outlier_threshold": 1.5, "outlier_method": "zscore"}
    cleaned_df = clean_data(df, types, config)
    print("Cleaned Data:\n", cleaned_df)

    # Test transform_data
    transformed_df = transform_data(cleaned_df, types)
    print("Transformed Data:\n", transformed_df)