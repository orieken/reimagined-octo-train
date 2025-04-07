// src/services/apiAdapter.js

/**
 * Adapts the API response to the format expected by the dashboard components
 */
export const adaptTestStats = (apiResponse) => {
  if (!apiResponse) {
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

  const stats = apiResponse;

  // Transform the API response to the expected format
  return {
    passRate: stats.pass_rate || 0,
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
    isConnected: apiResponse?.status === "ok",
    error: apiResponse?.status !== "ok" ? "API is not responding correctly" : null
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
 * Adapts the API builds response
 */
export const adaptBuilds = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.builds) {
    return [];
  }

  return apiResponse.builds.map(build => ({
    id: build.id || '',
    buildNumber: build.build_number || build.number || 'Unknown',
    date: build.date || build.timestamp || null,
    passRate: build.pass_rate ? Math.round(build.pass_rate * 100 * 10) / 10 : 0,
    totalScenarios: build.total_scenarios || 0,
    passedScenarios: build.passed_scenarios || 0,
    failedScenarios: build.failed_scenarios || 0
  }));
};

/**
 * Adapts the API build details response
 */
export const adaptBuildDetails = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.build) {
    return {
      id: '',
      buildNumber: 'Unknown',
      date: null,
      passRate: 0,
      totalScenarios: 0,
      passedScenarios: 0,
      failedScenarios: 0,
      skippedScenarios: 0,
      features: [],
      scenarios: []
    };
  }

  const build = apiResponse.build;

  return {
    id: build.id || '',
    buildNumber: build.build_number || build.number || 'Unknown',
    date: build.date || build.timestamp || null,
    passRate: build.pass_rate ? Math.round(build.pass_rate * 100 * 10) / 10 : 0,
    totalScenarios: build.total_scenarios || 0,
    passedScenarios: build.passed_scenarios || 0,
    failedScenarios: build.failed_scenarios || 0,
    skippedScenarios: build.skipped_scenarios || 0,
    features: (build.features || []).map(feature => ({
      id: feature.id || '',
      name: feature.name || 'Unknown',
      passRate: feature.pass_rate ? Math.round(feature.pass_rate * 100 * 10) / 10 : 0,
      totalScenarios: feature.total_scenarios || 0,
      passedScenarios: feature.passed_scenarios || 0,
      failedScenarios: feature.failed_scenarios || 0,
      skippedScenarios: feature.skipped_scenarios || 0
    })),
    scenarios: (build.scenarios || []).map(scenario => ({
      id: scenario.id || '',
      name: scenario.name || 'Unknown',
      feature: scenario.feature || 'Unknown',
      status: scenario.status || 'unknown',
      tags: scenario.tags || []
    }))
  };
};

/**
 * Adapts the API scenarios response
 */
export const adaptScenarios = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.scenarios) {
    return [];
  }

  return apiResponse.scenarios.map(scenario => ({
    id: scenario.id || '',
    name: scenario.name || 'Unknown',
    feature: scenario.feature || 'Unknown',
    status: scenario.status || 'unknown',
    tags: scenario.tags || []
  }));
};

/**
 * Adapts the API scenario details response
 */
export const adaptScenarioDetails = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.scenario) {
    return {
      id: '',
      name: 'Unknown',
      feature: 'Unknown',
      status: 'unknown',
      tags: [],
      steps: [],
      builds: []
    };
  }

  const scenario = apiResponse.scenario;

  return {
    id: scenario.id || '',
    name: scenario.name || 'Unknown',
    feature: scenario.feature || 'Unknown',
    status: scenario.status || 'unknown',
    tags: scenario.tags || [],
    steps: (scenario.steps || []).map(step => ({
      id: step.id || '',
      keyword: step.keyword || '',
      name: step.name || '',
      status: step.status || 'unknown',
      error: step.error || null
    })),
    builds: (scenario.builds || []).map(build => ({
      id: build.id || '',
      buildNumber: build.build_number || build.number || 'Unknown',
      date: build.date || build.timestamp || null,
      status: build.status || 'unknown'
    }))
  };
};

/**
 * Adapts the API features response
 */
export const adaptFeatures = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.features) {
    return [];
  }

  return apiResponse.features.map(feature => ({
    id: feature.id || '',
    name: feature.name || 'Unknown',
    passRate: feature.pass_rate ? Math.round(feature.pass_rate * 100 * 10) / 10 : 0,
    totalScenarios: feature.total_scenarios || 0,
    passedScenarios: feature.passed_scenarios || 0,
    failedScenarios: feature.failed_scenarios || 0,
    skippedScenarios: feature.skipped_scenarios || 0
  }));
};

/**
 * Adapts the API feature details response
 */
export const adaptFeatureDetails = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.feature) {
    return {
      id: '',
      name: 'Unknown',
      passRate: 0,
      totalScenarios: 0,
      passedScenarios: 0,
      failedScenarios: 0,
      skippedScenarios: 0,
      scenarios: [],
      builds: []
    };
  }

  const feature = apiResponse.feature;

  return {
    id: feature.id || '',
    name: feature.name || 'Unknown',
    passRate: feature.pass_rate ? Math.round(feature.pass_rate * 100 * 10) / 10 : 0,
    totalScenarios: feature.total_scenarios || 0,
    passedScenarios: feature.passed_scenarios || 0,
    failedScenarios: feature.failed_scenarios || 0,
    skippedScenarios: feature.skipped_scenarios || 0,
    scenarios: (feature.scenarios || []).map(scenario => ({
      id: scenario.id || '',
      name: scenario.name || 'Unknown',
      status: scenario.status || 'unknown',
      tags: scenario.tags || []
    })),
    builds: (feature.builds || []).map(build => ({
      id: build.id || '',
      buildNumber: build.build_number || build.number || 'Unknown',
      date: build.date || build.timestamp || null,
      passRate: build.pass_rate ? Math.round(build.pass_rate * 100 * 10) / 10 : 0
    }))
  };
};

/**
 * Adapts the API tags response
 */
export const adaptTags = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.tags) {
    return [];
  }

  return apiResponse.tags.map(tag => ({
    name: tag.name || 'Unknown',
    count: tag.count || 0,
    passRate: tag.pass_rate ? Math.round(tag.pass_rate * 100 * 10) / 10 : 0
  }));
};

/**
 * Adapts the API tag details response
 */
export const adaptTagDetails = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse || !apiResponse.tag) {
    return {
      name: 'Unknown',
      count: 0,
      passRate: 0,
      scenarios: [],
      features: []
    };
  }

  const tag = apiResponse.tag;

  return {
    name: tag.name || 'Unknown',
    count: tag.count || 0,
    passRate: tag.pass_rate ? Math.round(tag.pass_rate * 100 * 10) / 10 : 0,
    scenarios: (tag.scenarios || []).map(scenario => ({
      id: scenario.id || '',
      name: scenario.name || 'Unknown',
      feature: scenario.feature || 'Unknown',
      status: scenario.status || 'unknown'
    })),
    features: (tag.features || []).map(feature => ({
      id: feature.id || '',
      name: feature.name || 'Unknown',
      passRate: feature.pass_rate ? Math.round(feature.pass_rate * 100 * 10) / 10 : 0,
      count: feature.count || 0
    }))
  };
};

/**
 * Adapts the API query response
 */
export const adaptQueryResults = (apiResponse) => {
  // Handle empty or invalid responses
  if (!apiResponse) {
    return {
      answer: "No answer available",
      sources: [],
      relatedQueries: []
    };
  }

  return {
    answer: apiResponse.answer || apiResponse.result || "No answer available",
    sources: (apiResponse.sources || []).map(source => ({
      title: source.title || source.name || 'Unknown',
      confidence: source.confidence || 0.5
    })),
    relatedQueries: apiResponse.related_queries || apiResponse.suggestions || []
  };
};
