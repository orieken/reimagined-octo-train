// src/components/query/QueryResults.jsx
import React from 'react';
import PropTypes from 'prop-types';

const QueryResults = ({ results, onFollowupQuery, currentQuery }) => {
  if (!results) return null;

  return (
    <div className="space-y-6">
      {/* Query Info */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Results for: <span className="text-blue-600">{currentQuery}</span></h2>

        {/* Copy button */}
        <button
          onClick={() => {
            navigator.clipboard.writeText(results.answer);
            // Could add a toast notification here
            alert('Answer copied to clipboard');
          }}
          className="text-sm text-gray-500 hover:text-gray-700 flex items-center"
        >
          <svg className="w-4 h-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          Copy
        </button>
      </div>

      {/* Answer Section */}
      <div className="card bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-lg font-semibold mb-3">Answer</h3>
        <p className="text-gray-800 whitespace-pre-line">{results.answer}</p>
      </div>

      {/* Sources Section */}
      {results.sources && results.sources.length > 0 && (
        <div className="card bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold mb-3">Sources</h3>
          <div className="space-y-2">
            {results.sources.map((source, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                <span className="font-medium">{source.title}</span>
                <span className="text-sm text-gray-600 bg-white px-2 py-1 rounded-full border border-gray-200">
                  {(source.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Queries */}
      {results.relatedQueries && results.relatedQueries.length > 0 && (
        <div className="card bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="text-lg font-semibold mb-3">Follow-up Questions</h3>
          <div className="space-y-2">
            {results.relatedQueries.map((query, index) => (
              <div
                key={index}
                className="p-3 bg-gray-50 rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 transition-colors"
                onClick={() => onFollowupQuery(query)}
              >
                <div className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {query}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

QueryResults.propTypes = {
  results: PropTypes.shape({
    answer: PropTypes.string.isRequired,
    sources: PropTypes.arrayOf(
      PropTypes.shape({
        title: PropTypes.string.isRequired,
        confidence: PropTypes.number.isRequired
      })
    ),
    relatedQueries: PropTypes.arrayOf(PropTypes.string),
    chartData: PropTypes.object
  }),
  onFollowupQuery: PropTypes.func.isRequired,
  currentQuery: PropTypes.string.isRequired
};

export default QueryResults;