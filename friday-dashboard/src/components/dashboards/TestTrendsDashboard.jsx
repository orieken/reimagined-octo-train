// src/components/dashboards/TestTrendsDashboard.jsx
import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts';
import { getTestTrends } from '@services/api.js';

const TestTrendsDashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [trendData, setTrendData] = useState(null);
  const [timeRange, setTimeRange] = useState('week');
  const [error, setError] = useState(null);

  useEffect(() => {
    // Load trend data
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const data = await getTestTrends(timeRange);
        setTrendData(data);

      } catch (err) {
        console.error('Error loading test trends:', err);
        setError('Failed to load test trends. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [timeRange]);

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

  if (!trendData) {
    return (
      <div className="bg-secondary-light text-secondary-dark border border-secondary rounded-md p-4 mb-6">
        No trend data available.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="card flex items-center justify-between">
        <h2 className="text-xl font-semibold">Test Trends</h2>
        <div className="inline-flex rounded-md shadow-sm" role="group">
          <button
            type="button"
            className={`py-2 px-4 text-sm font-medium rounded-l-lg ${
              timeRange === 'week'
                ? 'bg-primary text-white'
                : 'bg-white text-secondary-dark hover:bg-secondary-light'
            }`}
            onClick={() => setTimeRange('week')}
          >
            Last Week
          </button>
          <button
            type="button"
            className={`py-2 px-4 text-sm font-medium ${
              timeRange === 'month'
                ? 'bg-primary text-white'
                : 'bg-white text-secondary-dark hover:bg-secondary-light'
            }`}
            onClick={() => setTimeRange('month')}
          >
            Last Month
          </button>
          <button
            type="button"
            className={`py-2 px-4 text-sm font-medium rounded-r-lg ${
              timeRange === 'quarter'
                ? 'bg-primary text-white'
                : 'bg-white text-secondary-dark hover:bg-secondary-light'
            }`}
            onClick={() => setTimeRange('quarter')}
          >
            Last Quarter
          </button>
        </div>
      </div>

      {/* Pass Rate Trend */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Pass Rate Trend</h2>
        <div className="h-80">
          {trendData.dailyTrends && trendData.dailyTrends.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={trendData.dailyTrends}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="passRate"
                  stroke="#48BB78"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Pass Rate (%)"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full justify-center items-center text-secondary">
              No pass rate trend data available
            </div>
          )}
        </div>
      </div>

      {/* Test Volume Trend */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Test Volume</h2>
        <div className="h-80">
          {trendData.dailyTrends && trendData.dailyTrends.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={trendData.dailyTrends}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                stackOffset="sign"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="passedTests" name="Passed Tests" stackId="a" fill="#48BB78" />
                <Bar dataKey="failedTests" name="Failed Tests" stackId="a" fill="#F56565" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full justify-center items-center text-secondary">
              No test volume data available
            </div>
          )}
        </div>
      </div>

      {/* Build-to-Build Comparison */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Build Comparison</h2>
        <div className="h-64">
          {trendData.buildComparison && trendData.buildComparison.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={trendData.buildComparison}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis dataKey="buildNumber" type="category" />
                <Tooltip />
                <Legend />
                <Bar
                  dataKey="passRate"
                  name="Pass Rate (%)"
                  fill="#3182CE"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full justify-center items-center text-secondary">
              No build comparison data available
            </div>
          )}
        </div>
      </div>

      {/* Top Failing Tests */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Top Failing Tests</h2>
        {trendData.topFailingTests && trendData.topFailingTests.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-secondary-light">
              <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Test Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Failure Rate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Occurrences
                </th>
              </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-light">
              {trendData.topFailingTests.map((test, index) => (
                <tr key={index} className="hover:bg-secondary-light">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {test.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center">
                      <span className="mr-2">{test.failureRate}%</span>
                      <div className="w-24 bg-secondary-light rounded-full h-2.5">
                        <div
                          className="h-2.5 rounded-full bg-danger"
                          style={{ width: `${test.failureRate}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {test.occurrences}
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-secondary p-4 bg-secondary-light rounded-md">
            No failing test data available.
          </div>
        )}
      </div>
    </div>
  );
};

export default TestTrendsDashboard;