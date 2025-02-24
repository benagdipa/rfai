#!/bin/bash

# Set up base directories
mkdir -p backend/{agents,models,utils,routers,tasks,config}
mkdir -p frontend/{pages,components,lib,store,styles,public}

# Function to create a file with content
create_file() {
    local file_path=$1
    local content=$2
    echo "$content" > "$file_path"
    chmod 644 "$file_path"
    echo "Created $file_path"
}

# Backend files

# main.py
create_file "backend/main.py" $'from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from utils.database import get_db, Base, engine
from utils.websocket import ws_manager
from routers import auth, api
from config.settings import settings
from utils.logger import logger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(api.router)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Application started")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        await ws_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")
        raise HTTPException(status_code=500, detail="WebSocket error")'

# agents/__init__.py
create_file "backend/agents/__init__.py" ""

# agents/data_ingestion.py
create_file "backend/agents/data_ingestion.py" $'from sqlalchemy.orm import Session
from agents.eda_preprocessing import preprocess_data
from utils.connectors import get_connector
from utils.logger import logger
from fastapi import HTTPException

async def ingest_data(db: Session, identifier: str, source_config: dict, config: dict):
    logger.info(f"Starting data ingestion for {identifier}")
    connector = get_connector(source_config["type"])
    if not connector:
        logger.error(f"Invalid source type: {source_config[\'type\']}")
        raise HTTPException(status_code=400, detail="Invalid source type")
    
    try:
        raw_data = await connector.fetch_data(source_config["config"])
        result = await preprocess_data(db, raw_data.to_dict(orient="records"), identifier, config)
        logger.info(f"Data ingestion completed for {identifier}")
        return result
    except Exception as e:
        logger.error(f"Data ingestion failed for {identifier}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")'

# agents/schema_learning.py
create_file "backend/agents/schema_learning.py" $'from sqlalchemy.orm import Session
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
    return result'

# agents/eda_preprocessing.py
create_file "backend/agents/eda_preprocessing.py" $'from sqlalchemy.orm import Session
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
    df[\'cluster\'] = clusters

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
                timestamp=pd.to_datetime(row[timestamp_col], errors=\'coerce\') or pd.Timestamp.now(),
                identifier=identifier,
                data=row.to_dict()
            )
            db.add(data_entry)
        db.commit()
    return result'

# agents/kpi_monitoring.py
create_file "backend/agents/kpi_monitoring.py" $'from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.logger import logger
import pandas as pd

def monitor_kpis(db: Session, identifier: str) -> dict:
    logger.info(f"Monitoring KPIs for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(100).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        logger.warning(f"No numeric data for {identifier}")
        return {"identifier": identifier, "anomalies_detected": False}

    anomalies = {col: len(df[col].dropna()) > 10 and df[col].std() > df[col].mean() * 0.5 for col in numeric_cols}
    return {"identifier": identifier, "anomalies_detected": any(anomalies.values())}'

# agents/issue_detection.py
create_file "backend/agents/issue_detection.py" $'from sqlalchemy.orm import Session
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
    
    return {"identifier": identifier, "issues": issues}'

# agents/prediction.py
create_file "backend/agents/prediction.py" $'from sqlalchemy.orm import Session
from models.dynamic_data import DynamicData
from utils.ml import train_lstm_model, predict_with_lstm
from utils.logger import logger
import pandas as pd
import numpy as np

def predict_kpis(db: Session, identifier: str) -> dict:
    logger.info(f"Generating predictions for {identifier}")
    data = db.query(DynamicData).filter(DynamicData.identifier == identifier).order_by(DynamicData.timestamp.desc()).limit(100).all()
    df = pd.DataFrame([d.data for d in data])
    
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if not numeric_cols:
        logger.warning(f"No numeric data for prediction in {identifier}")
        return {"identifier": identifier, "predictions": {}}

    predictions = {}
    for col in numeric_cols:
        series = df[col].dropna().values[-50:]
        if len(series) >= 20:  # Minimum data for LSTM
            try:
                model = train_lstm_model(series.reshape(-1, 1))
                pred = predict_with_lstm(model, series[-10:], steps=5)
                predictions[col] = pred.tolist()
            except Exception as e:
                logger.error(f"Prediction failed for {col}: {e}")
                predictions[col] = [0] * 5  # Fallback
        else:
            predictions[col] = [df[col].mean()] * 5  # Fallback for insufficient data
    
    return {"identifier": identifier, "predictions": predictions}'

# agents/root_cause_analysis.py
create_file "backend/agents/root_cause_analysis.py" $'from sqlalchemy.orm import Session
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
    if \'throughput\' in avg_values and \'latency\' in avg_values:
        if avg_values[\'throughput\'] < 10 and avg_values[\'latency\'] > 50:
            return {"identifier": identifier, "cause": "Possible interference or congestion"}
    return {"identifier": identifier, "cause": "Unknown"}'

# agents/optimization_proposal.py
create_file "backend/agents/optimization_proposal.py" $'from utils.logger import logger

def propose_optimization(identifier: str, cause: str) -> dict:
    logger.info(f"Generating optimization proposal for {identifier}")
    if "interference" in cause:
        proposal = "Adjust antenna tilt by 2 degrees or increase power by 3 dBm"
    elif "congestion" in cause:
        proposal = "Reallocate spectrum or offload traffic to adjacent cells"
    else:
        proposal = "Manual investigation required"
    return {"identifier": identifier, "proposal": proposal}'

# models/__init__.py
create_file "backend/models/__init__.py" ""

# models/dynamic_data.py
create_file "backend/models/dynamic_data.py" $'from sqlalchemy import Column, Integer, JSON, String, DateTime
from utils.database import Base

class DynamicData(Base):
    __tablename__ = "dynamic_data"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    identifier = Column(String, index=True)
    data = Column(JSON)'

# models/issue.py
create_file "backend/models/issue.py" $'from sqlalchemy import Column, Integer, String
from utils.database import Base

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True)
    description = Column(String)
    severity = Column(String)'

# models/optimization.py
create_file "backend/models/optimization.py" $'from sqlalchemy import Column, Integer, String
from utils.database import Base

class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True)
    proposal = Column(String)'

# utils/__init__.py
create_file "backend/utils/__init__.py" ""

# utils/database.py
create_file "backend/utils/database.py" $'from sqlalchemy import create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

engine = create_engine(settings.DATABASE_URL, pool_size=20, max_overflow=0)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

Index(\'ix_dynamic_data_identifier_timestamp\', "dynamic_data.identifier", "dynamic_data.timestamp")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()'

# utils/stats.py
create_file "backend/utils/stats.py" $'from sklearn.cluster import DBSCAN
from utils.logger import logger

def detect_clusters(features: list) -> list:
    try:
        clustering = DBSCAN(eps=0.5, min_samples=5).fit(features)
        return clustering.labels_
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return [-1] * len(features)  # Fallback to noise'

# utils/eda.py
create_file "backend/utils/eda.py" $'import pandas as pd
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
        df[f"{col}_trend"] = np.where(df[col].diff() > 0, \'up\', \'down\')
        df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min() + 1e-6)
    return df'

# utils/websocket.py
create_file "backend/utils/websocket.py" $'from fastapi import WebSocket, WebSocketDisconnect
import json
from utils.logger import logger

class WebSocketManager:
    def __init__(self):
        self.connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        logger.info("WebSocket connected")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
            logger.info("WebSocket disconnected")

    async def broadcast(self, message: dict):
        failed = []
        for conn in self.connections:
            try:
                await conn.send_text(json.dumps(message))
            except Exception as e:
                failed.append(conn)
                logger.error(f"WebSocket send failed: {e}")
        for conn in failed:
            await self.disconnect(conn)

ws_manager = WebSocketManager()'

# utils/cache.py
create_file "backend/utils/cache.py" $'import redis
import json
from config.settings import settings
from utils.logger import logger

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def cache_set(key: str, value: dict, ttl: int = 3600):
    try:
        redis_client.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.error(f"Cache set failed for {key}: {e}")

def cache_get(key: str) -> dict:
    try:
        result = redis_client.get(key)
        return json.loads(result) if result else None
    except Exception as e:
        logger.error(f"Cache get failed for {key}: {e}")
        return None'

# utils/security.py
create_file "backend/utils/security.py" $'from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config.settings import settings
from utils.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    try:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        return None

def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except JWTError as e:
        logger.error(f"Token decoding failed: {e}")
        return None'

# utils/logger.py
create_file "backend/utils/logger.py" $'from loguru import logger

logger.add("logs/app.log", rotation="1 week", retention="1 month", level="INFO")'

# utils/ai.py
create_file "backend/utils/ai.py" $'import aiohttp
from config.settings import settings
from utils.logger import logger

async def get_ai_insights(data: dict, prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": f"{prompt}: {data}"}],
            "max_tokens": 200
        }
        try:
            async with session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers) as resp:
                result = await resp.json()
                return result["choices"][0]["message"]["content"] if "choices" in result else "No insights available"
        except Exception as e:
            logger.error(f"AI insights request failed: {e}")
            return "Failed to retrieve AI insights"'

# utils/connectors.py
create_file "backend/utils/connectors.py" $'import pandas as pd
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine
from config.settings import settings
from utils.logger import logger

class DataConnector:
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        raise NotImplementedError

class CsvConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        return pd.read_csv(source_config["file_path"])

class SqlConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        engine = create_engine(source_config["connection_string"])
        return pd.read_sql(source_config["query"], engine)

class GoogleSheetsConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_SHEETS_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(source_config["sheet_id"]).sheet1
        return pd.DataFrame(sheet.get_all_records())

class AirtableConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        url = f"https://api.airtable.com/v0/{source_config[\'base_id\']}/{source_config[\'table_name\']}"
        headers = {"Authorization": f"Bearer {settings.AIRTABLE_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return pd.DataFrame([record["fields"] for record in data["records"]])

class ApiConnector(DataConnector):
    async def fetch_data(self, source_config: dict) -> pd.DataFrame:
        async with aiohttp.ClientSession() as session:
            async with session.get(source_config["url"], params=source_config.get("params", {})) as resp:
                data = await resp.json()
                return pd.json_normalize(data[source_config.get("data_key", "")] if "data_key" in source_config else data)

def get_connector(source_type: str) -> DataConnector:
    connectors = {
        "csv": CsvConnector(),
        "sql": SqlConnector(),
        "google_sheets": GoogleSheetsConnector(),
        "airtable": AirtableConnector(),
        "api": ApiConnector()
    }
    return connectors.get(source_type, None)'

# utils/ml.py
create_file "backend/utils/ml.py" $'import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from utils.logger import logger

def train_lstm_model(data: np.ndarray, look_back: int = 10) -> Sequential:
    X, y = [], []
    for i in range(len(data) - look_back):
        X.append(data[i:i + look_back])
        y.append(data[i + look_back])
    X, y = np.array(X), np.array(y)
    
    model = Sequential()
    model.add(LSTM(50, input_shape=(look_back, 1), return_sequences=True))
    model.add(LSTM(50))
    model.add(Dense(1))
    try:
        model.compile(optimizer=\'adam\', loss=\'mse\')
        model.fit(X, y, epochs=10, batch_size=1, verbose=0)
        return model
    except Exception as e:
        logger.error(f"LSTM training failed: {e}")
        raise

def predict_with_lstm(model: Sequential, data: np.ndarray, steps: int = 5) -> np.ndarray:
    predictions = []
    input_seq = data[-10:].reshape(1, 10, 1)
    try:
        for _ in range(steps):
            pred = model.predict(input_seq, verbose=0)
            predictions.append(pred[0, 0])
            input_seq = np.roll(input_seq, -1, axis=1)
            input_seq[0, -1, 0] = pred[0, 0]
        return np.array(predictions)
    except Exception as e:
        logger.error(f"LSTM prediction failed: {e}")
        return np.zeros(steps)'

# routers/__init__.py
create_file "backend/routers/__init__.py" ""

# routers/auth.py
create_file "backend/routers/auth.py" $'from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from utils.security import create_access_token, decode_token

router = APIRouter()

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "rf_engineer" and form_data.password == "securepass":
        token = create_access_token({"sub": form_data.username})
        if token:
            return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")'

# routers/api.py
create_file "backend/routers/api.py" $'from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from utils.database import get_db
from utils.security import oauth2_scheme
from agents import data_ingestion, kpi_monitoring, prediction
from pydantic import BaseModel

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

@router.get("/monitor/{identifier}")
def monitor(identifier: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return kpi_monitoring.monitor_kpis(db, identifier)

@router.get("/predict/{identifier}")
def predict(identifier: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return prediction.predict_kpis(db, identifier)'

# tasks/__init__.py
create_file "backend/tasks/__init__.py" ""

# tasks/celery_config.py
create_file "backend/tasks/celery_config.py" $'from celery import Celery
from config.settings import settings

celery_app = Celery(
    "network_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["agents.data_ingestion", "agents.eda_preprocessing", "agents.prediction"]
)'

# config/__init__.py
create_file "backend/config/__init__.py" ""

# config/settings.py
create_file "backend/config/settings.py" $'import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost/network_db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "/path/to/credentials.json")
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "your-airtable-key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key")

settings = Settings()'

# requirements.txt
create_file "backend/requirements.txt" $'fastapi==0.68.1
uvicorn==0.15.0
sqlalchemy==1.4.25
psycopg2-binary==2.9.1
pandas==1.3.0
numpy==1.21.0
scikit-learn==0.24.2
tensorflow==2.6.0
aiohttp==3.7.4
redis==4.0.0
celery==5.2.7
python-jose[cryptography]==3.3.0
loguru==0.5.3
gspread==5.4.0
oauth2client==4.1.3'

# .env
create_file "backend/.env" $'DATABASE_URL=postgresql://admin:password@localhost/network_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000
GOOGLE_SHEETS_CREDENTIALS=/path/to/credentials.json
AIRTABLE_API_KEY=your-airtable-key
OPENAI_API_KEY=your-openai-key'

# README.md
create_file "backend/README.md" $'# Network Performance Monitoring App

## Setup

### Backend
1. Install Python 3.9+ and dependencies: `pip install -r requirements.txt`
2. Configure `.env` with your credentials
3. Run Redis: `redis-server`
4. Start Celery: `celery -A tasks.celery_config worker -l info`
5. Run the server: `uvicorn main:app --host 0.0.0.0 --port 8000`'

# Frontend files

# pages/_app.js
create_file "frontend/pages/_app.js" $'import { Provider } from \'react-redux\';
import { ThemeProvider } from \'@mui/material/styles\';
import { store } from \'../store\';
import ErrorBoundary from \'../components/ErrorBoundary\';
import Navbar from \'../components/Navbar\';
import theme from \'../styles/theme\';
import \'../styles/globals.css\';

function MyApp({ Component, pageProps }) {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <ErrorBoundary>
          <Navbar />
          <Component {...pageProps} />
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>
  );
}

export default MyApp;'

# pages/index.js
create_file "frontend/pages/index.js" $'import { useRouter } from \'next/router\';
import { useEffect } from \'react\';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push(\'/dashboard\');
  }, [router]);

  return null;
}'

# pages/dashboard.js
create_file "frontend/pages/dashboard.js" $'import { useEffect, useState } from \'react\';
import { useDispatch, useSelector } from \'react-redux\';
import { fetchKpiData, updateEda } from \'../store/kpiSlice\';
import KpiChart from \'../components/KpiChart\';
import NetworkMap from \'../components/NetworkMap\';
import PredictionChart from \'../components/PredictionChart\';
import DataSourceConfig from \'../components/DataSourceConfig\';
import api from \'../lib/api\';
import { WebSocketClient } from \'../lib/websocket\';
import { Container, Typography, Paper, Grid, Box, CircularProgress } from \'@mui/material\';

export default function Dashboard() {
  const dispatch = useDispatch();
  const { data, eda, status, error } = useSelector(state => state.kpi);
  const [wsClient, setWsClient] = useState(null);
  const identifier = \'CELL001\';

  useEffect(() => {
    dispatch(fetchKpiData(identifier));
    const client = new WebSocketClient(process.env.NEXT_PUBLIC_WS_URL, (message) => {
      dispatch(updateEda(message));
    });
    setWsClient(client);
    return () => client.close();
  }, [dispatch]);

  const handleDataSourceSubmit = async (sourceConfig) => {
    try {
      await api.post(`/ingest/${identifier}`, sourceConfig);
    } catch (err) {
      console.error(\'Ingestion failed:\', err);
    }
  };

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>4G/5G Network Dashboard</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 2 }}>
            <DataSourceConfig onSubmit={handleDataSourceSubmit} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={8}>
          <Paper elevation={3} sx={{ p: 2 }}>
            {status === \'loading\' && <CircularProgress />}
            {error && <Typography color="error">Error: {error}</Typography>}
            {eda ? (
              <Box>
                <Typography variant="h6">Identifier: {eda.identifier}</Typography>
                <Typography>Clusters: {eda.clusters}</Typography>
                <Typography>AI Insights: {eda.ai_insights}</Typography>
                <KpiChart data={eda} />
              </Box>
            ) : (
              <Typography>No EDA data yet</Typography>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper elevation={3} sx={{ p: 2 }}>
            {data?.monitor ? <NetworkMap cells={[data.monitor]} /> : <Typography>No map data</Typography>}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper elevation={3} sx={{ p: 2 }}>
            {data?.predict ? (
              <Box>
                <Typography variant="h6">Predictions</Typography>
                <PredictionChart predictions={data.predict.predictions} />
              </Box>
            ) : (
              <Typography>No predictions yet</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}'

# pages/login.js
create_file "frontend/pages/login.js" $'import { useState } from \'react\';
import { useRouter } from \'next/router\';
import { login } from \'../lib/auth\';
import { TextField, Button, Typography, Box } from \'@mui/material\';

export default function Login() {
  const [username, setUsername] = useState(\'\');
  const [password, setPassword] = useState(\'\');
  const [error, setError] = useState(\'\');
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      router.push(\'/dashboard\');
    } catch (err) {
      setError(\'Invalid credentials\');
    }
  };

  return (
    <Box sx={{ maxWidth: 400, mx: \'auto\', mt: 8, p: 2 }}>
      <Typography variant="h4" gutterBottom>Login</Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          label="Username"
          fullWidth
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          margin="normal"
        />
        <TextField
          label="Password"
          type="password"
          fullWidth
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          margin="normal"
        />
        <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>
          Login
        </Button>
      </form>
      {error && <Typography color="error" sx={{ mt: 2 }}>{error}</Typography>}
    </Box>
  );
}'

# components/KpiChart.js
create_file "frontend/components/KpiChart.js" $'import { Line } from \'react-chartjs-2\';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip } from \'chart.js\';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const KpiChart = ({ data }) => {
  if (!data || !data.summary) return <div>No data available</div>;

  const numericCols = Object.keys(data.summary).filter(key => typeof data.summary[key].mean === \'number\');
  if (!numericCols.length) return <div>No numeric data</div>;

  const chartData = {
    labels: Array(Math.max(...numericCols.map(col => data.summary[col].count))).fill(\'\').map((_, i) => i),
    datasets: numericCols.map(col => ({
      label: col,
      data: Object.values(data.summary[col]),
      borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
    })),
  };

  return (
    <div style={{ height: \'400px\', width: \'100%\' }}>
      <Line data={chartData} options={{ maintainAspectRatio: false }} />
    </div>
  );
};

export default KpiChart;'

# components/NetworkMap.js
create_file "frontend/components/NetworkMap.js" $'import { MapContainer, TileLayer, Marker, Popup } from \'react-leaflet\';
import \'leaflet/dist/leaflet.css\';

const NetworkMap = ({ cells }) => {
  if (!cells || !cells.length) return <div>No map data</div>;

  return (
    <MapContainer center={[51.505, -0.09]} zoom={13} style={{ height: \'400px\', width: \'100%\' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {cells.map(cell => (
        <Marker key={cell.identifier} position={[cell.lat || 51.505, cell.lon || -0.09]}>
          <Popup>{cell.identifier} - Anomalies: {cell.anomalies_detected ? \'Yes\' : \'No\'}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default NetworkMap;'

# components/PredictionChart.js
create_file "frontend/components/PredictionChart.js" $'import { Line } from \'react-chartjs-2\';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip } from \'chart.js\';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const PredictionChart = ({ predictions }) => {
  if (!predictions || Object.keys(predictions).length === 0) return <div>No predictions available</div>;

  const datasets = Object.entries(predictions).map(([key, values]) => ({
    label: `${key} (Predicted)`,
    data: values,
    borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
    borderDash: [5, 5],
  }));

  const chartData = {
    labels: Array(datasets[0].data.length).fill(\'\').map((_, i) => `T+${i+1}`),
    datasets,
  };

  return (
    <div style={{ height: \'400px\', width: \'100%\' }}>
      <Line data={chartData} options={{ maintainAspectRatio: false }} />
    </div>
  );
};

export default PredictionChart;'

# components/DataSourceConfig.js
create_file "frontend/components/DataSourceConfig.js" $'import { useState } from \'react\';
import { TextField, Button, Select, MenuItem, FormControl, InputLabel, Box } from \'@mui/material\';

export default function DataSourceConfig({ onSubmit }) {
  const [sourceType, setSourceType] = useState(\'csv\');
  const [config, setConfig] = useState({});

  const handleConfigChange = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = () => {
    onSubmit({ type: sourceType, config });
  };

  return (
    <Box sx={{ p: 2, bgcolor: \'#f5f5f5\', borderRadius: 2 }}>
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Data Source Type</InputLabel>
        <Select value={sourceType} onChange={e => setSourceType(e.target.value)}>
          <MenuItem value="csv">CSV File</MenuItem>
          <MenuItem value="sql">SQL Database</MenuItem>
          <MenuItem value="google_sheets">Google Sheets</MenuItem>
          <MenuItem value="airtable">Airtable</MenuItem>
          <MenuItem value="api">API</MenuItem>
        </Select>
      </FormControl>
      {sourceType === \'csv\' && (
        <TextField
          label="File Path"
          fullWidth
          onChange={e => handleConfigChange(\'file_path\', e.target.value)}
          sx={{ mb: 2 }}
        />
      )}
      {sourceType === \'sql\' && (
        <>
          <TextField
            label="Connection String"
            fullWidth
            onChange={e => handleConfigChange(\'connection_string\', e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Query"
            fullWidth
            onChange={e => handleConfigChange(\'query\', e.target.value)}
            sx={{ mb: 2 }}
          />
        </>
      )}
      {sourceType === \'google_sheets\' && (
        <TextField
          label="Sheet ID"
          fullWidth
          onChange={e => handleConfigChange(\'sheet_id\', e.target.value)}
          sx={{ mb: 2 }}
        />
      )}
      {sourceType === \'airtable\' && (
        <>
          <TextField
            label="Base ID"
            fullWidth
            onChange={e => handleConfigChange(\'base_id\', e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Table Name"
            fullWidth
            onChange={e => handleConfigChange(\'table_name\', e.target.value)}
            sx={{ mb: 2 }}
          />
        </>
      )}
      {sourceType === \'api\' && (
        <>
          <TextField
            label="URL"
            fullWidth
            onChange={e => handleConfigChange(\'url\', e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Data Key (optional)"
            fullWidth
            onChange={e => handleConfigChange(\'data_key\', e.target.value)}
            sx={{ mb: 2 }}
          />
        </>
      )}
      <Button variant="contained" onClick={handleSubmit}>Connect</Button>
    </Box>
  );
}'

# components/ErrorBoundary.js
create_file "frontend/components/ErrorBoundary.js" $'import React from \'react\';
import { Typography } from \'@mui/material\';

class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error(\'Error:\', error, info);
  }

  render() {
    if (this.state.hasError) return <Typography>Something went wrong.</Typography>;
    return this.props.children;
  }
}

export default ErrorBoundary;'

# components/Navbar.js
create_file "frontend/components/Navbar.js" $'import { AppBar, Toolbar, Typography, Button } from \'@mui/material\';
import { logout } from \'../lib/auth\';

export default function Navbar() {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Network Dashboard
        </Typography>
        <Button color="inherit" onClick={logout}>Logout</Button>
      </Toolbar>
    </AppBar>
  );
}'

# lib/api.js
create_file "frontend/lib/api.js" $'import axios from \'axios\';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(\'token\');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;'

# lib/auth.js
create_file "frontend/lib/auth.js" $'import api from \'./api\';

export async function login(username, password) {
  const response = await api.post(\'/auth/token\', { username, password });
  localStorage.setItem(\'token\', response.data.access_token);
}

export function logout() {
  localStorage.removeItem(\'token\');
  window.location.href = \'/login\';
}'

# lib/websocket.js
create_file "frontend/lib/websocket.js" $'export class WebSocketClient {
  constructor(url, onMessage) {
    this.url = url;
    this.onMessage = onMessage;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (event) => this.onMessage(JSON.parse(event.data));
    this.ws.onclose = () => this.reconnect();
    this.ws.onerror = (error) => console.error(\'WebSocket error:\', error);
  }

  reconnect() {
    setTimeout(() => this.connect(), 1000);
  }

  close() {
    this.ws.close();
  }
}'

# store/index.js
create_file "frontend/store/index.js" $'import { configureStore } from \'@reduxjs/toolkit\';
import kpiReducer from \'./kpiSlice\';

export const store = configureStore({
  reducer: {
    kpi: kpiReducer,
  },
});'

# store/kpiSlice.js
create_file "frontend/store/kpiSlice.js" $'import { createSlice, createAsyncThunk } from \'@reduxjs/toolkit\';
import api from \'../lib/api\';

export const fetchKpiData = createAsyncThunk(\'kpi/fetch\', async (identifier) => {
  const monitor = await api.get(`/monitor/${identifier}`);
  const predict = await api.get(`/predict/${identifier}`);
  return { monitor, predict };
});

const kpiSlice = createSlice({
  name: \'kpi\',
  initialState: { data: null, eda: null, status: \'idle\', error: null },
  reducers: {
    updateEda(state, action) {
      state.eda = action.payload;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKpiData.pending, (state) => { state.status = \'loading\'; })
      .addCase(fetchKpiData.fulfilled, (state, action) => {
        state.status = \'succeeded\';
        state.data = action.payload;
      })
      .addCase(fetchKpiData.rejected, (state, action) => {
        state.status = \'failed\';
        state.error = action.error.message;
      });
  },
});

export const { updateEda } = kpiSlice.actions;
export default kpiSlice.reducer;'

# styles/globals.css
create_file "frontend/styles/globals.css" $'body {
  margin: 0;
  padding: 0;
  font-family: \'Roboto\', sans-serif;
  background-color: #f0f2f5;
}'

# styles/theme.js
create_file "frontend/styles/theme.js" $'import { createTheme } from \'@mui/material/styles\';

const theme = createTheme({
  palette: {
    primary: { main: \'#1976d2\' },
    secondary: { main: \'#dc004e\' },
  },
  typography: {
    fontFamily: \'Roboto, sans-serif\',
  },
});

export default theme;'

# public/favicon.ico
touch frontend/public/favicon.ico
chmod 644 frontend/public/favicon.ico
echo "Created frontend/public/favicon.ico (placeholder, replace with actual file)"

# .env.local
create_file "frontend/.env.local" $'NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws'

# package.json
create_file "frontend/package.json" $'{
  "name": "frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "@mui/material": "^5.10.0",
    "@emotion/react": "^11.10.0",
    "@emotion/styled": "^11.10.0",
    "@reduxjs/toolkit": "^1.6.2",
    "axios": "^0.24.0",
    "chart.js": "^3.6.0",
    "next": "12.0.0",
    "react": "17.0.2",
    "react-chartjs-2": "^4.0.0",
    "react-dom": "17.0.2",
    "react-redux": "^7.2.6",
    "react-leaflet": "^4.0.0",
    "leaflet": "^1.7.1"
  }
}'

# next.config.js
create_file "frontend/next.config.js" $'module.exports = {
  reactStrictMode: true,
};'

# README.md
create_file "frontend/README.md" $'# Network Dashboard Frontend

## Setup
#1. Install Node.js 16+
#2. Install dependencies: `npm install`
#3. Configure `.env.local` with API and WebSocket URLs
#4. Build and run: `npm run build && npm start`'

# Make the script executable
chmod +x setup_app.sh

echo "Setup complete! Run 'bash setup_app.sh' to create the app structure."
