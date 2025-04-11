// src/components/query/QueryForm.jsx
import React, { useState } from 'react';
import PropTypes from 'prop-types';

const QueryForm = ({ onSubmit, isLoading }) => {
  const [queryText, setQueryText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (queryText.trim() && !isLoading) {
      onSubmit(queryText);
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter key
    if (e.key === 'Enter' && queryText.trim() && !isLoading) {
      onSubmit(queryText);
    }
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="mb-2">
        <div className="flex flex-col">
          <label htmlFor="query" className="text-lg font-medium mb-2">
            Ask a question about your test data
          </label>
          <div className="flex w-full relative">
            <input
              type="text"
              id="query"
              className="form-input flex-grow mr-2 py-2 px-4 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., What was the pass rate for login tests in the last build?"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              autoComplete="off"
              autoFocus
            />
            <button
              type="submit"
              className={`btn ${
                isLoading ? 'btn-secondary opacity-70' : 'btn-primary'
              } flex items-center justify-center px-4 py-2 rounded-lg`}
              disabled={!queryText.trim() || isLoading}
            >
              {isLoading ? (
                <svg className="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              ) : (
                <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              )}
              {isLoading ? 'Analyzing...' : 'Ask'}
            </button>
          </div>
        </div>
      </form>

      <div className="text-xs text-gray-500 mt-1">
        Try asking about test pass rates, failures, trends, or specific features.
      </div>
    </div>
  );
};

QueryForm.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  isLoading: PropTypes.bool
};

QueryForm.defaultProps = {
  isLoading: false
};

export default QueryForm;