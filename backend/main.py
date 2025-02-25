from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from utils.database import get_db, Base, engine
from utils.websocket import ws_manager
from routers import auth, api
from config.settings import settings
from utils.logger import logger
from starlette.websockets import WebSocketDisconnect
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

# Global state for agent coordination (optional)
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
    # Startup tasks
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or verified")
    
    # Start background tasks
    heartbeat_task = asyncio.create_task(agent_heartbeat())
    logger.info("Application started with agent heartbeat task")

    yield  # Application runs here

    # Shutdown tasks
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

# WebSocket endpoint for real-time agent communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication with agents.

    Args:
        websocket (WebSocket): The WebSocket connection.
    """
    await ws_manager.connect(websocket)
    client_id = id(websocket)
    logger.info(f"WebSocket client {client_id} connected")
    
    try:
        while True:
            # Receive messages from clients (e.g., to trigger agent actions)
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
    """
    Check the health of the application and database connection.

    Args:
        db (Session): Database session.

    Returns:
        dict: Health status.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "agents": agent_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Example endpoint to trigger agent actions via WebSocket
@app.post("/trigger-agent/{agent_id}")
async def trigger_agent(
    agent_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Trigger an agent action via WebSocket broadcast.

    Args:
        agent_id (str): Identifier of the target agent.
        payload (dict): Data to send to the agent.
        db (Session): Database session.

    Returns:
        dict: Confirmation of trigger broadcast.
    """
    if agent_id not in agent_status:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    
    agent_status[agent_id] = "triggered"
    event_data = {
        "event_type": f"{agent_id}_trigger",
        "data": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "target_agent": agent_id
    }
    await ws_manager.broadcast(event_data)
    logger.info(f"Triggered agent {agent_id} with payload: {payload}")
    return {"message": f"Triggered {agent_id} with payload", "payload": payload}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)