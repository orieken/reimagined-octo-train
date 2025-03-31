// src/contexts/ApiContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';
import { checkHealth } from '../services/api';

const ApiContext = createContext();

export function ApiProvider({ children }) {
  const [apiStatus, setApiStatus] = useState({
    isConnected: false,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const healthStatus = await checkHealth();
        setApiStatus({
          isConnected: healthStatus.isConnected,
          isLoading: false,
          error: healthStatus.error,
        });
      } catch (_error) {
        setApiStatus({
          isConnected: false,
          isLoading: false,
          error: 'Unable to connect to the Friday service API',
        });
      }
    };

    checkApiHealth();

    // Set up a health check interval
    const interval = setInterval(checkApiHealth, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  const value = {
    apiStatus,
  };

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApi() {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
}