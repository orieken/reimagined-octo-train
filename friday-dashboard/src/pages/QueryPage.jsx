// src/pages/QueryPage.jsx
import React, { useState, useEffect } from 'react';
import QueryForm from '../components/query/QueryForm';
import QueryResults from '../components/query/QueryResults';
import QueryVisualization from '../components/query/QueryVisualization';
import MockToggle from '../components/query/MockToggle';
import { isUsingMockData, forceRealData } from '../services/api';
import { queryTestData } from '../services/queryService';

const QueryPage = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showExamples, setShowExamples] = useState(true);
  const [usingMockData, setUsingMockData] = useState(false);
  const [suggestedQueries, setSuggestedQueries] = useState([
    'What was the pass rate for authentication tests in the last build?',
    'Show me the most common failures in the login feature',
    'What are the trends for checkout tests over the last month?',
    'Which test scenarios have the highest failure rate?'
  ]);

  // Handle query submission
  const handleSubmitQuery = async (queryText) => {
    setQuery(queryText);
    setLoading(true);
    setError(null);
    setShowExamples(false);

    try {
      // Make sure to force a real API call by turning off mock data
      // if it was previously enabled
      window.localStorage.setItem('forceMockData', 'false');

      console.log(`Querying test data with: "${queryText}"`);
      const response = await queryTestData(queryText);
      console.log('Query response:', response);

      setResults(response);
      setUsingMockData(isUsingMockData());

      // If we got related queries, update our suggested queries for next time
      if (response.relatedQueries && response.relatedQueries.length > 0) {
        setSuggestedQueries(response.relatedQueries);
      }
    } catch (err) {
      console.error('Error querying test data:', err);
      setError(
        err.response?.data?.message ||
        'Failed to process your query. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  // Reset the query and show examples again
  const handleReset = () => {
    setQuery('');
    setResults(null);
    setError(null);
    setShowExamples(true);
  };

  return (
    <div className="py-6 px-4 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Query Test Data</h1>
        <p className="text-gray-600 mt-2">
          Ask questions about your test results in natural language and get insights instantly.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <MockToggle onChange={(useMock) => {
          setUsingMockData(useMock);
          if (!useMock) {
            forceRealData();
          }
        }} />
        <QueryForm onSubmit={handleSubmitQuery} isLoading={loading} />
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">Analyzing your query...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-start">
            <svg className="w-5 h-5 mr-2 mt-0.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="font-medium">Error</h3>
              <p className="mt-1">{error}</p>
              <button
                className="mt-3 text-sm text-blue-600 hover:text-blue-800"
                onClick={handleReset}
              >
                Try another query
              </button>
            </div>
          </div>
        </div>
      ) : results ? (
        <div>
          {usingMockData && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 text-sm text-yellow-800">
              <div className="flex items-center">
                <svg className="w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p>Using mock data - the query API is working but returning simulated responses.</p>
              </div>
            </div>
          )}

          <QueryResults
            results={results}
            onFollowupQuery={handleSubmitQuery}
            currentQuery={query}
          />

          {/* If the response includes chart data, render visualization */}
          {results.chartData && (
            <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <QueryVisualization chartData={results.chartData} />
            </div>
          )}

          <div className="mt-8 text-center">
            <button
              className="text-blue-600 hover:text-blue-800 font-medium"
              onClick={handleReset}
            >
              Ask another question
            </button>
          </div>
        </div>
      ) : showExamples ? (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-semibold mb-4">Example Queries</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suggestedQueries.map((exampleQuery, index) => (
              <div
                key={index}
                className="p-4 bg-white rounded-md shadow cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => handleSubmitQuery(exampleQuery)}
              >
                <p>{exampleQuery}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default QueryPage;