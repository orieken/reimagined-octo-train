// src/contexts/NotificationContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  initializeNotifications,
  onNotification,
  markAsRead,
  markAllAsRead
} from '../services/notificationService';

// Create the notification context
const NotificationContext = createContext();

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize notifications
  useEffect(() => {
    const initNotifications = async () => {
      try {
        setIsLoading(true);

        // Initialize WebSocket for real-time updates
        initializeNotifications();
        setIsInitialized(true);
      } catch (error) {
        console.error('Failed to initialize notifications:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initNotifications();

    // Clean up on unmount
    return () => {
      // Any cleanup needed
    };
  }, []);

  // Listen for new notifications via WebSocket
  useEffect(() => {
    if (!isInitialized) return;

    const unsubscribe = onNotification((newNotification) => {
      // Skip notifications without an ID
      if (!newNotification.id) {
        console.log('Received notification without ID, skipping:', newNotification);
        return;
      }

      console.log('Processing notification:', newNotification);

      // Add the new notification to the list
      setNotifications(prevNotifications => {
        // Check if this notification already exists (avoid duplicates)
        if (prevNotifications.some(n => n.id === newNotification.id)) {
          return prevNotifications;
        }

        // Add new notification at the beginning
        const updatedNotifications = [
          newNotification,
          ...prevNotifications
        ].slice(0, 100); // Limit to 100 notifications

        return updatedNotifications;
      });

      // Update unread count
      if (!newNotification.read) {
        setUnreadCount(prevCount => prevCount + 1);
      }

      // Trigger browser notification if supported
      showBrowserNotification(newNotification);
    });

    // Clean up subscription when component unmounts
    return () => {
      unsubscribe();
    };
  }, [isInitialized]);

  // Handle browser notifications
  const showBrowserNotification = (notification) => {
    if (!('Notification' in window)) {
      return;
    }

    if (Notification.permission === 'granted') {
      try {
        new Notification('Friday Dashboard', {
          body: notification.message,
          icon: '/favicon.ico'
        });
      } catch (error) {
        console.warn('Error showing browser notification:', error);
      }
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission();
    }
  };

  // Mark a notification as read
  const handleMarkAsRead = async (notificationId) => {
    if (!notificationId) {
      console.error('Cannot mark notification as read: No notification ID provided');
      return false;
    }

    try {
      const success = await markAsRead(notificationId);

      if (success) {
        setNotifications(prevNotifications =>
          prevNotifications.map(notification =>
            notification.id === notificationId
              ? { ...notification, read: true }
              : notification
          )
        );

        setUnreadCount(prevCount => Math.max(0, prevCount - 1));
      }

      return success;
    } catch (error) {
      console.error(`Error marking notification ${notificationId} as read:`, error);
      return false;
    }
  };

  // Mark all notifications as read
  const handleMarkAllAsRead = async () => {
    try {
      const success = await markAllAsRead();

      if (success) {
        setNotifications(prevNotifications =>
          prevNotifications.map(notification => ({
            ...notification,
            read: true
          }))
        );

        setUnreadCount(0);
      }

      return success;
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
      return false;
    }
  };

  // Request permission for browser notifications
  const requestBrowserNotificationPermission = () => {
    if (!('Notification' in window)) {
      return Promise.reject('Browser does not support notifications');
    }

    return Notification.requestPermission();
  };

  // Context value
  const value = {
    notifications,
    unreadCount,
    markAsRead: handleMarkAsRead,
    markAllAsRead: handleMarkAllAsRead,
    requestBrowserNotificationPermission,
    isInitialized,
    isLoading
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

// Custom hook to use the notification context
export function useNotifications() {
  const context = useContext(NotificationContext);

  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }

  return context;
}

// Also export the context itself
export default NotificationContext;
