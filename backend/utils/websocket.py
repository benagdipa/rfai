from fastapi import WebSocket, WebSocketDisconnect
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

ws_manager = WebSocketManager()
