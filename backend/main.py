from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from utils.websocket import ws_manager
from routers import auth, api
from config.settings import load_settings  # Import load_settings function
from utils.logger import logger, configure_logger
from utils.database import init_db, get_db, Base  # Adjusted imports
from starlette.websockets import WebSocketDisconnect
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

# Initialize settings and configure dependencies
settings = load_settings()
configure_logger(
    log_level=settings.LOG_LEVEL,
    log_file="logs/app.log",
    use_json=settings.LOG_JSON,
    environment=settings.ENVIRONMENT,
)
init_db(settings.DATABASE_URL)  # Initialize database with settings

# Global state for agent coordination
agent_status: Dict[str, str] = {
    "ingestion_agent_1": "idle",
    "eda_agent_1": "idle",
    "issue_detection_agent_1": "idle",
    "kpi_monitoring_agent_1": "idle",
    "schema_learning_agent_1": "idle",
    "root_cause_agent_1": "idle",
    "prediction_agent_1": "idle",
    "optimization_agent_1": "idle"
}

# Background task to simulate agent heartbeat
async def agent_heartbeat():
    """Periodically log agent status for monitoring."""
    while True:
        logger.debug(f"Agent status: {agent_status}")
        await asyncio.sleep(60)  # Check every minute

# Lifecycle management with async context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting application lifecycle")
    heartbeat_task = asyncio.create_task(agent_heartbeat())
    logger.info("Application started with agent heartbeat task")

    yield

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        logger.info("Agent heartbeat task cancelled")
    await ws_manager.close_all()
    logger.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(api.router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    client_id = id(websocket)
    logger.info(f"WebSocket client {client_id} connected")
    
    try:
        while True:
            message = await websocket.receive_text()
            data = {"message": message, "client_id": client_id}
            logger.debug(f"WebSocket received: {data}")
            await ws_manager.broadcast({"event": "client_message", "data": data})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        await ws_manager.disconnect(websocket)
        logger.error(f"WebSocket error for client {client_id}: {e}")
        await ws_manager.broadcast({"event": "error", "data": {"message": str(e)}})
        raise HTTPException(status_code=500, detail="WebSocket error")

# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "agents": agent_status,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Trigger agent endpoint
@app.post("/trigger-agent/{agent_id}")
async def trigger_agent(agent_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    if agent_id not in agent_status:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent_status[agent_id] = "triggered"
    event_data = {
        "event_type": f"{agent_id}_trigger",
        "data": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "target_agent": agent_id,
    }
    await ws_manager.broadcast(event_data)
    logger.info(f"Triggered agent {agent_id} with payload: {payload}")
    return {"message": f"Triggered {agent_id} with payload", "payload": payload}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)