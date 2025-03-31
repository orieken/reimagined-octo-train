// src/services/api.js
import axios from 'axios';
import {
  adaptTestStats,
  adaptHealthCheck,
  adaptQueryResults,
  adaptTestResults,
  adaptTestTrends,
  adaptFailureAnalysis
} from './apiAdapter';

// Get API URL from environment variables or use '/api' as default for development
const API_URL = import.meta.env.VITE_API_URL || '/api';

// Create an axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor for authentication if needed
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    console.log(`Making request to: ${config.baseURL}${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Add more detailed console logging for debugging
    console.error('API Error:', error.response || error.message || error);
    return Promise.reject(error);
  }
);

// API endpoint functions
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    console.log('Health check response:', response.data);
    return adaptHealthCheck(response.data);
  } catch (error) {
    console.error('Health check failed:', error);
    return { isConnected: false, error: error.message };
  }
};

export const processCucumberReports = async (reports) => {
  const response = await apiClient.post('/processor/cucumber-reports', reports);
  return response.data;
};

export const processBuildInfo = async (buildInfo) => {
  const response = await apiClient.post('/processor/build-info', buildInfo);
  return response.data;
};

export const queryTestData = async (query) => {
  const response = await apiClient.post('/query', { query });
  return adaptQueryResults(response.data);
};

export const getTestStats = async () => {
  try {
    const response = await apiClient.get('/stats');
    console.log('Raw API stats response:', response.data);
    const adaptedData = adaptTestStats(response.data);
    console.log('Adapted stats data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.error('Failed to get test stats:', error);
    throw error;
  }
};

export const getDetailedTestResults = async (filter = {}) => {
  try {
    // Convert filter to query parameters if needed
    const params = new URLSearchParams();
    Object.entries(filter).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value);
      }
    });

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const response = await apiClient.get(`/test-results${queryString}`);
    console.log('Raw test results response:', response.data);

    // Using the mock data temporarily if API doesn't provide this endpoint yet
    let result;
    if (response.data?.status === "error" || !response.data?.results) {
      console.log('Using default test results data as API endpoint may not be implemented');
      // Default to the statistics endpoint data with some modifications
      const statsResponse = await apiClient.get('/stats');

      // Create a simplified mock structure based on the stats response
      const mockData = {
        status: "success",
        results: {
          ...statsResponse.data.statistics,
          features: [
            // Create some mock features based on tags
            ...Object.entries(statsResponse.data.statistics.top_tags || {})
              .slice(0, 5)
              .map(([tagName, count]) => {
                const passed = Math.floor(count * statsResponse.data.statistics.pass_rate);
                const failed = count - passed;
                return {
                  name: tagName.replace('@', ''),
                  passed_scenarios: passed,
                  failed_scenarios: failed,
                  skipped_scenarios: 0
                };
              })
          ],
          tags: Object.entries(statsResponse.data.statistics.top_tags || {})
            .reduce((acc, [tag, count]) => {
              acc[tag] = {
                count,
                pass_rate: statsResponse.data.statistics.pass_rate
              };
              return acc;
            }, {})
        }
      };

      result = adaptTestResults(mockData);
    } else {
      result = adaptTestResults(response.data);
    }

    console.log('Adapted test results data:', result);
    return result;
  } catch (error) {
    console.error('Failed to get detailed test results:', error);

    // Fallback to some basic data to avoid UI crashes
    return {
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      skippedTests: 0,
      passRate: 0,
      lastUpdated: new Date().toISOString(),
      featureResults: [],
      tags: []
    };
  }
};

export const getTestTrends = async (timeRange = 'week') => {
  try {
    const response = await apiClient.get(`/trends?timeRange=${timeRange}`);
    console.log('Raw trends response:', response.data);

    // Fallback to mock data for now if API doesn't support this endpoint yet
    if (response.data?.status === "error" || !response.data?.trends) {
      console.log('Using default trends data');
      return generateMockTrendsData(timeRange);
    }

    const adaptedData = adaptTestTrends(response.data);
    console.log('Adapted trends data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.error('Failed to get test trends:', error);
    return generateMockTrendsData(timeRange);
  }
};

export const getFailureAnalysis = async () => {
  try {
    const response = await apiClient.get('/failures');
    console.log('Raw failures response:', response.data);

    // Fallback to mock data for now if API doesn't support this endpoint yet
    if (response.data?.status === "error" || !response.data?.failures) {
      console.log('Using default failure analysis data');
      return generateMockFailureData();
    }

    const adaptedData = adaptFailureAnalysis(response.data);
    console.log('Adapted failure data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.error('Failed to get failure analysis:', error);
    return generateMockFailureData();
  }
};

// Helper function to generate mock trends data
const generateMockTrendsData = (timeRange) => {
  // Generate sample data based on time range
  let data;
  if (timeRange === 'week') {
    data = generateDailyData(7);
  } else if (timeRange === 'month') {
    data = generateDailyData(30);
  } else {
    data = generateWeeklyData(12);
  }

  return data;
};

// Helper function to generate daily test data
const generateDailyData = (days) => {
  const data = [];
  const now = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // Generate random but somewhat consistent data
    const totalTests = Math.floor(Math.random() * 100) + 100;
    const passRate = 75 + Math.sin(i / 3) * 15 + (Math.random() * 5);
    const passedTests = Math.floor(totalTests * (passRate / 100));
    const failedTests = totalTests - passedTests;

    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      totalTests,
      passedTests,
      failedTests,
      passRate: Math.round(passRate * 10) / 10,
    });
  }

  return {
    dailyTrends: data,
    buildComparison: generateBuildComparison(),
    topFailingTests: generateTopFailingTests()
  };
};

// Helper function to generate weekly test data
const generateWeeklyData = (weeks) => {
  const data = [];
  const now = new Date();

  for (let i = weeks - 1; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - (i * 7));

    // Generate random but somewhat consistent data
    const totalTests = Math.floor(Math.random() * 500) + 500;
    const passRate = 75 + Math.sin(i / 4) * 15 + (Math.random() * 5);
    const passedTests = Math.floor(totalTests * (passRate / 100));
    const failedTests = totalTests - passedTests;

    data.push({
      date: `Week ${weeks - i}`,
      totalTests,
      passedTests,
      failedTests,
      passRate: Math.round(passRate * 10) / 10,
    });
  }

  return {
    dailyTrends: data,
    buildComparison: generateBuildComparison(),
    topFailingTests: generateTopFailingTests()
  };
};

// Helper function to generate build comparison data
const generateBuildComparison = () => {
  const builds = [];

  for (let i = 0; i < 5; i++) {
    const buildNumber = 1000 + i;
    const passRate = 75 + Math.sin(i) * 15 + (Math.random() * 5);

    builds.push({
      buildNumber: `#${buildNumber}`,
      passRate: Math.round(passRate * 10) / 10,
    });
  }

  return builds.reverse();
};

// Helper function to generate top failing tests
const generateTopFailingTests = () => {
  const tests = [
    'User authentication with invalid credentials',
    'Product checkout with expired credit card',
    'Search functionality with special characters',
    'User profile update with invalid data',
    'Product catalog filtering by multiple criteria'
  ];

  return tests.map((test, index) => ({
    name: test,
    failureRate: Math.round((40 - index * 3) * 10) / 10,
    occurrences: Math.floor(Math.random() * 10) + 5
  }));
};

// Helper function to generate mock failure data
const generateMockFailureData = () => {
  return {
    failureCategories: [
      { name: 'UI Elements Not Found', value: 95, percentage: 35.7 },
      { name: 'Timeout Errors', value: 68, percentage: 25.6 },
      { name: 'Assertion Failures', value: 45, percentage: 16.9 },
      { name: 'API Response Errors', value: 32, percentage: 12.0 },
      { name: 'Database Connection', value: 16, percentage: 6.0 },
      { name: 'Other', value: 10, percentage: 3.8 }
    ],
    failureDetails: {
      'UI Elements Not Found': [
        { element: 'Submit Button', occurrences: 24, scenarios: ['User Registration', 'Checkout'] },
        { element: 'Search Results', occurrences: 18, scenarios: ['Product Search', 'Content Search'] },
        { element: 'Navigation Menu', occurrences: 15, scenarios: ['Homepage', 'Category Pages'] }
      ],
      'Timeout Errors': [
        { element: 'API Response', occurrences: 28, scenarios: ['Product Catalog', 'Search Results'] },
        { element: 'Page Load', occurrences: 22, scenarios: ['Product Details', 'Checkout'] },
        { element: 'Payment Processing', occurrences: 18, scenarios: ['Checkout'] }
      ]
    },
    failuresByFeature: [
      { feature: 'Checkout', failures: 64, tests: 204, failureRate: 31.4 },
      { feature: 'Search', failures: 43, tests: 230, failureRate: 18.7 },
      { feature: 'User Profile', failures: 23, tests: 120, failureRate: 19.2 },
      { feature: 'Product Catalog', failures: 64, tests: 329, failureRate: 19.5 },
      { feature: 'Authentication', failures: 12, tests: 140, failureRate: 8.6 }
    ],
    recentFailures: [
      {
        id: 'F123',
        scenario: 'User cannot complete checkout with saved payment method',
        error: 'Timeout waiting for payment confirmation dialog',
        date: new Date().toISOString(),
        build: '#1045'
      },
      {
        id: 'F122',
        scenario: 'Search results do not include relevant products',
        error: 'Assertion error: Expected search results to contain "bluetooth headphones"',
        date: new Date(Date.now() - 3600000).toISOString(),
        build: '#1045'
      },
      {
        id: 'F121',
        scenario: 'User profile update fails with valid data',
        error: 'Element not found: Save Changes button',
        date: new Date(Date.now() - 7200000).toISOString(),
        build: '#1044'
      }
    ]
  };
};

export default apiClient;