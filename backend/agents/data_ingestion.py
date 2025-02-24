from sqlalchemy.orm import Session
from agents.eda_preprocessing import preprocess_data
from utils.connectors import get_connector
from utils.logger import logger
from fastapi import HTTPException

async def ingest_data(db: Session, identifier: str, source_config: dict, config: dict):
    logger.info(f"Starting data ingestion for {identifier}")
    source_type = source_config.get("type")
    
    if source_type == "csv" and "data" in source_config["config"]:
        # Handle uploaded CSV data directly
        raw_data = source_config["config"]["data"]
    else:
        connector = get_connector(source_type)
        if not connector:
            logger.error(f"Invalid source type: {source_type}")
            raise HTTPException(status_code=400, detail="Invalid source type")
        try:
            raw_data = await connector.fetch_data(source_config["config"])
        except Exception as e:
            logger.error(f"Data fetching failed for {identifier}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Data fetching failed: {str(e)}")
    
    try:
        result = await preprocess_data(db, raw_data, identifier, config)
        logger.info(f"Data ingestion completed for {identifier}")
        return result
    except Exception as e:
        logger.error(f"Data ingestion failed for {identifier}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")