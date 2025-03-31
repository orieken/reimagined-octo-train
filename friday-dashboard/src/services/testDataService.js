// src/services/testDataService.js
import apiClient from './api';

// Get overall test statistics
export const getTestStats = async (filter = {}) => {
  const params = new URLSearchParams();

  // Add filter parameters
  Object.entries(filter).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  });

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await apiClient.get(`/stats${query}`);
  return response.data;
};

// Get detailed test results
export const getTestResults = async (build, filter = {}) => {
  const params = new URLSearchParams();

  // Add filter parameters
  Object.entries(filter).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  });

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await apiClient.get(`/results/${build}${query}`);
  return response.data;
};

// Get test trends over time
export const getTestTrends = async (timeRange = 'week', filter = {}) => {
  const params = new URLSearchParams({ timeRange });

  // Add filter parameters
  Object.entries(filter).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  });

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await apiClient.get(`/trends${query}`);
  return response.data;
};

// Get failure analysis
export const getFailureAnalysis = async (filter = {}) => {
  const params = new URLSearchParams();

  // Add filter parameters
  Object.entries(filter).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  });

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await apiClient.get(`/failures${query}`);
  return response.data;
};

// Upload test results
export const uploadTestResults = async (formData) => {
  const response = await apiClient.post('/processor/cucumber-reports', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return response.data;
};

// Upload build information
export const uploadBuildInfo = async (buildInfo) => {
  const response = await apiClient.post('/processor/build-info', buildInfo);
  return response.data;
};