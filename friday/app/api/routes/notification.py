# app/api/routes/notification.py
import uuid
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional
import logging

from app.services.notification import notification_manager, send_notification

router = APIRouter(tags=["notifications"])
logger = logging.getLogger("friday.notification.routes")


@router.websocket("/notifications/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint without explicit client_id
    Generates a random client_id and redirects to the main handler
    """
    # Generate a unique client_id
    client_id = str(uuid.uuid4())

    # Log more details about the connection
    client_host = websocket.client.host if hasattr(websocket, 'client') else 'unknown'
    headers = dict(websocket.headers) if hasattr(websocket, 'headers') else {}
    user_agent = headers.get('user-agent', 'unknown')

    logger.info(f"New WebSocket connection request from {client_host} with User-Agent: {user_agent}")
    logger.info(f"Generated client_id: {client_id}")

    # Accept the connection
    await websocket.accept()

    # Handle the connection
    await notification_manager.handle_websocket(websocket, client_id)


@router.websocket("/notifications/ws/{client_id}")
async def websocket_endpoint_with_client_id(websocket: WebSocket, client_id: str):
    """
    Main WebSocket handler that processes incoming connections
    and messages for a specific client_id
    """
    logger.info(f"New WebSocket connection with provided ID: {client_id}")

    # Accept the connection here first
    await websocket.accept()

    # Now handle the connection
    try:
        await notification_manager.handle_websocket(websocket, client_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")


# HTTP endpoints to interact with the notification system
@router.post("/api/notifications", status_code=201,
             description="Send a notification to WebSocket clients")
async def send_notification_endpoint(
        message: dict,
        topic: Optional[str] = Query(None, description="Topic to publish to, or broadcast if None")
):
    """
    Send a notification to clients via WebSocket
    Can target a specific topic or broadcast to all connected clients
    """
    sent_count = await send_notification(message, topic)
    return {"status": "published", "recipients": sent_count}