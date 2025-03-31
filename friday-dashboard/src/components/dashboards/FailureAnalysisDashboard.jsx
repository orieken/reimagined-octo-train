// src/components/dashboards/FailureAnalysisDashboard.jsx
import React, { useState, useEffect } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import { getFailureAnalysis } from '@services/api.js';


const FailureAnalysisDashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [failureData, setFailureData] = useState(null);
  const [selectedFailure, setSelectedFailure] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Load failure analysis data
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const data = await getFailureAnalysis();
        setFailureData(data);

        if (data.failureCategories && data.failureCategories.length > 0) {
          setSelectedFailure(data.failureCategories[0].name);
        }

      } catch (err) {
        console.error('Error loading failure analysis:', err);
        setError('Failed to load failure analysis. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Helper function to format date for display
  const formatTimeStamp = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
      // eslint-disable-next-line no-unused-vars
    } catch (error) {
      return dateString || 'Unknown date';
    }
  };

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

  if (!failureData) {
    return (
      <div className="bg-secondary-light text-secondary-dark border border-secondary rounded-md p-4 mb-6">
        No failure analysis data available.
      </div>
    );
  }

  const COLORS = ['#F56565', '#ED8936', '#ECC94B', '#48BB78', '#4299E1', '#A0AEC0'];

  const selectedFailureDetails = selectedFailure && failureData.failureDetails
    ? (failureData.failureDetails[selectedFailure] || [])
    : [];

  return (
    <div className="space-y-6">
      {/* Failure Categories Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-1">
          <h2 className="text-xl font-semibold mb-4">Failure Categories</h2>
          <div className="h-80">
            {failureData.failureCategories && failureData.failureCategories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={failureData.failureCategories}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percentage }) => `${name}: ${percentage}%`}
                  >
                    {failureData.failureCategories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, name, props) => [
                      `${value} occurrences (${props.payload.percentage}%)`,
                      name
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full justify-center items-center text-secondary">
                No failure category data available
              </div>
            )}
          </div>
        </div>

        <div className="card lg:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Failures by Feature</h2>
          <div className="h-80">
            {failureData.failuresByFeature && failureData.failuresByFeature.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={failureData.failuresByFeature}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="feature" />
                  <YAxis yAxisId="left" orientation="left" stroke="#F56565" />
                  <YAxis yAxisId="right" orientation="right" stroke="#4299E1" />
                  <Tooltip />
                  <Legend />
                  <Bar
                    yAxisId="left"
                    dataKey="failures"
                    name="Failures"
                    fill="#F56565"
                  />
                  <Bar
                    yAxisId="right"
                    dataKey="failureRate"
                    name="Failure Rate (%)"
                    fill="#4299E1"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full justify-center items-center text-secondary">
                No feature failure data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Failure Details */}
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
          <h2 className="text-xl font-semibold">Failure Details</h2>

          <div className="mt-2 md:mt-0">
            {failureData.failureCategories && failureData.failureCategories.length > 0 ? (
              <select
                className="form-input"
                value={selectedFailure || ''}
                onChange={(e) => setSelectedFailure(e.target.value)}
              >
                {failureData.failureCategories.map((category, index) => (
                  <option key={index} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-secondary">No categories available</span>
            )}
          </div>
        </div>

        {selectedFailureDetails.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-secondary-light">
              <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Element / Issue
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Occurrences
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary uppercase tracking-wider">
                  Affected Scenarios
                </th>
              </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-light">
              {selectedFailureDetails.map((detail, index) => (
                <tr key={index} className="hover:bg-secondary-light">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {detail.element}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {detail.occurrences}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {detail.scenarios && detail.scenarios.length > 0 ? detail.scenarios.join(', ') : 'N/A'}
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-secondary p-4 bg-secondary-light rounded-md">
            No details available for this failure category.
          </div>
        )}
      </div>

      {/* Recent Failures */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Recent Failures</h2>
        {failureData.recentFailures && failureData.recentFailures.length > 0 ? (
          <div className="space-y-4">
            {failureData.recentFailures.map((failure, index) => (
              <div key={index} className="p-4 bg-secondary-light rounded-md">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center">
                    <span className="font-bold mr-2">{failure.id}</span>
                    <span className="text-xs bg-danger text-white px-2 py-1 rounded">
                      Build {failure.build}
                    </span>
                  </div>
                  <div className="text-xs text-secondary mt-1 md:mt-0">
                    {formatTimeStamp(failure.date)}
                  </div>
                </div>
                <p className="font-medium mt-2">{failure.scenario}</p>
                <p className="text-danger mt-1 text-sm">{failure.error}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-secondary p-4 bg-secondary-light rounded-md">
            No recent failures available.
          </div>
        )}
        <div className="mt-4 flex justify-center">
          <button className="btn btn-secondary">
            View All Failures
          </button>
        </div>
      </div>
    </div>
  );
};

export default FailureAnalysisDashboard;