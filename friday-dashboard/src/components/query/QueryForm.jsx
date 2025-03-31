// src/components/query/QueryForm.jsx
import React, { useState } from 'react';

const QueryForm = ({ onSubmit }) => {
  const [queryText, setQueryText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (queryText.trim()) {
      onSubmit(queryText);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex flex-col">
        <label htmlFor="query" className="text-lg font-medium mb-2">
          Ask a question about your test data
        </label>
        <div className="flex w-full">
          <input
            type="text"
            id="query"
            className="form-input flex-grow mr-2"
            placeholder="e.g., What was the pass rate for login tests in the last build?"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            autoComplete="off"
          />
          <button
            type="submit"
            className="btn btn-primary flex items-center justify-center"
            disabled={!queryText.trim()}
          >
            <svg className="w-5 h-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Ask
          </button>
        </div>
      </div>
    </form>
  );
};

export default QueryForm;