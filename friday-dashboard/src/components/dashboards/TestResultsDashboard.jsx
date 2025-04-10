// src/components/dashboards/TestResultsDashboard.jsx
import React, { useState, useEffect } from 'react';
import PassRateChart from '../charts/PassRateChart';
import TagsBarChart from '../charts/TagsBarChart';
import { getDetailedTestResults } from '@services/api.js';
import { formatDate } from '@utils/formatters.js';
import TestResultsPieChart from '@components/charts/TotalResultsPieChart.jsx';


const TestResultsDashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [testData, setTestData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const data = await getDetailedTestResults();
        setTestData(data);

      } catch (err) {
        console.error('Error loading test results:', err);
        setError('Failed to load test results. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-danger-light text-danger border border-danger rounded-md p-4 mb-6">
        {error}
      </div>
    );
  }

  if (!testData) {
    return (
      <div className="bg-secondary-light text-secondary-dark border border-secondary rounded-md p-4 mb-6">
        No test data available.
      </div>
    );
  }

  const skippedTests = testData.skippedTests || testData.featureResults?.reduce((sum, feature) => sum + (feature.skipped || 0), 0) || 0;
  console.log('Skipped Tests:', skippedTests);
  console.log('test data by tags', testData.tags);

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-white">
          <h3 className="text-secondary mb-1 text-sm font-medium">Total Tests</h3>
          <p className="text-2xl font-bold">{testData.totalTests}</p>
        </div>
        <div className="card bg-white">
          <h3 className="text-secondary mb-1 text-sm font-medium">Passed Tests</h3>
          <p className="text-2xl font-bold text-success">{testData.passedTests}</p>
        </div>
        <div className="card bg-white">
          <h3 className="text-secondary mb-1 text-sm font-medium">Failed Tests</h3>
          <p className="text-2xl font-bold text-danger">{testData.failedTests}</p>
        </div>
        <div className="card bg-white">
          <h3 className="text-secondary mb-1 text-sm font-medium">Pass Rate</h3>
          <p className="text-2xl font-bold">{testData.passRate}%</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Test Results by Status</h2>
          <div className="h-80">
            <TestResultsPieChart
              passed={testData.passedTests}
              failed={testData.failedTests}
              skipped={skippedTests}
            />
          </div>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Pass Rate by Feature</h2>
          <div className="h-80">
            {testData.featureResults && testData.featureResults.length > 0 ? (
              <PassRateChart features={testData.featureResults} />
            ) : (
              <div className="flex h-full justify-center items-center text-secondary">
                No feature data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tag Distribution */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Test Distribution by Tag</h2>
        <div className="h-80">
          {testData.tags && testData.tags.length > 0 ? (
            <TagsBarChart tags={testData.tags} />
          ) : (
            <div className="flex h-full justify-center items-center text-secondary">
              No tag data available
            </div>
          )}
        </div>
      </div>

      {/* Feature Results Table */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Feature Results</h2>
        {testData.featureResults && testData.featureResults.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-secondary-light">
              <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Feature
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Total
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Passed
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Failed
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Skipped
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Pass Rate
                </th>
              </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-light">
              {testData.featureResults.map((feature, index) => {
                const total = feature.passed + feature.failed + (feature.skipped || 0);
                const passRate = total > 0 ? (feature.passed / total * 100).toFixed(1) : '0.0';

                return (
                  <tr key={index} className="hover:bg-secondary-light">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {feature.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {total}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-success">
                      {feature.passed}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-danger">
                      {feature.failed}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-warning">
                      {feature.skipped || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center">
                        <span className="mr-2">{passRate}%</span>
                        <div className="w-24 bg-secondary-light rounded-full h-2.5">
                          <div
                            className={`h-2.5 rounded-full ${passRate >= 80 ? 'bg-success' : passRate >= 60 ? 'bg-warning' : 'bg-danger'}`}
                            style={{ width: `${passRate}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-secondary p-4 bg-secondary-light rounded-md">
            No feature data available.
          </div>
        )}
      </div>

      <div className="text-xs text-secondary text-right">
        Last updated: {formatDate(testData.lastUpdated)}
      </div>
    </div>
  );
};

export default TestResultsDashboard;