// src/components/settings/NotificationSettings.jsx
import React, { useState, useEffect } from 'react';
import {
  getNotificationPreferences,
  updateNotificationPreferences
} from '../../services/notificationService';

const NotificationSettings = () => {
  const [preferences, setPreferences] = useState({
    emailEnabled: false,
    browserEnabled: false,
    testFailuresEnabled: true,
    buildCompletionsEnabled: true,
    weeklyReportsEnabled: true,
    dailyDigestEnabled: false
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load preferences on component mount
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        setLoading(true);
        setError(null);

        const prefs = await getNotificationPreferences();

        // Only update if we got preferences back
        if (Object.keys(prefs).length > 0) {
          setPreferences(prevPrefs => ({
            ...prevPrefs,
            ...prefs
          }));
        }
      } catch (err) {
        console.error('Error loading notification preferences:', err);
        setError('Failed to load notification preferences. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadPreferences();
  }, []);

  // Handle checkbox change
  const handleCheckboxChange = (e) => {
    const { name, checked } = e.target;

    setPreferences(prevPrefs => ({
      ...prevPrefs,
      [name]: checked
    }));
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      setSaving(true);
      setError(null);
      setSaveSuccess(false);

      await updateNotificationPreferences(preferences);

      setSaveSuccess(true);

      // Hide success message after 3 seconds
      setTimeout(() => {
        setSaveSuccess(false);
      }, 3000);
    } catch (err) {
      console.error('Error saving notification preferences:', err);
      setError('An error occurred while saving your preferences. Please try again later.');
    } finally {
      setSaving(false);
    }
  };

  // Request browser notification permission
  const requestBrowserPermission = () => {
    if (!('Notification' in window)) {
      alert('This browser does not support desktop notifications');
      return;
    }

    Notification.requestPermission()
      .then(permission => {
        if (permission === 'granted') {
          // Show a test notification
          new Notification('Friday Dashboard', {
            body: 'Browser notifications are now enabled!',
            icon: '/favicon.ico'
          });

          // Update preferences
          setPreferences(prevPrefs => ({
            ...prevPrefs,
            browserEnabled: true
          }));
        }
      });
  };

  // Group preferences by category
  const notificationGroups = [
    {
      title: 'Notification Methods',
      description: 'How would you like to receive notifications?',
      preferences: [
        {
          id: 'browserEnabled',
          label: 'Browser Notifications',
          description: 'Receive notifications in your browser',
          custom: true,
          render: () => (
            <div className="flex items-center">
              <button
                type="button"
                className="btn btn-secondary text-sm"
                onClick={requestBrowserPermission}
                disabled={preferences.browserEnabled}
              >
                {preferences.browserEnabled ? 'Enabled' : 'Enable Browser Notifications'}
              </button>
              {preferences.browserEnabled && (
                <span className="ml-2 text-sm text-success">✓ Enabled</span>
              )}
            </div>
          )
        },
        {
          id: 'emailEnabled',
          label: 'Email Notifications',
          description: 'Receive notifications via email'
        }
      ]
    },
    {
      title: 'Notification Types',
      description: 'What events would you like to be notified about?',
      preferences: [
        {
          id: 'testFailuresEnabled',
          label: 'Test Failures',
          description: 'Get notified when tests fail'
        },
        {
          id: 'buildCompletionsEnabled',
          label: 'Build Completions',
          description: 'Get notified when builds complete'
        },
        {
          id: 'weeklyReportsEnabled',
          label: 'Weekly Reports',
          description: 'Receive weekly test summary reports'
        },
        {
          id: 'dailyDigestEnabled',
          label: 'Daily Digest',
          description: 'Receive a daily summary of test activity'
        }
      ]
    }
  ];

  if (loading) {
    return (
      <div className="p-4 bg-white rounded-lg shadow">
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Notification Settings</h2>

      {error && (
        <div className="mb-4 p-4 bg-danger-light text-danger rounded-md">
          {error}
        </div>
      )}

      {saveSuccess && (
        <div className="mb-4 p-4 bg-success-light text-success rounded-md">
          Your notification preferences have been saved successfully.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {notificationGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="mb-6 pb-6 border-b border-secondary-light last:border-b-0 last:pb-0">
            <h3 className="text-lg font-medium mb-2">{group.title}</h3>
            {group.description && (
              <p className="text-secondary text-sm mb-4">{group.description}</p>
            )}

            <div className="space-y-4">
              {group.preferences.map((pref) => (
                <div key={pref.id} className="flex items-start">
                  {pref.custom ? (
                    pref.render()
                  ) : (
                    <>
                      <div className="flex items-center h-5">
                        <input
                          id={pref.id}
                          name={pref.id}
                          type="checkbox"
                          className="h-4 w-4 text-primary focus:ring-primary border-secondary rounded"
                          checked={preferences[pref.id] || false}
                          onChange={handleCheckboxChange}
                        />
                      </div>
                      <div className="ml-3 text-sm">
                        <label htmlFor={pref.id} className="font-medium text-secondary-dark">
                          {pref.label}
                        </label>
                        {pref.description && (
                          <p className="text-secondary">{pref.description}</p>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        <div className="flex justify-end mt-6">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
              </>
            ) : (
              'Save Preferences'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default NotificationSettings;
