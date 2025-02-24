from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from utils.database import get_db
from utils.security import oauth2_scheme
from agents import data_ingestion, kpi_monitoring, prediction
from pydantic import BaseModel
import pandas as pd
import io

router = APIRouter()

class SourceConfig(BaseModel):
    type: str
    config: dict

@router.post("/ingest/{identifier}")
async def ingest(
    identifier: str,
    source_config: SourceConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    config = {"impute_method": "mean", "outlier_threshold": 2.0}
    background_tasks.add_task(data_ingestion.ingest_data, db, identifier, source_config.dict(), config)
    return {"message": f"Data ingestion started for {identifier}"}

@router.post("/upload-csv/{identifier}")
async def upload_csv(
    identifier: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    config = {"impute_method": "mean", "outlier_threshold": 2.0}
    result = await data_ingestion.ingest_data(db, identifier, {"type": "csv", "config": {"data": df.to_dict(orient="records")}}, config)
    return result

@router.get("/monitor/{identifier}")
def monitor(identifier: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return kpi_monitoring.monitor_kpis(db, identifier)

@router.get("/predict/{identifier}")
def predict(identifier: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return prediction.predict_kpis(db, identifier)