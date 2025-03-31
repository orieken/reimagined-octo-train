// src/components/common/Footer.jsx
import React from 'react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white shadow-sm z-10 py-3">
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row items-center justify-between">
          <div className="text-sm text-secondary-dark">
            &copy; {currentYear} Friday Dashboard. All rights reserved.
          </div>
          <div className="mt-2 sm:mt-0 text-xs text-secondary">
            <span>Version 0.1.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;