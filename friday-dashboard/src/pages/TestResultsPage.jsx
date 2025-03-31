// src/pages/TestResultsPage.jsx
import React, { useState } from 'react';
import TestResultsDashboard from '../components/dashboards/TestResultsDashboard';
import TestTrendsDashboard from '../components/dashboards/TestTrendsDashboard';
import FailureAnalysisDashboard from '../components/dashboards/FailureAnalysisDashboard';

const TestResultsPage = () => {
  const [activeTab, setActiveTab] = useState('results');

  return (
    <div className="py-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Test Results</h1>
        <div>
          <button className="btn btn-primary">
            Upload Test Results
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-secondary">
        <nav className="flex -mb-px">
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'results'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('results')}
          >
            Test Results
          </button>
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'trends'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('trends')}
          >
            Test Trends
          </button>
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'failures'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('failures')}
          >
            Failure Analysis
          </button>
        </nav>
      </div>

      {/* Dashboard content based on active tab */}
      <div className="mt-4">
        {activeTab === 'results' && <TestResultsDashboard />}
        {activeTab === 'trends' && <TestTrendsDashboard />}
        {activeTab === 'failures' && <FailureAnalysisDashboard />}
      </div>
    </div>
  );
};

export default TestResultsPage;