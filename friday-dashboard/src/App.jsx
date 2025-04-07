// src/App.jsx
import { useState } from 'react';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import Footer from './components/common/Footer';
import AppRoutes from './routes';
import { ApiProvider } from './contexts/ApiContext';
import { NotificationProvider } from '@contexts/NotificationContext.jsx';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <ApiProvider>
      <NotificationProvider>
        <div className="flex h-screen overflow-hidden bg-secondary-light">
          {/* Sidebar */}
          <Sidebar isOpen={sidebarOpen} toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

          {/* Main Content */}
          <div className="flex flex-col flex-1 w-0 overflow-hidden">
            <Header toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

            <main className="relative flex-1 overflow-y-auto focus:outline-none p-4">
              <div className="container mx-auto">
                <AppRoutes />
              </div>
            </main>

            <Footer />
          </div>
        </div>
      </NotificationProvider>
    </ApiProvider>
  );
}

export default App;