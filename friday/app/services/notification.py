# app/services/notification.py
import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from datetime import datetime

from starlette.websockets import WebSocketState

# Configure logging
logger = logging.getLogger("friday.notification")


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting
    """

    def __init__(self):
        # Dictionary to store active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Dictionary to track client subscriptions: topic -> set of client_ids
        self.subscriptions: Dict[str, Set[str]] = {}
        # Connection heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        # Track connection state (to prevent using closed connections)
        self.connection_state: Dict[str, bool] = {}  # True = connected, False = disconnected
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Register a new WebSocket connection
        Note: The connection should already be accepted by the route handler
        """
        async with self.lock:
            # If client already connected, close the old connection
            if client_id in self.active_connections:
                try:
                    logger.info(f"Client {client_id} reconnected, closing old connection")
                    self.connection_state[client_id] = False  # Mark old connection as disconnected
                    await self.active_connections[client_id].close(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Connection superseded by newer connection"
                    )
                except Exception as e:
                    logger.warning(f"Error closing existing connection for {client_id}: {e}")

            # Register the new connection
            self.active_connections[client_id] = websocket
            self.last_heartbeat[client_id] = datetime.now()
            self.connection_state[client_id] = True  # Mark as connected

            # Send welcome message
            success = await self._send_personal_message(
                {"type": "connection", "status": "connected", "client_id": client_id},
                client_id
            )

            if success:
                logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
            else:
                logger.warning(f"Client {client_id} connected but failed to send welcome message")

    async def disconnect(self, client_id: str, code: int = status.WS_1000_NORMAL_CLOSURE) -> None:
        """
        Remove a client connection and clean up subscriptions
        """
        async with self.lock:
            if client_id in self.active_connections:
                # Mark as disconnected first to prevent further message sending
                self.connection_state[client_id] = False

                try:
                    # Check if the WebSocket is still open before trying to close it
                    websocket = self.active_connections[client_id]
                    if hasattr(websocket, 'client_state') and websocket.client_state != WebSocketState.DISCONNECTED:
                        await websocket.close(code=code)
                except RuntimeError as e:
                    if "already completed" in str(e) or "Unexpected ASGI message" in str(e):
                        logger.debug(f"WebSocket for {client_id} was already closed")
                    else:
                        logger.warning(f"Error during disconnect for {client_id}: {e}")
                except Exception as e:
                    logger.warning(f"Error during disconnect for {client_id}: {e}")

                # Rest of the cleanup code...

                # Clean up
                del self.active_connections[client_id]
                if client_id in self.last_heartbeat:
                    del self.last_heartbeat[client_id]
                if client_id in self.connection_state:
                    del self.connection_state[client_id]

                # Clean up subscriptions
                for topic in list(self.subscriptions.keys()):
                    if client_id in self.subscriptions[topic]:
                        self.subscriptions[topic].remove(client_id)
                        if not self.subscriptions[topic]:  # If no more subscribers
                            del self.subscriptions[topic]

                logger.info(f"Client {client_id} disconnected. Remaining connections: {len(self.active_connections)}")

    async def is_connected(self, client_id: str) -> bool:
        """
        Check if a client is connected
        """
        return client_id in self.active_connections and self.connection_state.get(client_id, False)

    async def subscribe(self, client_id: str, topic: str) -> bool:
        """
        Subscribe a client to a topic
        """
        if not await self.is_connected(client_id):
            logger.warning(f"Cannot subscribe {client_id} to {topic}: Not connected")
            return False

        async with self.lock:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()

            self.subscriptions[topic].add(client_id)

            # Notify client of successful subscription
            success = await self._send_personal_message(
                {"type": "subscription", "topic": topic, "status": "subscribed"},
                client_id
            )

            if success:
                logger.info(f"Client {client_id} subscribed to {topic}")
            else:
                logger.warning(f"Failed to confirm subscription for {client_id} to {topic}")

                # Remove the subscription if we couldn't confirm it
                self.subscriptions[topic].remove(client_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
                return False

            return success

    async def unsubscribe(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe a client from a topic
        """
        if not await self.is_connected(client_id):
            logger.warning(f"Cannot unsubscribe {client_id} from {topic}: Not connected")
            return False

        async with self.lock:
            if topic in self.subscriptions and client_id in self.subscriptions[topic]:
                self.subscriptions[topic].remove(client_id)

                # Clean up empty topics
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]

                # Notify client of successful unsubscription
                success = await self._send_personal_message(
                    {"type": "subscription", "topic": topic, "status": "unsubscribed"},
                    client_id
                )

                if success:
                    logger.info(f"Client {client_id} unsubscribed from {topic}")
                else:
                    logger.warning(f"Failed to confirm unsubscription for {client_id} from {topic}")

                return success

            return False

    async def broadcast(self, message: dict, topic: Optional[str] = None) -> int:
        """
        Broadcast a message to all clients subscribed to a topic
        If topic is None, broadcast to all connected clients
        Returns the number of clients the message was sent to
        """
        sent_count = 0

        if topic is not None and topic not in self.subscriptions:
            return 0

        # Prepare the message
        if isinstance(message, dict):
            message_str = json.dumps(message)
        else:
            message_str = str(message)

        disconnected_clients = []

        async with self.lock:
            targets = self.subscriptions.get(topic, set(self.active_connections.keys())) if topic else set(
                self.active_connections.keys())

            # Send the message to each target client
            for client_id in list(targets):
                if not await self.is_connected(client_id):
                    # Skip clients that are no longer connected
                    disconnected_clients.append(client_id)
                    continue

                try:
                    await self.active_connections[client_id].send_text(message_str)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending message to {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up any disconnected clients (outside of the lock)
        for client_id in disconnected_clients:
            asyncio.create_task(self.disconnect(client_id, code=status.WS_1011_INTERNAL_ERROR))

        return sent_count

    async def _send_personal_message(self, message: dict, client_id: str) -> bool:
        """
        Send a message to a specific client
        """
        if not await self.is_connected(client_id):
            logger.warning(f"Cannot send message to {client_id}: Not connected")
            return False

        try:
            if isinstance(message, dict):
                await self.active_connections[client_id].send_text(json.dumps(message))
            else:
                await self.active_connections[client_id].send_text(str(message))
            return True
        except Exception as e:
            logger.error(f"Error sending personal message to {client_id}: {e}")
            # Mark as disconnected and schedule cleanup
            self.connection_state[client_id] = False
            asyncio.create_task(self.disconnect(client_id, code=status.WS_1011_INTERNAL_ERROR))
            return False

    async def update_heartbeat(self, client_id: str) -> None:
        """
        Update the last heartbeat time for a client
        """
        if await self.is_connected(client_id):
            self.last_heartbeat[client_id] = datetime.now()

    async def check_heartbeats(self, heartbeat_timeout: int = 60) -> None:
        """
        Check heartbeats and disconnect stale clients
        """
        current_time = datetime.now()
        clients_to_disconnect = []

        async with self.lock:
            for client_id, last_time in list(self.last_heartbeat.items()):
                if not await self.is_connected(client_id):
                    # Skip clients that are already disconnected
                    continue

                time_diff = (current_time - last_time).total_seconds()
                if time_diff > heartbeat_timeout:
                    clients_to_disconnect.append(client_id)

        # Disconnect stale clients outside the lock
        for client_id in clients_to_disconnect:
            logger.warning(f"Client {client_id} timed out (no heartbeat for {heartbeat_timeout}s)")
            await self.disconnect(client_id, code=status.WS_1001_GOING_AWAY)

    async def monitor_connections(self, heartbeat_timeout: int = 60) -> None:
        """
        Periodic task to check for stale connections and clean them up
        """
        while True:
            try:
                await self.check_heartbeats(heartbeat_timeout)
                await asyncio.sleep(15)  # Check every 15 seconds
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(15)  # Continue monitoring despite errors


class NotificationManager:
    """
    Service for handling notifications through WebSockets
    """

    def __init__(self):
        self.connection_manager = ConnectionManager()
        # Start the background tasks
        self.background_tasks = []

    async def start_background_tasks(self):
        """
        Start background tasks for the notification service
        """
        # Monitor connections for heartbeat timeouts
        monitor_task = asyncio.create_task(
            self.connection_manager.monitor_connections(heartbeat_timeout=60)
        )
        self.background_tasks.append(monitor_task)

        logger.info("Started notification service background tasks")

    async def stop_background_tasks(self):
        """
        Stop all background tasks
        """
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.background_tasks.clear()
        logger.info("Stopped notification service background tasks")

    async def handle_websocket(self, websocket: WebSocket, client_id: str) -> None:
        """
        Handle a WebSocket connection for a specific client
        The connection should already be accepted by the route handler
        """
        try:
            # Register the connection (don't try to accept it again)
            await self.connection_manager.connect(websocket, client_id)

            while True:
                try:
                    # Wait for messages from the client
                    data = await websocket.receive_text()
                    logger.debug(f"Received message from {client_id}: {data[:100]}...")

                    # Check if still connected before processing message
                    if not await self.connection_manager.is_connected(client_id):
                        logger.warning(f"Received message from disconnected client {client_id}, ignoring")
                        break

                    message = json.loads(data)

                    # Handle different message types
                    if message.get("type") == "heartbeat":
                        await self.connection_manager.update_heartbeat(client_id)
                        await self.connection_manager._send_personal_message(
                            {"type": "heartbeat", "status": "acknowledged"},
                            client_id
                        )

                    elif message.get("type") == "subscribe":
                        topic = message.get("topic")
                        if topic:
                            await self.connection_manager.subscribe(client_id, topic)

                    elif message.get("type") == "unsubscribe":
                        topic = message.get("topic")
                        if topic:
                            await self.connection_manager.unsubscribe(client_id, topic)

                    # Handle any custom message types
                    else:
                        # Echo back as a simple response
                        await self.connection_manager._send_personal_message(
                            {"type": "echo", "data": message},
                            client_id
                        )

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected during receive: {client_id}")
                    break

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {client_id}: {e}")
                    if await self.connection_manager.is_connected(client_id):
                        await self.connection_manager._send_personal_message(
                            {"type": "error", "message": "Invalid JSON payload"},
                            client_id
                        )

                except Exception as e:
                    logger.error(f"Error processing message from {client_id}: {e}")
                    if await self.connection_manager.is_connected(client_id):
                        await self.connection_manager._send_personal_message(
                            {"type": "error", "message": "Error processing message"},
                            client_id
                        )

        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected normally")

        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")

        finally:
            # Ensure the client is properly disconnected
            await self.connection_manager.disconnect(client_id)

    async def publish_notification(self, message: dict, topic: Optional[str] = None) -> int:
        """
        Publish a notification to clients
        This is the main interface for other services to send notifications
        """
        try:
            # Add timestamp to the message
            message["timestamp"] = datetime.now().isoformat()

            # Broadcast the message
            sent_count = await self.connection_manager.broadcast(message, topic)

            if sent_count > 0:
                logger.info(f"Published notification to {sent_count} clients" +
                            (f" on topic {topic}" if topic else ""))

            return sent_count
        except Exception as e:
            logger.error(f"Error publishing notification: {e}")
            return 0


# Create a global instance of the notification manager
notification_manager = NotificationManager()


# Convenience function for other modules to send notifications
async def send_notification(message: dict, topic: Optional[str] = None) -> int:
    """
    Public function to send a notification to WebSocket clients

    Args:
        message: The notification message (dictionary)
        topic: Optional topic to target specific subscribers

    Returns:
        Number of clients the notification was sent to
    """
    return await notification_manager.publish_notification(message, topic)