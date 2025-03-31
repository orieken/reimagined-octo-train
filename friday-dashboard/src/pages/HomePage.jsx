// src/pages/HomePage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTestStats } from '../services/api';

const HomePage = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    passRate: 0,
    totalTests: 0,
    passedTests: 0,
    failedTests: 0,
    buildCount: 0,
    lastBuild: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await getTestStats();
        console.log('API Response:', data); // Debug log to see the actual API response

        // Process the data to handle different API response structures
        // Adjust this section based on your actual API response structure
        const processedStats = {
          passRate: typeof data?.passRate === 'number' ? data.passRate : 0,
          totalTests: typeof data?.totalTests === 'number' ? data.totalTests : 0,
          passedTests: typeof data?.passedTests === 'number' ? data.passedTests : 0,
          failedTests: typeof data?.failedTests === 'number' ? data.failedTests : 0,
          buildCount: typeof data?.buildCount === 'number' ? data.buildCount : 0,
          lastBuild: data?.lastBuild || null,
        };

        setStats(processedStats);
        setError(null);
      } catch (err) {
        console.error('Error details:', err);
        setError('Failed to load test statistics. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const StatCard = ({ title, value, icon, color, onClick }) => (
    <div
      className={`bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer border-l-4 ${color}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-secondary mb-1">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <div className={`p-3 rounded-full bg-opacity-10 ${color.replace('border', 'bg')}`}>
          {icon}
        </div>
      </div>
    </div>
  );

  // Safely format pass rate with fallback
  const formatPassRate = (rate) => {
    console.log('Formatting pass rate:', rate); // Debug log to see the value being formatted
    if (typeof rate !== 'number') return '0.0%';
    return `${rate.toFixed(1)}%`;
  };

  // Safely format numbers with fallback
  const formatNumber = (num) => {
    console.log('Formatting number:', num); // Debug log to see the value being formatted
    if (typeof num !== 'number') return '0';
    return num.toLocaleString();
  };

  return (
    <div className="py-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Dashboard Overview</h1>
        <div>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/query')}
          >
            Query Test Data
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      ) : error ? (
        <div className="bg-danger-light text-danger border border-danger rounded-md p-4 mb-6">
          {error}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Pass Rate"
            value={formatPassRate(stats.passRate)}
            icon={
              <svg className="w-6 h-6 text-success" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            color="border-success"
            onClick={() => navigate('/test-results')}
          />
          <StatCard
            title="Total Tests"
            value={formatNumber(stats.totalTests)}
            icon={
              <svg className="w-6 h-6 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
              </svg>
            }
            color="border-primary"
            onClick={() => navigate('/test-results')}
          />
          <StatCard
            title="Passed Tests"
            value={formatNumber(stats.passedTests)}
            icon={
              <svg className="w-6 h-6 text-success" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            }
            color="border-success"
            onClick={() => navigate('/test-results')}
          />
          <StatCard
            title="Failed Tests"
            value={formatNumber(stats.failedTests)}
            icon={
              <svg className="w-6 h-6 text-danger" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            }
            color="border-danger"
            onClick={() => navigate('/test-results')}
          />
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
          <p className="text-secondary">
            This section will display recent test runs and activity.
          </p>
          {/* We'll implement this with real data later */}
          <div className="mt-4 flex justify-center">
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/test-results')}
            >
              View All Test Results
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="space-y-4">
            <div className="flex flex-col space-y-2">
              <button
                className="btn btn-primary flex items-center justify-center"
                onClick={() => navigate('/query')}
              >
                <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Query Test Data
              </button>
              <button
                className="btn btn-secondary flex items-center justify-center"
                onClick={() => navigate('/test-results')}
              >
                <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                View All Test Results
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;