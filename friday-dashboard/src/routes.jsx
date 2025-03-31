// src/routes.jsx
import { Route, Routes, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import TestResultsPage from './pages/TestResultsPage';
import QueryPage from './pages/QueryPage';
import SettingsPage from './pages/SettingsPage';

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/test-results" element={<TestResultsPage />} />
      <Route path="/query" element={<QueryPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default AppRoutes;