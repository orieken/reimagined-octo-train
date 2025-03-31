// src/utils/colors.js

/**
 * Generate a color based on a value within a range
 * @param {number} value - The value to map to a color
 * @param {number} min - The minimum value in the range (default: 0)
 * @param {number} max - The maximum value in the range (default: 100)
 * @returns {string} A color in hex format
 */
export const getColorFromValue = (value, min = 0, max = 100) => {
  // Ensure value is within bounds
  const bounded = Math.max(min, Math.min(max, value));

  // Normalize the value to a 0-1 range
  const normalized = (bounded - min) / (max - min);

  // Generate colors from red to green
  const r = Math.round(255 * (1 - normalized));
  const g = Math.round(255 * normalized);
  const b = 0;

  // Convert to hex
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
};

/**
 * Generate a color class for Tailwind CSS based on a value
 * @param {number} value - The value to map to a color class
 * @returns {string} A Tailwind CSS color class
 */
export const getColorClassFromValue = (value) => {
  if (value >= 90) return 'bg-success text-white';
  if (value >= 75) return 'bg-success-light text-success-dark';
  if (value >= 60) return 'bg-warning text-white';
  if (value >= 40) return 'bg-warning-light text-warning-dark';
  return 'bg-danger text-white';
};

/**
 * Get a status color class based on a status string
 * @param {string} status - The status string (e.g., 'passed', 'failed')
 * @returns {string} A Tailwind CSS color class
 */
export const getStatusColorClass = (status) => {
  if (!status) return '';

  const lowerStatus = status.toLowerCase();
  switch (lowerStatus) {
    case 'passed':
      return 'bg-success text-white';
    case 'failed':
      return 'bg-danger text-white';
    case 'skipped':
      return 'bg-warning text-white';
    case 'pending':
      return 'bg-secondary text-white';
    default:
      return 'bg-secondary-light text-secondary-dark';
  }
};

/**
 * Generate a color from a string (useful for consistent colors for tags, features, etc.)
 * @param {string} str - The string to generate a color from
 * @returns {string} A color in hex format
 */
export const getColorFromString = (str) => {
  if (!str) return '#A0AEC0'; // Default gray

  // Simple hash function
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }

  // Convert to hex color
  let color = '#';
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xFF;
    color += ('00' + value.toString(16)).substr(-2);
  }

  return color;
};

/**
 * Predefined colors for charts
 */
export const chartColors = {
  primary: '#3182CE',
  secondary: '#A0AEC0',
  success: '#48BB78',
  danger: '#F56565',
  warning: '#ED8936',
  info: '#4299E1',
  purple: '#9F7AEA',
  pink: '#ED64A6',
  indigo: '#667EEA',
  teal: '#38B2AC'
};

/**
 * Get a set of colors for a chart with n segments
 * @param {number} n - Number of segments/series in the chart
 * @returns {string[]} An array of colors
 */
export const getChartColors = (n) => {
  const colors = Object.values(chartColors);

  if (n <= colors.length) {
    return colors.slice(0, n);
  }

  // If we need more colors than predefined, generate additional ones
  const result = [...colors];
  for (let i = colors.length; i < n; i++) {
    result.push(getColorFromString(`additional-${i}`));
  }

  return result;
};