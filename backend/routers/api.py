from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from utils.database import get_db
from utils.security import oauth2_scheme
from agents import (
    data_ingestion,
    kpi_monitoring,
    prediction,
    schema_learning,
    issue_detection,
    root_cause_analysis,
    optimization_proposal
)
from pydantic import BaseModel
import pandas as pd
import io
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["Data Operations"])

# Pydantic models for request validation
class SourceConfig(BaseModel):
    type: str
    config: Dict[str, Any]

class PredictionConfig(BaseModel):
    lookback: Optional[int] = 10
    forecast_steps: Optional[int] = 5

class OptimizationRequest(BaseModel):
    causes: Optional[list] = None
    predictions: Optional[Dict[str, list]] = None
    kpis: Optional[Dict[str, Dict[str, float]]] = None

# Dependency to handle agent ID injection (optional customization via header)
async def get_agent_id(token: str = Depends(oauth2_scheme)) -> str:
    return "api_agent_1"  # Could be derived from token or config

@router.post("/ingest/{identifier}")
async def ingest(
    identifier: str,
    source_config: SourceConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Ingest data from a specified source in the background.

    Args:
        identifier (str): Unique identifier for the data.
        source_config (SourceConfig): Configuration for the data source.
        background_tasks (BackgroundTasks): FastAPI background task manager.
        db (Session): Database session.
        agent_id (str): Identifier for the ingestion agent.

    Returns:
        dict: Confirmation message indicating ingestion has started.

    Raises:
        HTTPException: If ingestion setup encounters an error.
    """
    config = {"impute_method": "mean", "outlier_threshold": 2.0}
    background_tasks.add_task(
        data_ingestion.ingest_data,
        db,
        identifier,
        source_config.dict(),
        config,
        agent_id=agent_id,
        target_agent="eda_agent_1"
    )
    return {"message": f"Data ingestion started for {identifier} by agent {agent_id}"}

@router.post("/upload-csv/{identifier}")
async def upload_csv(
    identifier: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Upload and process a CSV file for immediate data ingestion.

    Args:
        identifier (str): Unique identifier for the data.
        file (UploadFile): The uploaded CSV file.
        db (Session): Database session.
        agent_id (str): Identifier for the ingestion agent.

    Returns:
        dict: Result of the data ingestion process.

    Raises:
        HTTPException: If the file is not a CSV or ingestion fails.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        # Read and parse the CSV file
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        source_config = {
            "type": "csv",
            "config": {"data": df.to_dict(orient="records")}
        }
        config = {"impute_method": "mean", "outlier_threshold": 2.0}

        # Trigger data ingestion synchronously
        result = await data_ingestion.ingest_data(
            db,
            identifier,
            source_config,
            config,
            agent_id=agent_id,
            target_agent="eda_agent_1"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV ingestion failed: {str(e)}")

@router.get("/schema/{identifier}")
async def get_schema(
    identifier: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve the learned schema for the specified identifier.

    Args:
        identifier (str): Unique identifier for the data.
        db (Session): Database session.
        agent_id (str): Identifier for the schema learning agent.

    Returns:
        dict: Learned schema and metadata.
    """
    # Use empty raw_data to fetch cached/historical schema
    result = await schema_learning.learn_schema(db, identifier, [], agent_id=agent_id, source_agent=agent_id)
    return result

@router.get("/monitor/{identifier}")
async def monitor(
    identifier: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve KPI monitoring data for the specified identifier.

    Args:
        identifier (str): Unique identifier for the data.
        db (Session): Database session.
        agent_id (str): Identifier for the KPI monitoring agent.

    Returns:
        dict: Monitoring results including anomalies detected.
    """
    result = await kpi_monitoring.monitor_kpis(db, identifier, agent_id=agent_id, source_agent=agent_id)
    return result

@router.get("/issues/{identifier}")
async def detect_issues(
    identifier: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve issue detection results for the specified identifier.

    Args:
        identifier (str): Unique identifier for the data.
        db (Session): Database session.
        agent_id (str): Identifier for the issue detection agent.

    Returns:
        dict: Detected issues and metadata.
    """
    result = await issue_detection.detect_issues(db, identifier, agent_id=agent_id, source_agent=agent_id)
    return result

@router.get("/root-cause/{identifier}")
async def analyze_root_cause(
    identifier: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve root cause analysis for the specified identifier.

    Args:
        identifier (str): Unique identifier for the data.
        db (Session): Database session.
        agent_id (str): Identifier for the root cause analysis agent.

    Returns:
        dict: Root cause analysis results.
    """
    result = await root_cause_analysis.analyze_root_cause(db, identifier, agent_id=agent_id, source_agent=agent_id)
    return result

@router.post("/predict/{identifier}")
async def predict(
    identifier: str,
    pred_config: PredictionConfig = Depends(),
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve predictive analytics for the specified identifier with configurable parameters.

    Args:
        identifier (str): Unique identifier for the data.
        pred_config (PredictionConfig): Configuration for prediction (lookback, forecast steps).
        db (Session): Database session.
        agent_id (str): Identifier for the prediction agent.

    Returns:
        dict: Prediction results.
    """
    config = pred_config.dict(exclude_unset=True)
    result = await prediction.predict_kpis(db, identifier, config, agent_id=agent_id, source_agent=agent_id)
    return result

@router.post("/optimize/{identifier}")
async def propose_optimization(
    identifier: str,
    request: OptimizationRequest,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Propose optimizations for the specified identifier based on provided inputs.

    Args:
        identifier (str): Unique identifier for the data.
        request (OptimizationRequest): Optional causes, predictions, and KPIs.
        db (Session): Database session.
        agent_id (str): Identifier for the optimization proposal agent.

    Returns:
        dict: Optimization proposals and metadata.
    """
    result = await optimization_proposal.propose_optimization(
        identifier,
        causes=request.causes,
        predictions=request.predictions,
        kpis=request.kpis,
        agent_id=agent_id,
        source_agent=agent_id
    )
    return result

@router.get("/status/{identifier}")
async def get_status(
    identifier: str,
    db: Session = Depends(get_db),
    agent_id: str = Depends(get_agent_id)
):
    """
    Retrieve a comprehensive status report for the specified identifier.

    Args:
        identifier (str): Unique identifier for the data.
        db (Session): Database session.
        agent_id (str): Identifier for the API agent.

    Returns:
        dict: Combined results from schema, monitoring, issues, predictions, root cause, and optimization.
    """
    try:
        schema = await schema_learning.learn_schema(db, identifier, [], agent_id=agent_id, source_agent=agent_id)
        monitoring = await kpi_monitoring.monitor_kpis(db, identifier, agent_id=agent_id, source_agent=agent_id)
        issues = await issue_detection.detect_issues(db, identifier, agent_id=agent_id, source_agent=agent_id)
        predictions = await prediction.predict_kpis(db, identifier, agent_id=agent_id, source_agent=agent_id)
        root_cause = await root_cause_analysis.analyze_root_cause(db, identifier, agent_id=agent_id, source_agent=agent_id)
        optimization = await optimization_proposal.propose_optimization(
            identifier,
            causes=root_cause.get("causes", []),
            predictions=predictions.get("predictions", {}),
            kpis=monitoring.get("kpis", {}),
            agent_id=agent_id,
            source_agent=agent_id
        )

        return {
            "identifier": identifier,
            "schema": schema,
            "monitoring": monitoring,
            "issues": issues,
            "predictions": predictions,
            "root_cause": root_cause,
            "optimization": optimization,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")