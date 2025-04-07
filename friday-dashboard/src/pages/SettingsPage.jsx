// src/pages/SettingsPage.jsx
import React, { useState } from 'react';
import NotificationSettings from '../components/settings/NotificationSettings';

const SettingsPage = () => {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className="py-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-secondary mt-2">
          Configure your Friday Dashboard preferences.
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="mb-6 border-b border-secondary">
        <nav className="flex -mb-px">
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'general'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('general')}
          >
            General
          </button>
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'notifications'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('notifications')}
          >
            Notifications
          </button>
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'api'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('api')}
          >
            API Configuration
          </button>
          <button
            className={`py-4 px-6 border-b-2 font-medium text-sm ${
              activeTab === 'data'
                ? 'border-primary text-primary'
                : 'border-transparent text-secondary hover:text-primary hover:border-secondary'
            }`}
            onClick={() => setActiveTab('data')}
          >
            Data Management
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'general' && (
          <GeneralSettings />
        )}

        {activeTab === 'notifications' && (
          <NotificationSettings />
        )}

        {activeTab === 'api' && (
          <ApiSettings />
        )}

        {activeTab === 'data' && (
          <DataSettings />
        )}
      </div>
    </div>
  );
};

// General Settings Component
const GeneralSettings = () => {
  const [settings, setSettings] = useState({
    theme: 'light',
    refreshInterval: 5,
    notifications: true
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings({
      ...settings,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);

    // Simulate API call to save settings
    await new Promise(resolve => setTimeout(resolve, 1000));

    setIsSaving(false);
    setSaveSuccess(true);

    // Clear success message after 3 seconds
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">User Interface</h2>
          <div className="mb-4">
            <label htmlFor="theme" className="block text-sm font-medium text-secondary-dark mb-1">
              Theme
            </label>
            <select
              id="theme"
              name="theme"
              className="form-input"
              value={settings.theme}
              onChange={handleChange}
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System Default</option>
            </select>
          </div>
          <div className="mb-4">
            <label htmlFor="refreshInterval" className="block text-sm font-medium text-secondary-dark mb-1">
              Data Refresh Interval (minutes)
            </label>
            <input
              type="number"
              id="refreshInterval"
              name="refreshInterval"
              min="1"
              max="60"
              className="form-input"
              value={settings.refreshInterval}
              onChange={handleChange}
            />
            <p className="mt-1 text-xs text-secondary">
              How often the dashboard data should automatically refresh.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end mt-8">
          {saveSuccess && (
            <div className="mr-4 text-success">
              Settings saved successfully!
            </div>
          )}
          <button
            type="submit"
            className="btn btn-primary flex items-center"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

// API Settings Component
const ApiSettings = () => {
  const [settings, setSettings] = useState({
    apiEndpoint: '/api'
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings({
      ...settings,
      [name]: value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);

    // Simulate API call to save settings
    await new Promise(resolve => setTimeout(resolve, 1000));

    setIsSaving(false);
    setSaveSuccess(true);

    // Clear success message after 3 seconds
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
          <div className="mb-4">
            <label htmlFor="apiEndpoint" className="block text-sm font-medium text-secondary-dark mb-1">
              API Endpoint
            </label>
            <input
              type="text"
              id="apiEndpoint"
              name="apiEndpoint"
              className="form-input"
              value={settings.apiEndpoint}
              onChange={handleChange}
            />
            <p className="mt-1 text-xs text-secondary">
              The URL of the Friday service API.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end mt-8">
          {saveSuccess && (
            <div className="mr-4 text-success">
              Settings saved successfully!
            </div>
          )}
          <button
            type="submit"
            className="btn btn-primary flex items-center"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

// Data Management Settings Component
const DataSettings = () => {
  const [settings, setSettings] = useState({
    dataRetentionDays: 30
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings({
      ...settings,
      [name]: value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);

    // Simulate API call to save settings
    await new Promise(resolve => setTimeout(resolve, 1000));

    setIsSaving(false);
    setSaveSuccess(true);

    // Clear success message after 3 seconds
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Data Management</h2>
          <div className="mb-4">
            <label htmlFor="dataRetentionDays" className="block text-sm font-medium text-secondary-dark mb-1">
              Data Retention Period (days)
            </label>
            <input
              type="number"
              id="dataRetentionDays"
              name="dataRetentionDays"
              min="1"
              max="365"
              className="form-input"
              value={settings.dataRetentionDays}
              onChange={handleChange}
            />
            <p className="mt-1 text-xs text-secondary">
              How long test data should be retained before being archived.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end mt-8">
          {saveSuccess && (
            <div className="mr-4 text-success">
              Settings saved successfully!
            </div>
          )}
          <button
            type="submit"
            className="btn btn-primary flex items-center"
            disabled={isSaving}
          >
            {isSaving ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save Settings'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsPage;