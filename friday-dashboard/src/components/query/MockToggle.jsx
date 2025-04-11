// src/components/query/MockToggle.jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const MockToggle = ({ onChange }) => {
  const [useMock, setUseMock] = useState(
    localStorage.getItem('forceMockData') !== 'false'
  );

  useEffect(() => {
    // Initialize based on localStorage
    const mockSetting = localStorage.getItem('forceMockData');
    setUseMock(mockSetting !== 'false');
  }, []);

  const handleToggle = () => {
    const newValue = !useMock;
    setUseMock(newValue);
    localStorage.setItem('forceMockData', newValue ? 'true' : 'false');

    if (onChange) {
      onChange(newValue);
    }
  };

  return (
    <div className="flex items-center justify-end mb-2">
      <span className="text-sm text-gray-600 mr-2">
        {useMock ? 'Using mock data' : 'Using real API'}
      </span>
      <button
        onClick={handleToggle}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          useMock ? 'bg-gray-400' : 'bg-blue-600'
        }`}
      >
        <span className="sr-only">Use mock data</span>
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            useMock ? 'translate-x-1' : 'translate-x-6'
          }`}
        />
      </button>
    </div>
  );
};

MockToggle.propTypes = {
  onChange: PropTypes.func
};

export default MockToggle;