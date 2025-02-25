from fastapi import WebSocket, WebSocketDisconnect
import json
from utils.logger import logger
from typing import Dict, Any, List, Optional
import asyncio
from collections import defaultdict
from async_timeout import timeout

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[int, WebSocket] = {}  # Keyed by connection ID
        self._lock = asyncio.Lock()  # For thread-safe operations
        self._message_queue: List[Dict[str, Any]] = []  # Queue for pending messages
        self._running = True

    async def connect(self, websocket: WebSocket) -> int:
        """
        Accept a new WebSocket connection and assign a unique ID.

        Args:
            websocket (WebSocket): The WebSocket connection.

        Returns:
            int: Unique connection ID.
        """
        await websocket.accept()
        conn_id = id(websocket)
        async with self._lock:
            self.connections[conn_id] = websocket
        logger.info(f"WebSocket connected: ID={conn_id}, total={len(self.connections)}")
        return conn_id

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket connection.

        Args:
            websocket (WebSocket): The WebSocket connection to remove.
        """
        conn_id = id(websocket)
        async with self._lock:
            if conn_id in self.connections:
                del self.connections[conn_id]
                logger.info(f"WebSocket disconnected: ID={conn_id}, total={len(self.connections)}")

    async def broadcast(self, message: Dict[str, Any], target: Optional[str] = None) -> None:
        """
        Broadcast a message to all or specific WebSocket connections.

        Args:
            message (dict): Message to broadcast (must be JSON-serializable).
            target (str, optional): Target agent ID; if None, broadcast to all.
        """
        if not self._running:
            logger.warning("WebSocketManager is shutting down; message dropped")
            return

        try:
            serialized_message = json.dumps(message)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message: {e}")
            return

        failed_connections = []
        async with self._lock:
            if not self.connections:
                logger.debug("No active WebSocket connections; queuing message")
                self._message_queue.append({"message": message, "target": target})
                return

            for conn_id, conn in list(self.connections.items()):
                # Check if message is targeted and matches connection context (e.g., agent_id)
                should_send = target is None or (
                    "target_agent" in message and message["target_agent"] == target
                )
                if should_send:
                    try:
                        async with timeout(5):  # 5-second timeout for sending
                            await conn.send_text(serialized_message)
                        logger.debug(f"Message sent to WebSocket ID={conn_id}")
                    except (RuntimeError, asyncio.TimeoutError) as e:
                        logger.error(f"WebSocket send failed for ID={conn_id}: {e}")
                        failed_connections.append(conn_id)
                    except Exception as e:
                        logger.error(f"Unexpected error sending to WebSocket ID={conn_id}: {e}")
                        failed_connections.append(conn_id)

        # Clean up failed connections
        for conn_id in failed_connections:
            await self.disconnect(self.connections.get(conn_id))

        # Process queued messages if connections are available
        if self.connections and self._message_queue:
            async with self._lock:
                queued = self._message_queue[:]
                self._message_queue.clear()
            for queued_msg in queued:
                await self.broadcast(queued_msg["message"], queued_msg["target"])

    async def send_to(self, conn_id: int, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            conn_id (int): Connection ID to target.
            message (dict): Message to send.

        Returns:
            bool: True if successful, False otherwise.
        """
        async with self._lock:
            conn = self.connections.get(conn_id)
            if not conn:
                logger.warning(f"No WebSocket found for ID={conn_id}")
                return False
        
        try:
            serialized_message = json.dumps(message)
            async with timeout(5):
                await conn.send_text(serialized_message)
            logger.debug(f"Message sent to WebSocket ID={conn_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to WebSocket ID={conn_id}: {e}")
            await self.disconnect(conn)
            return False

    async def close_all(self) -> None:
        """
        Close all WebSocket connections and stop the manager.
        """
        self._running = False
        async with self._lock:
            for conn_id, conn in list(self.connections.items()):
                try:
                    await conn.close()
                    logger.debug(f"Closed WebSocket ID={conn_id}")
                except Exception as e:
                    logger.error(f"Error closing WebSocket ID={conn_id}: {e}")
                del self.connections[conn_id]
            self._message_queue.clear()
        logger.info("All WebSocket connections closed")

    def get_connection_count(self) -> int:
        """
        Get the current number of active WebSocket connections.

        Returns:
            int: Number of connections.
        """
        return len(self.connections)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the WebSocket manager.

        Returns:
            dict: Health status and details.
        """
        async with self._lock:
            active = len(self.connections)
            queued = len(self._message_queue)
        
        return {
            "status": "healthy" if active > 0 or queued == 0 else "warning",
            "details": {
                "active_connections": active,
                "queued_messages": queued
            }
        }

ws_manager = WebSocketManager()

if __name__ == "__main__":
    # Test the WebSocketManager
    async def test_websocket():
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        client = TestClient(app)
        
        # Mock WebSocket for testing
        class MockWebSocket:
            def __init__(self):
                self.closed = False
            async def accept(self):
                pass
            async def send_text(self, data):
                print(f"Sent: {data}")
            async def close(self):
                self.closed = True
        
        ws = MockWebSocket()
        conn_id = await ws_manager.connect(ws)
        await ws_manager.broadcast({"event": "test", "data": "Hello"})
        await ws_manager.send_to(conn_id, {"event": "direct", "data": "Direct message"})
        print(f"Health: {await ws_manager.health_check()}")
        await ws_manager.disconnect(ws)
        await ws_manager.close_all()

    asyncio.run(test_websocket())