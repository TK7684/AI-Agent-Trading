import { Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import Dashboard from '@components/Dashboard/Dashboard';
import { DashboardLayout } from '@components/Dashboard/Layout/DashboardLayout';
import ToastContainer from '@components/Notifications/ToastContainer';
import ErrorBoundary from '@components/Common/ErrorBoundary';
import { Login } from '@components/Auth/Login';
import ProtectedRoute from '@components/Auth/ProtectedRoute';
import { ConnectionTest } from '@components/ConnectionTest';
import { ConnectionStatus } from '@components/Common/ConnectionStatus';
import { BackendConnectionTest } from '@components/BackendConnectionTest';
import { OfflineIndicator } from '@components/Common/OfflineIndicator';
import { OfflineQueue } from '@components/Common/OfflineQueue';
import { OfflineBanner } from '@components/Common/OfflineBanner';
import { useBackendIntegration } from '@/hooks/useBackendIntegration';
import { useOffline } from '@/hooks/useOffline';
import { offlineService } from '@/services/offlineService';
import { persistenceService } from '@/services/persistenceService';
import './App.css';

function App() {
  const { error } = useBackendIntegration();
  const { queuedActions } = useOffline();

  // Initialize offline services
  useEffect(() => {
    const initializeOfflineServices = async () => {
      try {
        await Promise.all([
          offlineService.initialize(),
          persistenceService.initialize(),
        ]);
        console.log('[App] Offline services initialized successfully');
      } catch (error) {
        console.error('[App] Failed to initialize offline services:', error);
      }
    };

    initializeOfflineServices();

    // Cleanup on unmount
    return () => {
      offlineService.destroy();
      persistenceService.close();
    };
  }, []);

  return (
    <div className="App">
      <ToastContainer />
      <OfflineBanner />
      
      {/* Connection status banner */}
      <div className="bg-gray-800 text-white px-4 py-2 flex justify-between items-center">
        <div className="text-sm">Trading Dashboard</div>
        <div className="flex items-center space-x-4">
          <OfflineIndicator />
          <ConnectionStatus showDetails={true} />
        </div>
      </div>
      
      {/* Connection error banner */}
      {error && (
        <div className="bg-red-100 text-red-900 text-center py-2 text-sm">
          Backend connection error: {error}
        </div>
      )}

      {/* Offline queue banner */}
      {queuedActions.length > 0 && (
        <div className="bg-blue-50 border-b border-blue-200 p-2">
          <OfflineQueue className="max-w-4xl mx-auto" />
        </div>
      )}
      
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/connection-test" element={<ConnectionTest />} />
          <Route path="/backend-test" element={<BackendConnectionTest />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Dashboard />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Dashboard />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </ErrorBoundary>
    </div>
  );
}

export default App;