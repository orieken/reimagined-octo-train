# app/main.py
import logging
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from app.config import settings
from app.api.routes import api_router
from app.services.vector_db import VectorDBService
# from app.services.worker_manager import worker_manager
from app.services.notification import notification_manager
from app.services.orchestrator import ServiceOrchestrator

# Configure logging
# Use DEBUG if LOG_LEVEL is not available
log_level = getattr(settings, "LOG_LEVEL", "DEBUG")
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("friday")

# Startup and shutdown event handlers
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown event handlers for the FastAPI application.

    This function is called when the application starts up and shuts down.
    It initializes and cleans up resources.
    """
    # Startup: Initialize services
    logger.info("Starting Friday service...")

    # Initialize vector database connection
    vector_db_service = VectorDBService()

    # Initialize notification service background tasks
    logger.info("Starting notification service...")
    await notification_manager.start_background_tasks()

    # Initialize and start workers if auto-start is enabled
    if getattr(settings, "AUTO_START_WORKERS", False):
        logger.info("Auto-starting workers...")
        # await worker_manager.start_workers()

    # Start periodic system notifications (if enabled)
    if getattr(settings, "ENABLE_SYSTEM_NOTIFICATIONS", False):
        logger.info("Starting system notifications...")
        asyncio.create_task(send_periodic_notifications())

    # Initialize orchestrator service
    logger.info("Starting orchestrator service...")
    orchestrator = ServiceOrchestrator()
    # await orchestrator.ping_services()

    logger.info("Services initialized successfully.")
    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down Friday service...")

    # Stop notification service background tasks
    logger.info("Stopping notification service...")
    await notification_manager.stop_background_tasks()

    # Stop all running workers
    # if worker_manager.running:
    #     logger.info("Stopping all workers...")
    #     await worker_manager.stop_workers()

    logger.info("Resources cleaned up successfully.")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API for Friday, an intelligent test analysis service",
    version=settings.APP_VERSION,
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    lifespan=lifespan
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom Swagger UI path
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(req: Request) -> Response:
    """Custom Swagger UI with improved styling."""
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        title=f"{settings.APP_NAME} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


# Mount static files if directory exists
static_dir = os.path.join(os.getcwd(), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include all API routes
app.include_router(api_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint that redirects to docs."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Friday - Intelligent Test Analysis Service",
        "docs": "/docs"
    }


# Add this route to your main.py for a simple test client

@app.get("/test-ws", include_in_schema=False)
async def inline_test_client():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple WebSocket Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            #status {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .connected {
                background-color: #d4edda;
                color: #155724;
            }
            .disconnected {
                background-color: #f8d7da;
                color: #721c24;
            }
            .connecting {
                background-color: #fff3cd;
                color: #856404;
            }
            button {
                padding: 8px 16px;
                margin: 5px;
                cursor: pointer;
            }
            #messages {
                border: 1px solid #ddd;
                padding: 10px;
                margin-top: 20px;
                height: 300px;
                overflow-y: auto;
            }
            .message {
                margin-bottom: 8px;
                padding: 8px;
                border-radius: 4px;
            }
            .received {
                background-color: #e8f4fd;
                border-left: 3px solid #2196F3;
            }
            .sent {
                background-color: #e9f5e9;
                border-left: 3px solid #4CAF50;
            }
            input {
                padding: 8px;
                margin: 5px 0;
                width: 300px;
            }
        </style>
    </head>
    <body>
        <h1>Friday WebSocket Test</h1>

        <div>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
            <button onclick="sendHeartbeat()">Send Heartbeat</button>
        </div>

        <div>
            <input type="text" id="topic" placeholder="Topic name">
            <button onclick="subscribeTopic()">Subscribe</button>
            <button onclick="unsubscribeTopic()">Unsubscribe</button>
        </div>

        <div>
            <input type="text" id="messageInput" placeholder="Custom message">
            <button onclick="sendCustomMessage()">Send</button>
        </div>

        <div id="status" class="disconnected">Disconnected</div>

        <div id="messages"></div>

        <script>
            let socket;

            function updateStatus(message, cls) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = cls;
            }

            function addMessage(message, type) {
                const msgDiv = document.createElement('div');
                msgDiv.className = `message ${type}`;

                const timestamp = new Date().toLocaleTimeString();
                msgDiv.innerHTML = `<strong>${timestamp}</strong>: ${message}`;

                const messages = document.getElementById('messages');
                messages.appendChild(msgDiv);
                messages.scrollTop = messages.scrollHeight;
            }

            function connect() {
                updateStatus('Connecting...', 'connecting');

                // Use the correct WebSocket URL based on your server setup
                socket = new WebSocket('ws://localhost:4000/notifications/ws');

                socket.onopen = function(e) {
                    updateStatus('Connected!', 'connected');
                    addMessage('Connected to server', 'received');
                };

                socket.onmessage = function(event) {
                    addMessage(`Received: ${event.data}`, 'received');

                    try {
                        const data = JSON.parse(event.data);
                        console.log('Parsed message:', data);
                    } catch (e) {
                        console.error('Failed to parse message:', e);
                    }
                };

                socket.onclose = function(event) {
                    let reason = '';
                    if (event.code !== 1000) {
                        reason = ` (Code: ${event.code}${event.reason ? `, Reason: ${event.reason}` : ''})`;
                    }

                    updateStatus(`Disconnected${reason}`, 'disconnected');
                    addMessage(`Disconnected from server${reason}`, 'received');
                };

                socket.onerror = function(error) {
                    updateStatus(`Error: ${error.message || 'Unknown error'}`, 'disconnected');
                    addMessage(`WebSocket error: ${error.message || 'Unknown error'}`, 'received');
                };
            }

            function disconnect() {
                if (socket) {
                    socket.close();
                    socket = null;
                }
            }

            function sendHeartbeat() {
                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    addMessage('Cannot send heartbeat: Not connected', 'sent');
                    return;
                }

                const message = {
                    type: 'heartbeat'
                };

                socket.send(JSON.stringify(message));
                addMessage(`Sent heartbeat`, 'sent');
            }

            function subscribeTopic() {
                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    addMessage('Cannot subscribe: Not connected', 'sent');
                    return;
                }

                const topic = document.getElementById('topic').value.trim();
                if (!topic) {
                    addMessage('Please enter a topic name', 'sent');
                    return;
                }

                const message = {
                    type: 'subscribe',
                    topic: topic
                };

                socket.send(JSON.stringify(message));
                addMessage(`Sent subscription request for topic: ${topic}`, 'sent');
            }

            function unsubscribeTopic() {
                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    addMessage('Cannot unsubscribe: Not connected', 'sent');
                    return;
                }

                const topic = document.getElementById('topic').value.trim();
                if (!topic) {
                    addMessage('Please enter a topic name', 'sent');
                    return;
                }

                const message = {
                    type: 'unsubscribe',
                    topic: topic
                };

                socket.send(JSON.stringify(message));
                addMessage(`Sent unsubscription request for topic: ${topic}`, 'sent');
            }

            function sendCustomMessage() {
                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    addMessage('Cannot send message: Not connected', 'sent');
                    return;
                }

                const msgInput = document.getElementById('messageInput').value.trim();
                if (!msgInput) {
                    addMessage('Please enter a message', 'sent');
                    return;
                }

                try {
                    // Try to parse as JSON first
                    let message;
                    try {
                        message = JSON.parse(msgInput);
                    } catch (e) {
                        // If not valid JSON, send as a custom message
                        message = {
                            type: 'custom',
                            content: msgInput
                        };
                    }

                    const messageStr = JSON.stringify(message);
                    socket.send(messageStr);
                    addMessage(`Sent: ${messageStr}`, 'sent');

                    // Clear input
                    document.getElementById('messageInput').value = '';
                } catch (e) {
                    addMessage(`Error sending message: ${e.message}`, 'sent');
                }
            }
        </script>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")

# Sample background task that sends periodic notifications
async def send_periodic_notifications():
    """
    Example background task that sends periodic system notifications
    about worker status and system health
    """
    await asyncio.sleep(10)  # Wait for startup to complete

    while True:
        try:
            # Check if there are any active connections first
            from app.services.notification import notification_manager
            active_connections_count = len(notification_manager.connection_manager.active_connections)

            if active_connections_count > 0:
                # Get worker status
                # worker_status = "operational" if worker_manager.running else "stopped"
                # workers_count = len(worker_manager.workers)

                # Broadcast system status notification
                message = {
                    "type": "system_status",
                    "service": "friday",
                    "status": "healthy",
                    "workers": {
                        "status": "stopped",
                        "count": 0
                    }
                }

                from app.services.notification import send_notification
                sent = await send_notification(message, topic="system_status")

                if sent > 0:
                    logger.debug(f"Sent system status notification to {sent} clients")
        except Exception as e:
            logger.error(f"Error sending periodic notification: {e}")

        # Send status update every minute
        await asyncio.sleep(60)


# Run the app if executed as script
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
