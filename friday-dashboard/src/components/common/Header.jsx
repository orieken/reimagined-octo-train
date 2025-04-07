// src/components/common/Header.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../../contexts/ApiContext';
import NotificationCenter from './NotificationCenter.jsx';

const Header = ({ toggleSidebar }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { apiStatus } = useApi();
  const navigate = useNavigate();

  const toggleDropdown = () => {
    setIsDropdownOpen(!isDropdownOpen);
  };

  return (
    <header className="bg-white shadow-sm z-10 relative">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            {/* Mobile menu button */}
            <button
              type="button"
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-primary hover:bg-secondary-light lg:hidden"
              onClick={toggleSidebar}
              aria-label="Open sidebar"
            >
              <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Logo */}
            <div className="flex-shrink-0 flex items-center ml-4 lg:ml-0 cursor-pointer" onClick={() => navigate('/')}>
              <span className="text-xl font-bold text-primary">Friday Dashboard</span>
            </div>
          </div>

          <div className="flex items-center">
            {/* Mock Data Indicator */}
            {apiStatus.usingMockData && (
              <div className="mr-4 px-2 py-1 bg-warning-light text-warning-dark text-xs rounded-md">
                Using Demo Data
              </div>
            )}

            {/* API Status Indicator */}
            <div className="mr-4 flex items-center">
              <div className={`h-3 w-3 rounded-full mr-2 ${apiStatus.isConnected ? 'bg-success' : 'bg-warning'}`}></div>
              <span className="text-sm">{apiStatus.isConnected ? 'API Connected' : 'API Simulated'}</span>
            </div>

            {/* Notification Center */}
            <div className="mx-4">
              <NotificationCenter />
            </div>

            {/* User Profile Dropdown */}
            <div className="relative">
              <div>
                <button
                  type="button"
                  className="flex items-center max-w-xs rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                  id="user-menu-button"
                  onClick={toggleDropdown}
                  aria-expanded={isDropdownOpen}
                  aria-haspopup="true"
                >
                  <span className="sr-only">Open user menu</span>
                  <div className="h-8 w-8 rounded-full bg-primary text-white flex items-center justify-center">
                    <span>U</span>
                  </div>
                </button>
              </div>

              {isDropdownOpen && (
                <div
                  className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
                  role="menu"
                  aria-orientation="vertical"
                  aria-labelledby="user-menu-button"
                  tabIndex="-1"
                >
                  <a
                    href="#"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-secondary-light"
                    role="menuitem"
                    onClick={() => {
                      navigate('/settings');
                      setIsDropdownOpen(false);
                    }}
                  >
                    Settings
                  </a>
                  <a
                    href="#"
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-secondary-light"
                    role="menuitem"
                    onClick={() => setIsDropdownOpen(false)}
                  >
                    Sign out
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;