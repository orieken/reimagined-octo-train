// src/utils/formatters.js
import { format, formatDistanceToNow } from 'date-fns';

/**
 * Format a date as a string
 * @param {string|Date} date - The date to format
 * @param {string} formatString - The format string (default: 'PPP')
 * @returns {string} The formatted date string
 */
export const formatDate = (date, formatString = 'PPP') => {
  if (!date) return '';
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, formatString);
};

/**
 * Format a date as relative time (e.g., "2 hours ago")
 * @param {string|Date} date - The date to format
 * @param {Object} options - Options for formatDistanceToNow
 * @returns {string} The formatted relative time string
 */
export const formatRelativeTime = (date, options = {}) => {
  if (!date) return '';
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(dateObj, { addSuffix: true, ...options });
};

/**
 * Format a number as a percentage
 * @param {number} value - The value to format
 * @param {number} decimals - The number of decimal places (default: 1)
 * @returns {string} The formatted percentage string
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === undefined || value === null) return '';
  return `${value.toFixed(decimals)}%`;
};

/**
 * Format a number with comma separators
 * @param {number} value - The value to format
 * @returns {string} The formatted number string
 */
export const formatNumber = (value) => {
  if (value === undefined || value === null) return '';
  return value.toLocaleString();
};

/**
 * Format a duration in milliseconds
 * @param {number} ms - The duration in milliseconds
 * @returns {string} The formatted duration string
 */
export const formatDuration = (ms) => {
  if (ms === undefined || ms === null) return '';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
};

/**
 * Truncate a string to a maximum length
 * @param {string} str - The string to truncate
 * @param {number} maxLength - The maximum length (default: 50)
 * @returns {string} The truncated string
 */
export const truncateString = (str, maxLength = 50) => {
  if (!str) return '';
  if (str.length <= maxLength) return str;
  return `${str.substring(0, maxLength)}...`;
};

/**
 * Format a status string to title case with color class
 * @param {string} status - The status string (e.g., 'passed', 'failed')
 * @returns {Object} An object with text and color properties
 */
export const formatStatus = (status) => {
  if (!status) return { text: '', color: '' };

  const statusMap = {
    passed: { text: 'Passed', color: 'text-success' },
    failed: { text: 'Failed', color: 'text-danger' },
    skipped: { text: 'Skipped', color: 'text-warning' },
    pending: { text: 'Pending', color: 'text-secondary' },
    undefined: { text: 'Undefined', color: 'text-secondary-dark' }
  };

  const lowerStatus = status.toLowerCase();
  return statusMap[lowerStatus] || { text: status, color: '' };
};
