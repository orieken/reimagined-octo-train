// src/services/queryService.js
import apiClient from './api';

// Query test data using natural language
export const queryTestData = async (query) => {
  const response = await apiClient.post('/query', { query });
  return response.data;
};

// Get suggested queries
export const getSuggestedQueries = async () => {
  const response = await apiClient.get('/query/suggestions');
  return response.data;
};

// Get query history
export const getQueryHistory = async () => {
  const response = await apiClient.get('/query/history');
  return response.data;
};

// Save a query to favorites
export const saveQueryToFavorites = async (queryId) => {
  const response = await apiClient.post(`/query/favorites/${queryId}`);
  return response.data;
};

// Remove a query from favorites
export const removeQueryFromFavorites = async (queryId) => {
  const response = await apiClient.delete(`/query/favorites/${queryId}`);
  return response.data;
};

// Get favorite queries
export const getFavoriteQueries = async () => {
  const response = await apiClient.get('/query/favorites');
  return response.data;
};