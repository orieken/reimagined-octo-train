// src/components/common/NotificationCenter.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useNotifications } from '../../contexts/NotificationContext';

// Simple formatRelativeTime function in case the utility isn't available
const formatRelativeTime = (timestamp) => {
  if (!timestamp) return 'Unknown time';

  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;

    // Convert to seconds
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} minutes ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hours ago`;
    if (diffSec < 604800) return `${Math.floor(diffSec / 86400)} days ago`;

    // Default to date string for older dates
    return date.toLocaleString();
  } catch (e) {
    console.error('Error formatting timestamp:', e);
    return 'Invalid date';
  }
};

const NotificationCenter = () => {
  const [isOpen, setIsOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    requestBrowserNotificationPermission,
    isLoading
  } = useNotifications();
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Determine notification type icon and style
  const getNotificationTypeInfo = (type) => {
    switch (type?.toLowerCase()) {
      case 'success':
        return {
          icon: (
            <svg className="w-6 h-6 text-success" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          bgColor: 'bg-success-light',
          textColor: 'text-success-dark'
        };
      case 'error':
      case 'failure':
        return {
          icon: (
            <svg className="w-6 h-6 text-danger" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          bgColor: 'bg-danger-light',
          textColor: 'text-danger-dark'
        };
      case 'warning':
        return {
          icon: (
            <svg className="w-6 h-6 text-warning" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ),
          bgColor: 'bg-warning-light',
          textColor: 'text-warning-dark'
        };
      case 'info':
      default:
        return {
          icon: (
            <svg className="w-6 h-6 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ),
          bgColor: 'bg-primary-light',
          textColor: 'text-primary-dark'
        };
    }
  };

  // Handle marking a notification as read
  const handleNotificationClick = async (notification) => {
    if (!notification.id) {
      console.error('Cannot mark notification as read: Missing ID');
      return;
    }

    if (!notification.read) {
      await markAsRead(notification.id);
    }

    // Handle notification click (navigate to relevant page, etc.)
    if (notification.link) {
      window.location.href = notification.link;
    }
  };

  // Handle requesting browser notification permission
  const handleEnableBrowserNotifications = async () => {
    try {
      const permission = await requestBrowserNotificationPermission();
      if (permission === 'granted') {
        // Show success message
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Notification Bell Icon */}
      <button
        className="relative p-2 text-gray-400 rounded-full hover:text-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="sr-only">View notifications</span>
        <svg className="w-6 h-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 flex items-center justify-center w-4 h-4 text-xs font-bold text-white bg-danger rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Dropdown */}
      {isOpen && (
        <div className="absolute right-0 z-50 mt-2 overflow-hidden bg-white rounded-md shadow-lg w-80 sm:w-96 ring-1 ring-black ring-opacity-5">
          <div className="p-4 bg-white border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Notifications</h3>
              {unreadCount > 0 && (
                <button
                  className="text-xs text-primary hover:text-primary-dark"
                  onClick={markAllAsRead}
                  disabled={isLoading}
                >
                  Mark all as read
                </button>
              )}
            </div>
          </div>

          {/* Notification List */}
          <div className="overflow-y-auto max-h-80">
            {isLoading ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center text-secondary-dark">
                <svg className="w-12 h-12 mb-2 text-secondary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <p>No notifications</p>
              </div>
            ) : (
              <ul className="divide-y divide-secondary-light">
                {notifications.map((notification) => {
                  const { icon, bgColor, textColor } = getNotificationTypeInfo(notification.type);
                  return (
                    <li
                      key={notification.id}
                      className={`p-4 hover:bg-secondary-light cursor-pointer ${!notification.read ? 'bg-secondary-light bg-opacity-50' : ''}`}
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex items-start">
                        <div className={`flex-shrink-0 p-1 rounded-full ${bgColor}`}>
                          {icon}
                        </div>
                        <div className="ml-3 w-0 flex-1">
                          <p className={`text-sm font-medium ${textColor}`}>
                            {notification.title}
                          </p>
                          <p className="mt-1 text-sm text-secondary-dark">
                            {notification.message}
                          </p>
                          <p className="mt-1 text-xs text-secondary">
                            {formatRelativeTime(notification.timestamp)}
                          </p>
                        </div>
                        {!notification.read && (
                          <div className="ml-3 flex-shrink-0">
                            <span className="inline-block w-2 h-2 bg-primary rounded-full"></span>
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Footer with browser notification option */}
          <div className="p-4 text-xs text-center border-t bg-secondary-light">
            <button
              className="text-primary hover:text-primary-dark"
              onClick={handleEnableBrowserNotifications}
            >
              Enable browser notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationCenter;