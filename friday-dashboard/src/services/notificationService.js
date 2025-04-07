// src/services/notificationService.js
import apiClient from './api';

// Connection variables
let socket = null;
let reconnectTimer = null;
let reconnectInterval = 2000; // Start with 2 seconds, will increase with backoff
const maxReconnectInterval = 30000; // Max 30 seconds between reconnection attempts
let notificationCallbacks = [];

// WebSocket endpoint for notifications
const WS_URL = 'ws://localhost:4000/notifications/ws';

/**
 * Initialize WebSocket connection for notifications
 */
export const initializeNotifications = () => {
  // If we already have a socket, don't create another
  if (socket) {
    console.log('WebSocket connection already established');
    return;
  }

  try {
    console.log('Connecting to notification WebSocket at:', WS_URL);

    // Create WebSocket connection
    socket = new WebSocket(WS_URL);

    // Connection opened
    socket.addEventListener('open', (event) => {
      console.log('Connected to notification service');
      resetReconnectTimer();
    });

    // Listen for messages
    socket.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);

        // Skip connection messages
        if (data.type === 'connection') {
          console.log('Connection established with client ID:', data.client_id);
          return;
        }

        // Notify all registered callbacks for actual notifications
        notificationCallbacks.forEach(callback => {
          try {
            callback(data);
          } catch (err) {
            console.error('Error in notification callback:', err);
          }
        });
      } catch (err) {
        console.error('Error parsing notification:', err);
      }
    });

    // Connection closed
    socket.addEventListener('close', (event) => {
      console.log('Disconnected from notification service:', event.code, event.reason);
      socket = null;
      scheduleReconnect();
    });

    // Connection error
    socket.addEventListener('error', (event) => {
      console.error('WebSocket error:', event);
      // The socket will be closed automatically after an error
    });
  } catch (err) {
    console.error('Error initializing WebSocket connection:', err);
    socket = null;
    scheduleReconnect();
  }
};

/**
 * Close WebSocket connection
 */
export const closeNotifications = () => {
  resetReconnectTimer();

  if (socket) {
    socket.close();
    socket = null;
  }
};

/**
 * Register a callback to be notified of new messages
 * @param {Function} callback - Function to call with notification data
 * @returns {Function} - Function to call to unregister the callback
 */
export const onNotification = (callback) => {
  notificationCallbacks.push(callback);

  // Make sure we're connected
  if (!socket) {
    initializeNotifications();
  }

  // Return a function to remove this callback
  return () => {
    notificationCallbacks = notificationCallbacks.filter(cb => cb !== callback);

    // If no callbacks remain, close the connection
    if (notificationCallbacks.length === 0) {
      closeNotifications();
    }
  };
};

/**
 * Schedule a reconnection attempt with exponential backoff
 */
const scheduleReconnect = () => {
  resetReconnectTimer();

  reconnectTimer = setTimeout(() => {
    console.log(`Attempting to reconnect to notification service...`);
    initializeNotifications();

    // Increase the reconnect interval for exponential backoff
    reconnectInterval = Math.min(reconnectInterval * 1.5, maxReconnectInterval);
  }, reconnectInterval);
};

/**
 * Reset the reconnection timer
 */
const resetReconnectTimer = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  reconnectInterval = 2000; // Reset to initial value
};

/**
 * Mark a notification as read
 * @param {string} notificationId - ID of the notification to mark as read
 * @returns {Promise<boolean>} - Success status
 */
export const markAsRead = async (notificationId) => {
  if (!notificationId) {
    console.error('Cannot mark notification as read: No notification ID provided');
    return false;
  }

  try {
    console.log(`Marking notification ${notificationId} as read`);
    await apiClient.post(`/notifications/${notificationId}/read`);
    return true;
  } catch (err) {
    console.error(`Failed to mark notification ${notificationId} as read:`, err);
    return false;
  }
};

/**
 * Mark all notifications as read
 * @returns {Promise<boolean>} - Success status
 */
export const markAllAsRead = async () => {
  try {
    await apiClient.post('/notifications/read-all');
    return true;
  } catch (err) {
    console.error('Failed to mark all notifications as read:', err);
    return false;
  }
};

/**
 * Get user notification preferences
 * @returns {Promise<Object>} - User notification preferences
 */
export const getNotificationPreferences = async () => {
  try {
    const response = await apiClient.get('/notifications/preferences');
    return response.data.preferences || {};
  } catch (err) {
    console.error('Failed to fetch notification preferences:', err);
    throw err;
  }
};

/**
 * Update user notification preferences
 * @param {Object} preferences - Updated notification preferences
 * @returns {Promise<boolean>} - Success status
 */
export const updateNotificationPreferences = async (preferences) => {
  try {
    await apiClient.post('/notifications/preferences', { preferences });
    return true;
  } catch (err) {
    console.error('Failed to update notification preferences:', err);
    throw err;
  }
};