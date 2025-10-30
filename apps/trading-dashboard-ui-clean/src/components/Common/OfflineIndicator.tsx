// OfflineIndicator Component - Shows connection status and offline capabilities
import React from 'react';
import { useOffline } from '@/hooks/useOffline';
import { formatDuration } from '@/utils/formatters';

interface OfflineIndicatorProps {
  className?: string;
  showDetails?: boolean;
}

export const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  className = '',
  showDetails = false,
}) => {
  const {
    isOnline,
    isServiceWorkerRegistered,
    // offlineMode,
    offlineDuration,
    queuedActions,
    getOfflineCapabilities,
  } = useOffline();

  const capabilities = getOfflineCapabilities();

  const getStatusColor = () => {
    if (isOnline) return 'text-green-600 bg-green-100';
    if (isServiceWorkerRegistered) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusText = () => {
    if (isOnline) return 'Online';
    if (isServiceWorkerRegistered) return 'Offline (Limited)';
    return 'Offline (Read-only)';
  };

  const getStatusIcon = () => {
    if (isOnline) {
      return (
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      );
    }
    
    return (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
      </svg>
    );
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* Status Indicator */}
      <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
        {getStatusIcon()}
        <span>{getStatusText()}</span>
      </div>

      {/* Queued Actions Badge */}
      {queuedActions.length > 0 && (
        <div className="flex items-center space-x-1 px-2 py-1 bg-blue-100 text-blue-600 rounded-full text-xs font-medium">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
          <span>{queuedActions.length} queued</span>
        </div>
      )}

      {/* Offline Duration */}
      {!isOnline && offlineDuration > 0 && (
        <div className="text-xs text-gray-500">
          Offline for {formatDuration(offlineDuration)}
        </div>
      )}

      {/* Detailed Status */}
      {showDetails && (
        <div className="ml-4 text-xs text-gray-600">
          <div className="grid grid-cols-2 gap-2">
            <div className={`flex items-center space-x-1 ${capabilities.canViewData ? 'text-green-600' : 'text-red-600'}`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              <span>View Data</span>
            </div>
            <div className={`flex items-center space-x-1 ${capabilities.canModifySettings ? 'text-green-600' : 'text-red-600'}`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              <span>Modify Settings</span>
            </div>
            <div className={`flex items-center space-x-1 ${capabilities.canExecuteTrades ? 'text-green-600' : 'text-red-600'}`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              <span>Execute Trades</span>
            </div>
            <div className={`flex items-center space-x-1 ${capabilities.hasBackgroundSync ? 'text-green-600' : 'text-red-600'}`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              <span>Background Sync</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OfflineIndicator;