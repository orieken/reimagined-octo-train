# Friday Service WebSocket Notification System

This guide explains how the WebSocket notification system has been integrated with the Friday Service.

## Implementation Overview

The WebSocket notification system provides real-time communication capabilities to the Friday Service, enabling event broadcasting to connected clients. The implementation follows the requirements you specified:

1. ✅ Updated notification service to handle client connections and broadcasts
2. ✅ Created resilient WebSocket routes that handle both `/ws` and `/ws/{client_id}` patterns
3. ✅ Implemented error handling and automatic reconnection logic
4. ✅ Added CORS support for WebSocket connections
5. ✅ Created a test client for verifying WebSocket functionality

## File Structure

The implementation adds the following files to your existing project:

```
app/
├── services/
│   └── notification_service.py  (New)
├── api/
│   └── websocket_routes.py  (New)
└── static/
    └── websocket_test_client.html  (New)
```

The `main.py` file has been updated to integrate these new components.

## Key Components

### 1. Notification Service

`app/services/notification_service.py` provides:

- Connection management (connect, disconnect, heartbeat)
- Subscription system (subscribe/unsubscribe to topics)
- Message broadcasting (to all clients or by topic)
- Background tasks for connection monitoring

### 2. WebSocket Routes

`app/api/websocket_routes.py` defines:

- WebSocket endpoints (`/ws` and `/ws/{client_id}`)
- HTTP endpoints for sending notifications
- Integration with the main FastAPI application

### 3. Main Application Integration

The main application (`app/main.py`) has been updated to:

- Initialize the notification service during startup
- Clean up resources during shutdown
- Mount WebSocket routes
- Optionally run a periodic notification task

### 4. WebSocket Test Client

`app/static/websocket_test_client.html` provides:

- Connection controls (connect, disconnect, heartbeat)
- Subscription management
- Message sending and receiving
- Automatic reconnection logic

## Usage Examples

### Sending Notifications from Code

You can send notifications from any part of your application by importing the notification service:

```python
from app.services.notification_service import notification_service

# Example: Send notification when a test run completes
async def on_test_run_complete(run_id, status):
    await notification_service.publish_notification({
        "type": "test_run_status",
        "run_id": run_id,
        "status": status,
        "message": f"Test run {run_id} completed with status: {status}"
    }, topic=f"test_run_{run_id}")
```

### API Endpoint for Notifications

There's also an HTTP endpoint for sending notifications:

```
POST /api/notifications
{
  "type": "alert",
  "message": "System update scheduled"
}
?topic=system_alerts  # Optional query parameter
```

### Client-Side Connection (JavaScript)

```javascript
// Connect to WebSocket
const socket = new WebSocket('ws://your-friday-service-url/ws');

// Listen for messages
socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
  
  // Handle different message types
  if (message.type === 'test_run_status') {
    updateTestRunUI(message.run_id, message.status);
  }
};

// Subscribe to topics
socket.onopen = () => {
  socket.send(JSON.stringify({
    type: 'subscribe',
    topic: 'system_status'
  }));
};
```

## Message Protocol

### Client to Server Messages

1. **Heartbeat**
   ```json
   {"type": "heartbeat"}
   ```

2. **Subscribe to Topic**
   ```json
   {"type": "subscribe", "topic": "test_results"}
   ```

3. **Unsubscribe from Topic**
   ```json
   {"type": "unsubscribe", "topic": "test_results"}
   ```

### Server to Client Messages

1. **Connection Confirmation**
   ```json
   {
     "type": "connection",
     "status": "connected",
     "client_id": "client-uuid-123"
   }
   ```

2. **Subscription Confirmation**
   ```json
   {
     "type": "subscription",
     "topic": "test_results",
     "status": "subscribed"
   }
   ```

3. **Notification Messages**
   ```json
   {
     "type": "notification",
     "message": "Test run completed",
     "data": { ... },
     "timestamp": "2025-04-02T14:30:00.000Z"
   }
   ```

## Testing the Integration

1. Start your Friday Service
2. Access the test client at `/test-ws` (only available in DEBUG mode)
3. Connect to the WebSocket endpoint
4. Try subscribing to topics like `system_status`
5. Send test messages and observe the responses

## Next Steps and Considerations

1. **Authentication**: Consider adding authentication for WebSocket connections, possibly using JWT tokens
2. **Rate Limiting**: Implement rate limiting for subscription requests and message sending
3. **Persistent Connections**: For production, ensure your infrastructure supports persistent WebSocket connections
4. **Scaling**: For high-load scenarios, consider a distributed notification system using Redis pub/sub
5. **Monitoring**: Add metrics for connection counts, message throughput, and error rates

## Troubleshooting

- **Connection Issues**: Ensure your network/proxy allows WebSocket connections
- **404 Errors**: Check that the WebSocket routes are properly registered
- **Disconnections**: Look for timeout configurations in any proxy or load balancer
- **Message Not Received**: Verify the topic name and subscription status