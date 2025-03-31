// src/services/apiAdapter.js

/**
 * Adapts the API response to the format expected by the dashboard components
 */
export const adaptTestStats = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.statistics) {
    return {
      passRate: 0,
      totalTests: 0,
      passedTests: 0,
      failedTests: 0,
      buildCount: 0,
      lastBuild: null,
      tags: []
    };
  }

  const stats = apiResponse.statistics;

  // Transform the API response to the expected format
  return {
    passRate: stats.pass_rate ? Math.round(stats.pass_rate * 100 * 10) / 10 : 0, // Convert to percentage with 1 decimal
    totalTests: stats.total_scenarios || 0,
    passedTests: stats.passed_scenarios || 0,
    failedTests: stats.failed_scenarios || 0,
    buildCount: stats.unique_builds || 0,
    lastBuild: null, // API doesn't seem to provide this
    tags: Object.entries(stats.top_tags || {}).map(([name, count]) => ({
      name,
      count
    }))
  };
};

/**
 * Adapts the API health response
 */
export const adaptHealthCheck = (apiResponse) => {
  return {
    isConnected: apiResponse?.status === "success",
    error: apiResponse?.status !== "success" ? "API is not responding correctly" : null
  };
};

/**
 * Adapts the detailed test results for the TestResultsDashboard
 */
export const adaptTestResults = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.results) {
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

  const results = apiResponse.results;

  // Extract feature results if available
  const featureResults = (results.features || []).map(feature => {
    return {
      name: feature.name || 'Unknown',
      passed: feature.passed_scenarios || 0,
      failed: feature.failed_scenarios || 0,
      skipped: feature.skipped_scenarios || 0
    };
  });

  // Extract tag data if available
  const tags = Object.entries(results.tags || {}).map(([name, data]) => {
    return {
      name,
      count: data.count || 0,
      passRate: data.pass_rate ? Math.round(data.pass_rate * 100 * 10) / 10 : 0
    };
  });

  return {
    totalTests: results.total_scenarios || 0,
    passedTests: results.passed_scenarios || 0,
    failedTests: results.failed_scenarios || 0,
    skippedTests: results.skipped_scenarios || 0,
    passRate: results.pass_rate ? Math.round(results.pass_rate * 100 * 10) / 10 : 0,
    lastUpdated: results.last_updated || new Date().toISOString(),
    featureResults,
    tags
  };
};

/**
 * Adapts the API test trends data
 */
export const adaptTestTrends = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.trends) {
    return {
      dailyTrends: [],
      buildComparison: [],
      topFailingTests: []
    };
  }

  const trends = apiResponse.trends;

  // Process daily trends
  const dailyTrends = (trends.daily || []).map(day => ({
    date: day.date,
    totalTests: day.total_scenarios || 0,
    passedTests: day.passed_scenarios || 0,
    failedTests: day.failed_scenarios || 0,
    passRate: day.pass_rate ? Math.round(day.pass_rate * 100 * 10) / 10 : 0
  }));

  // Process build comparisons
  const buildComparison = (trends.builds || []).map(build => ({
    buildNumber: build.build_number || build.id || 'Unknown',
    passRate: build.pass_rate ? Math.round(build.pass_rate * 100 * 10) / 10 : 0
  }));

  // Process failing tests
  const topFailingTests = (trends.top_failures || []).map(failure => ({
    name: failure.name || failure.scenario || 'Unknown',
    failureRate: failure.failure_rate ? Math.round(failure.failure_rate * 100 * 10) / 10 : 0,
    occurrences: failure.occurrences || 0
  }));

  return {
    dailyTrends,
    buildComparison,
    topFailingTests
  };
};

/**
 * Adapts the API failure analysis data
 */
export const adaptFailureAnalysis = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.failures) {
    return {
      failureCategories: [],
      failureDetails: {},
      failuresByFeature: [],
      recentFailures: []
    };
  }

  const failures = apiResponse.failures;

  // Process failure categories
  const failureCategories = (failures.categories || []).map(category => {
    const percentage = category.percentage || (category.count / failures.total_failures * 100);
    return {
      name: category.name || 'Unknown',
      value: category.count || 0,
      percentage: Math.round(percentage * 10) / 10
    };
  });

  // Process failure details
  const failureDetails = {};
  Object.entries(failures.details || {}).forEach(([category, details]) => {
    failureDetails[category] = details.map(detail => ({
      element: detail.element || detail.name || 'Unknown',
      occurrences: detail.occurrences || 0,
      scenarios: detail.scenarios || []
    }));
  });

  // Process failures by feature
  const failuresByFeature = (failures.by_feature || []).map(feature => {
    const total = feature.total_tests || feature.total_scenarios || 0;
    const failedTests = feature.failures || feature.failed_scenarios || 0;
    const failureRate = feature.failure_rate || (total > 0 ? failedTests / total * 100 : 0);

    return {
      feature: feature.name || 'Unknown',
      failures: failedTests,
      tests: total,
      failureRate: Math.round(failureRate * 10) / 10
    };
  });

  // Process recent failures
  const recentFailures = (failures.recent || []).map(failure => ({
    id: failure.id || `F${Math.floor(Math.random() * 1000)}`,
    scenario: failure.scenario || 'Unknown scenario',
    error: failure.error || failure.message || 'Unknown error',
    date: failure.date || failure.timestamp || new Date().toISOString(),
    build: failure.build || 'Unknown'
  }));

  return {
    failureCategories,
    failureDetails,
    failuresByFeature,
    recentFailures
  };
};

/**
 * Adapts the API query response
 */
export const adaptQueryResults = (apiResponse) => {
  // Implement when you have the actual API response format for queries
  return {
    answer: apiResponse?.result || "No answer available",
    sources: [],
    relatedQueries: []
  };
};