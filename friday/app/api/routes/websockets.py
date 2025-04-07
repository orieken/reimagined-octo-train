# app/api/websocket_routes.py
import uuid
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional

from app.services.notification_service import notification_service
from app.config import settings

router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint without explicit client_id
    Generates a random client_id and redirects to the main handler
    """
    # Generate a unique client_id
    client_id = str(uuid.uuid4())
    await websocket_endpoint_with_client_id(websocket, client_id)

@router.websocket("/ws/{client_id}")
async def websocket_endpoint_with_client_id(websocket: WebSocket, client_id: str):
    """
    Main WebSocket handler that processes incoming connections
    and messages for a specific client_id
    """
    # Accept the connection
    try:
        # Handle the WebSocket connection through the notification service
        await notification_service.handle_websocket(websocket, client_id)
    except WebSocketDisconnect:
        # This is handled in the notification service
        pass
    except Exception as e:
        # Log the error (already handled in notification service)
        pass

# HTTP endpoints to interact with the notification system
@router.post("/api/notifications", status_code=201,
             description="Send a notification to WebSocket clients")
async def send_notification(
    message: dict,
    topic: Optional[str] = Query(None, description="Topic to publish to, or broadcast if None")
):
    """
    Send a notification to clients via WebSocket
    Can target a specific topic or broadcast to all connected clients
    """
    sent_count = await notification_service.publish_notification(message, topic)
    return {"status": "published", "recipients": sent_count}

def initialize_websocket_service(app):
    """
    Initialize the WebSocket notification service
    Should be called during application startup
    """
    # Include the WebSocket routes
    app.include_router(router)