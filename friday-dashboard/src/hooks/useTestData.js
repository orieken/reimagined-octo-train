// src/hooks/useTestData.js
import { useState, useEffect, useCallback } from 'react';
import { getTestStats } from '@services/testDataService.js';

const useTestData = (initialFilter = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState(initialFilter);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getTestStats(filter);
      setData(response);
    } catch (err) {
      setError(err.message || 'Failed to fetch test data');
      console.error('Error fetching test data:', err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateFilter = useCallback((newFilter) => {
    setFilter(prev => ({ ...prev, ...newFilter }));
  }, []);

  const refresh = fetchData;

  return {
    data,
    loading,
    error,
    filter,
    updateFilter,
    refresh
  };
};

export default useTestData;