// src/pages/QueryPage.jsx
import React from 'react';
import QueryForm from '../components/query/QueryForm';
import QueryResults from '../components/query/QueryResults';

const QueryPage = () => {
  const [query, setQuery] = React.useState('');
  const [results, setResults] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleSubmit = async (queryText) => {
    setQuery(queryText);
    setLoading(true);
    setError(null);

    try {
      // This would be replaced with an actual API call
      // const response = await queryTestData(queryText);

      // For now, we'll simulate a response
      await new Promise(resolve => setTimeout(resolve, 1000));
      const mockResults = {
        answer: 'This is a simulated answer to your query about test results.',
        sources: [
          { title: 'Test Run #123', confidence: 0.85 },
          { title: 'Feature: User Authentication', confidence: 0.72 }
        ],
        relatedQueries: [
          'What are the most common failures?',
          'Show me test trends over the last week',
          'What is the pass rate for login tests?'
        ]
      };

      setResults(mockResults);
    } catch (err) {
      setError('Failed to process your query. Please try again.');
      console.error('Error querying test data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Query Test Data</h1>
        <p className="text-secondary mt-2">
          Ask questions about your test results in natural language.
        </p>
      </div>

      <div className="card mb-6">
        <QueryForm onSubmit={handleSubmit} />
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      ) : error ? (
        <div className="bg-danger-light text-danger border border-danger rounded-md p-4">
          {error}
        </div>
      ) : results ? (
        <QueryResults results={results} onFollowupQuery={handleSubmit} />
      ) : (
        <div className="card bg-secondary-light">
          <h2 className="text-xl font-semibold mb-4">Example Queries</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              className="p-4 bg-white rounded-md shadow cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleSubmit('What was the pass rate for the last test run?')}
            >
              <p>What was the pass rate for the last test run?</p>
            </div>
            <div
              className="p-4 bg-white rounded-md shadow cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleSubmit('Show me the most common failures in the login feature.')}
            >
              <p>Show me the most common failures in the login feature.</p>
            </div>
            <div
              className="p-4 bg-white rounded-md shadow cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleSubmit('What are the trends for the checkout tests over the last month?')}
            >
              <p>What are the trends for the checkout tests over the last month?</p>
            </div>
            <div
              className="p-4 bg-white rounded-md shadow cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => handleSubmit('Which test scenarios have the highest failure rate?')}
            >
              <p>Which test scenarios have the highest failure rate?</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryPage;