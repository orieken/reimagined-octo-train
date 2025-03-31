// src/components/query/QueryResults.jsx
import React from 'react';

const QueryResults = ({ results, onFollowupQuery }) => {
  if (!results) return null;

  return (
    <div className="space-y-6">
      {/* Answer Section */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Answer</h2>
        <p className="text-secondary-dark">{results.answer}</p>
      </div>

      {/* Sources Section */}
      {results.sources && results.sources.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Sources</h2>
          <div className="space-y-2">
            {results.sources.map((source, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-secondary-light rounded-md">
                <span>{source.title}</span>
                <span className="text-sm text-secondary bg-white px-2 py-1 rounded-full">
                  {(source.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Queries */}
      {results.relatedQueries && results.relatedQueries.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">Related Questions</h2>
          <div className="space-y-2">
            {results.relatedQueries.map((query, index) => (
              <div
                key={index}
                className="p-3 bg-secondary-light rounded-md cursor-pointer hover:bg-secondary hover:text-white transition-colors"
                onClick={() => onFollowupQuery(query)}
              >
                {query}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryResults;