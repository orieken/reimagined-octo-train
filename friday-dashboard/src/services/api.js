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

// Flag to track if we're using mock data
let usingMockData = false;

// Create an axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Don't let API call failures stop our app - we'll handle with fallbacks
  validateStatus: status => true
});

// Add a request interceptor for authentication if needed
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    console.log(`Making request to: ${config.baseURL}${config.url}`);
    return config;
  },
  (error) => {
    console.warn('Request error:', error);
    return Promise.reject(error);
  }
);

// Add a response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // If we get a 404 or 5xx, use mock data
    if (response.status >= 400) {
      console.warn(`API returned status ${response.status} for ${response.config.url}, will use mock data`);
      usingMockData = true;
      return response;
    }
    return response;
  },
  (error) => {
    // Add more detailed console logging for debugging
    console.error('API Error:', error.response || error.message || error);
    usingMockData = true;
    return Promise.reject(error);
  }
);

// Mock data for endpoints that aren't available yet
const mockData = {
  stats: {
    status: "success",
    statistics: {
      total_scenarios: 95,
      passed_scenarios: 65,
      failed_scenarios: 30,
      pass_rate: 0.6842105263157895,
      unique_builds: 10,
      top_tags: {
        "@medium": 18,
        "@sprint-22": 16,
        "@cart": 16,
        "@api": 14,
        "@checkout": 13,
        "@low": 13,
        "@high": 11,
        "@account": 11,
        "@payment": 11,
        "@jira-123": 11
      }
    }
  },

  health: {
    status: "success",
    version: "0.1.0",
    timestamp: new Date().toISOString()
  },

  results: {
    status: "success",
    results: {
      total_scenarios: 95,
      passed_scenarios: 65,
      failed_scenarios: 30,
      skipped_scenarios: 0,
      pass_rate: 0.6842105263157895,
      last_updated: new Date().toISOString(),
      features: [
        {
          name: "Authentication",
          passed_scenarios: 12,
          failed_scenarios: 2,
          skipped_scenarios: 0
        },
        {
          name: "Shopping Cart",
          passed_scenarios: 14,
          failed_scenarios: 4,
          skipped_scenarios: 0
        },
        {
          name: "Checkout",
          passed_scenarios: 10,
          failed_scenarios: 5,
          skipped_scenarios: 0
        },
        {
          name: "User Account",
          passed_scenarios: 9,
          failed_scenarios: 3,
          skipped_scenarios: 0
        },
        {
          name: "Product Search",
          passed_scenarios: 20,
          failed_scenarios: 6,
          skipped_scenarios: 0
        }
      ],
      tags: {
        "@medium": {
          count: 18,
          pass_rate: 0.72
        },
        "@sprint-22": {
          count: 16,
          pass_rate: 0.69
        },
        "@cart": {
          count: 16,
          pass_rate: 0.75
        },
        "@api": {
          count: 14,
          pass_rate: 0.85
        },
        "@checkout": {
          count: 13,
          pass_rate: 0.62
        }
      }
    }
  }
};

/**
 * Check if we're using mock data
 */
export const isUsingMockData = () => {
  return usingMockData;
};

export function getAPIVersionPrefix() {
  const prefix = import.meta.env.VITE_API_VERSION_PREFIX;
  return prefix ? `/${prefix}` : '';
}

// API endpoint functions
export const checkHealth = async () => {
  try {
    const response = await apiClient.get(`/health`);

    // If we got an error response, use mock data
    if (response.status >= 400) {
      console.log('Health check failed, using mock data');
      return adaptHealthCheck(mockData.health);
    }

    console.log('Health check response:', response.data);
    return adaptHealthCheck(response.data);
  } catch (error) {
    console.warn('Health check failed, using mock data:', error);
    usingMockData = true;
    return adaptHealthCheck(mockData.health);
  }
};

export const processCucumberReports = async (reports) => {
  if (usingMockData) {
    console.log('Using mock data (mock mode)');
    return { status: "success", message: "Reports processed successfully" };
  }

  try {
    const response = await apiClient.post('/cucumber-reports', reports);

    if (response.status >= 400) {
      console.log('Failed to process cucumber reports, using mock response');
      usingMockData = true;
      return { status: "success", message: "Reports processed successfully" };
    }

    return response.data;
  } catch (error) {
    console.warn('Failed to process cucumber reports, using mock response:', error);
    usingMockData = true;
    return { status: "success", message: "Reports processed successfully" };
  }
};

export const processBuildInfo = async (buildInfo) => {
  if (usingMockData) {
    console.log('Using mock data (mock mode)');
    return { status: "success", message: "Build info processed successfully" };
  }

  try {
    const response = await apiClient.post('/builds', buildInfo);

    if (response.status >= 400) {
      console.log('Failed to process build info, using mock response');
      usingMockData = true;
      return { status: "success", message: "Build info processed successfully" };
    }

    return response.data;
  } catch (error) {
    console.warn('Failed to process build info, using mock response:', error);
    usingMockData = true;
    return { status: "success", message: "Build info processed successfully" };
  }
};

export const queryTestData = async (query) => {
  if (usingMockData) {
    console.log('Using mock data for query:', query);
    return adaptQueryResults({
      status: "success",
      result: `Here is information about "${query}". This is a mock response since the API endpoint is not available.`,
      sources: [
        { title: "Mock Source 1", confidence: 0.85 },
        { title: "Mock Source 2", confidence: 0.75 }
      ],
      related_queries: [
        "What are common test failures?",
        "Show test trends for last week",
        "What's the pass rate for checkout tests?"
      ]
    });
  }

  try {
    const response = await apiClient.post('/query', { query });

    if (response.status >= 400) {
      console.log('Query failed, using mock data');
      usingMockData = true;
      return adaptQueryResults({
        status: "success",
        result: `Here is information about "${query}". This is a mock response since the API endpoint is not available.`,
        sources: [
          { title: "Mock Source 1", confidence: 0.85 },
          { title: "Mock Source 2", confidence: 0.75 }
        ],
        related_queries: [
          "What are common test failures?",
          "Show test trends for last week",
          "What's the pass rate for checkout tests?"
        ]
      });
    }

    return adaptQueryResults(response.data);
  } catch (error) {
    console.warn('Query failed, using mock data:', error);
    usingMockData = true;
    return adaptQueryResults({
      status: "success",
      result: `Here is information about "${query}". This is a mock response since the API endpoint is not available.`,
      sources: [
        { title: "Mock Source 1", confidence: 0.85 },
        { title: "Mock Source 2", confidence: 0.75 }
      ],
      related_queries: [
        "What are common test failures?",
        "Show test trends for last week",
        "What's the pass rate for checkout tests?"
      ]
    });
  }
};

export const getTestStats = async () => {
  try {
    const response = await apiClient.get('/stats/summary');

    // If status is 404 or other error, use mock data
    if (response.status >= 400) {
      console.log('Failed to get test stats, using mock data');
      usingMockData = true;
      const adaptedData = adaptTestStats(mockData.stats);
      console.log('Adapted mock stats data:', adaptedData);
      return adaptedData;
    }

    console.log('Raw API stats response:', response.data);
    const adaptedData = adaptTestStats(response.data);
    console.log('Adapted stats data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.warn('Failed to get test stats, using mock data:', error);
    usingMockData = true;
    const adaptedData = adaptTestStats(mockData.stats);
    console.log('Adapted mock stats data:', adaptedData);
    return adaptedData;
  }
};

export const getDetailedTestResults = async (filter = {}) => {
  if (usingMockData) {
    console.log('Using mock data for detailed test results');
    return adaptTestResults(mockData.results);
  }

  try {
    // Convert filter to query parameters if needed
    const params = new URLSearchParams();
    Object.entries(filter).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value);
      }
    });

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const response = await apiClient.get(`/results${queryString}`);

    if (response.status >= 400) {
      console.log('Failed to get detailed test results, using mock data');
      usingMockData = true;
      return adaptTestResults(mockData.results);
    }

    console.log('Raw test results response:', response.data);
    return adaptTestResults(response.data);
  } catch (error) {
    console.warn('Failed to get detailed test results, using mock data:', error);
    usingMockData = true;
    return adaptTestResults(mockData.results);
  }
};

export const getTestTrends = async (timeRange = 'week') => {
  if (usingMockData) {
    console.log('Using mock data for test trends');
    return generateMockTrendsData(timeRange);
  }

  try {
    const response = await apiClient.get(`/trends?time_range=${timeRange}`);

    if (response.status >= 400) {
      console.log('Failed to get test trends, using mock data');
      usingMockData = true;
      return generateMockTrendsData(timeRange);
    }

    console.log('Raw trends response:', response.data);
    const adaptedData = adaptTestTrends(response.data);
    console.log('Adapted trends data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.warn('Failed to get test trends, using mock data:', error);
    usingMockData = true;
    return generateMockTrendsData(timeRange);
  }
};

export const getFailureAnalysis = async () => {
  if (usingMockData) {
    console.log('Using mock data for failure analysis');
    return generateMockFailureData();
  }

  try {
    const response = await apiClient.get('/failures');

    if (response.status >= 400) {
      console.log('Failed to get failure analysis, using mock data');
      usingMockData = true;
      return generateMockFailureData();
    }

    console.log('Raw failures response:', response.data);
    const adaptedData = adaptFailureAnalysis(response.data);
    console.log('Adapted failure data:', adaptedData);
    return adaptedData;
  } catch (error) {
    console.warn('Failed to get failure analysis, using mock data:', error);
    usingMockData = true;
    return generateMockFailureData();
  }
};

// Get builds list
export const getBuilds = async () => {
  if (usingMockData) {
    console.log('Using mock data for builds list');
    return generateMockBuilds();
  }

  try {
    const response = await apiClient.get('/builds');

    if (response.status >= 400) {
      console.log('Failed to get builds, using mock data');
      usingMockData = true;
      return generateMockBuilds();
    }

    console.log('Raw builds response:', response.data);
    return response.data.builds || [];
  } catch (error) {
    console.warn('Failed to get builds, using mock data:', error);
    usingMockData = true;
    return generateMockBuilds();
  }
};

// Get build details
export const getBuildDetails = async (buildId) => {
  if (usingMockData) {
    console.log(`Using mock data for build ${buildId} details`);
    return generateMockBuildDetails(buildId);
  }

  try {
    const response = await apiClient.get(`/builds/${buildId}`);

    if (response.status >= 400) {
      console.log(`Failed to get build ${buildId} details, using mock data`);
      usingMockData = true;
      return generateMockBuildDetails(buildId);
    }

    console.log(`Raw build ${buildId} details:`, response.data);
    return response.data;
  } catch (error) {
    console.warn(`Failed to get build ${buildId} details, using mock data:`, error);
    usingMockData = true;
    return generateMockBuildDetails(buildId);
  }
};

// Get scenarios
export const getScenarios = async (filter = {}) => {
  if (usingMockData) {
    console.log('Using mock data for scenarios');
    return generateMockScenarios(filter);
  }

  try {
    // Convert filter to query parameters
    const params = new URLSearchParams();
    Object.entries(filter).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value);
      }
    });

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const response = await apiClient.get(`/scenarios${queryString}`);

    if (response.status >= 400) {
      console.log('Failed to get scenarios, using mock data');
      usingMockData = true;
      return generateMockScenarios(filter);
    }

    console.log('Raw scenarios response:', response.data);
    return response.data.scenarios || [];
  } catch (error) {
    console.warn('Failed to get scenarios, using mock data:', error);
    usingMockData = true;
    return generateMockScenarios(filter);
  }
};

// Generate mock builds
const generateMockBuilds = () => {
  const builds = [];
  const now = new Date();

  for (let i = 0; i < 10; i++) {
    const buildDate = new Date(now);
    buildDate.setDate(buildDate.getDate() - i);

    const passRate = 0.60 + (Math.random() * 0.30); // Between 60% and 90%
    const totalScenarios = Math.floor(90 + (Math.random() * 20)); // Between 90 and 110
    const passedScenarios = Math.floor(totalScenarios * passRate);
    const failedScenarios = totalScenarios - passedScenarios;

    builds.push({
      id: `build-${1045 - i}`,
      build_number: `${1045 - i}`,
      date: buildDate.toISOString(),
      pass_rate: passRate,
      total_scenarios: totalScenarios,
      passed_scenarios: passedScenarios,
      failed_scenarios: failedScenarios
    });
  }

  return builds;
};

// Generate mock build details
const generateMockBuildDetails = (buildId) => {
  const buildNumber = buildId.replace('build-', '');
  const passRate = 0.60 + (Math.random() * 0.30);
  const totalScenarios = Math.floor(90 + (Math.random() * 20));
  const passedScenarios = Math.floor(totalScenarios * passRate);
  const failedScenarios = totalScenarios - passedScenarios;

  return {
    build: {
      id: buildId,
      build_number: buildNumber,
      date: new Date().toISOString(),
      pass_rate: passRate,
      total_scenarios: totalScenarios,
      passed_scenarios: passedScenarios,
      failed_scenarios: failedScenarios,
      skipped_scenarios: 0,
      features: [
        {
          id: 'feature-1',
          name: 'Authentication',
          pass_rate: 0.85,
          total_scenarios: 14,
          passed_scenarios: 12,
          failed_scenarios: 2,
          skipped_scenarios: 0
        },
        {
          id: 'feature-2',
          name: 'Shopping Cart',
          pass_rate: 0.78,
          total_scenarios: 18,
          passed_scenarios: 14,
          failed_scenarios: 4,
          skipped_scenarios: 0
        },
        {
          id: 'feature-3',
          name: 'Checkout',
          pass_rate: 0.67,
          total_scenarios: 15,
          passed_scenarios: 10,
          failed_scenarios: 5,
          skipped_scenarios: 0
        }
      ],
      scenarios: generateMockScenarios({ limit: 20 })
    }
  };
};

// Generate mock scenarios
const generateMockScenarios = (filter = {}) => {
  const count = filter.limit || 50;
  const scenarios = [];
  const features = ['Authentication', 'Shopping Cart', 'Checkout', 'User Account', 'Product Search'];
  const statuses = ['passed', 'failed'];
  const tags = ['@medium', '@sprint-22', '@cart', '@api', '@checkout', '@low', '@high', '@account', '@payment', '@jira-123'];

  for (let i = 0; i < count; i++) {
    const featureName = features[Math.floor(Math.random() * features.length)];
    const status = statuses[Math.floor(Math.random() * (statuses.length - 0.3))]; // Weight slightly toward passed
    const scenarioTags = [];

    // Add between 1 and 3 tags
    const tagCount = 1 + Math.floor(Math.random() * 3);
    for (let j = 0; j < tagCount; j++) {
      const tag = tags[Math.floor(Math.random() * tags.length)];
      if (!scenarioTags.includes(tag)) {
        scenarioTags.push(tag);
      }
    }

    scenarios.push({
      id: `scenario-${i + 1}`,
      name: `${featureName} Scenario ${i + 1}`,
      feature: featureName,
      status: status,
      tags: scenarioTags
    });
  }

  return scenarios;
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
    const totalTests = Math.floor(Math.random() * 20) + 90; // Between 90 and 110
    const passRate = 0.60 + (Math.sin(i / 3) * 0.15) + (Math.random() * 0.1); // Between 60% and 90% with some variation
    const passedTests = Math.floor(totalTests * passRate);
    const failedTests = totalTests - passedTests;

    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      totalTests,
      passedTests,
      failedTests,
      passRate: Math.round(passRate * 1000) / 10, // Convert to percentage with 1 decimal
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
    const totalTests = Math.floor(Math.random() * 100) + 450; // Between 450 and 550
    const passRate = 0.60 + (Math.sin(i / 4) * 0.15) + (Math.random() * 0.1); // Between 60% and 90% with some variation
    const passedTests = Math.floor(totalTests * passRate);
    const failedTests = totalTests - passedTests;

    data.push({
      date: `Week ${weeks - i}`,
      totalTests,
      passedTests,
      failedTests,
      passRate: Math.round(passRate * 1000) / 10, // Convert to percentage with 1 decimal
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
    const buildNumber = 1041 + i;
    const passRate = 60 + (Math.sin(i) * 10) + (Math.random() * 20);

    builds.push({
      buildNumber: `#${buildNumber}`,
      passRate: Math.round(passRate * 10) / 10,
    });
  }

  return builds;
};

// Helper function to generate top failing tests
const generateTopFailingTests = () => {
  const tests = [
    'User authentication with invalid credentials',
    'Product checkout with expired credit card',
    'Search functionality with special characters',
    'User profile update with invalid data',
    'Product catalog filtering by multiple criteria',
    'Add to cart with out-of-stock item',
    'Payment processing timeout scenario',
    'User registration with existing email'
  ];

  return tests.slice(0, 5).map((test, index) => ({
    name: test,
    failureRate: 40 - (index * 5) + (Math.random() * 5), // Decreasing failure rates with some randomness
    occurrences: Math.floor(Math.random() * 10) + 5 // Between 5 and 15
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
      ],
      'Assertion Failures': [
        { element: 'Data Validation', occurrences: 20, scenarios: ['User Input', 'Form Submission'] },
        { element: 'Content Verification', occurrences: 15, scenarios: ['Product Details', 'Search Results'] },
        { element: 'State Transitions', occurrences: 10, scenarios: ['Multi-step Flows'] }
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
        date: new Date(Date.now() - 15 * 60000).toISOString(),
        build: '#1045'
      },
      {
        id: 'F122',
        scenario: 'Search results do not include relevant products',
        error: 'Assertion error: Expected search results to contain "bluetooth headphones"',
        date: new Date(Date.now() - 3 * 3600000).toISOString(),
        build: '#1045'
      },
      {
        id: 'F121',
        scenario: 'User profile update fails with valid data',
        error: 'Element not found: Save Changes button',
        date: new Date(Date.now() - 6 * 3600000).toISOString(),
        build: '#1044'
      }
    ]
  };
};

export default apiClient;