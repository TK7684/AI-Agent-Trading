// OfflineQueue Component - Manages queued actions when offline
import React, { useState } from 'react';
import { useOffline } from '@/hooks/useOffline';
import { formatDateTime } from '@/utils/formatters';
import type { QueuedAction } from '@/services/offlineService';

interface OfflineQueueProps {
  className?: string;
}

export const OfflineQueue: React.FC<OfflineQueueProps> = ({ className = '' }) => {
  const {
    queuedActions,
    clearQueue,
    retryFailedActions,
    isOnline,
  } = useOffline();

  const [isExpanded, setIsExpanded] = useState(false);

  if (queuedActions.length === 0) {
    return null;
  }

  const failedActions = queuedActions.filter(action => action.retryCount >= action.maxRetries);
  const pendingActions = queuedActions.filter(action => action.retryCount < action.maxRetries);

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'trade':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" />
            <path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" />
          </svg>
        );
      case 'config':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
        );
      case 'system':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const getActionStatusColor = (action: QueuedAction) => {
    if (action.retryCount >= action.maxRetries) {
      return 'text-red-600 bg-red-50';
    }
    if (action.retryCount > 0) {
      return 'text-yellow-600 bg-yellow-50';
    }
    return 'text-blue-600 bg-blue-50';
  };

  const getActionStatusText = (action: QueuedAction) => {
    if (action.retryCount >= action.maxRetries) {
      return 'Failed';
    }
    if (action.retryCount > 0) {
      return `Retry ${action.retryCount}/${action.maxRetries}`;
    }
    return 'Pending';
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
          <h3 className="text-sm font-medium text-gray-900">
            Queued Actions ({queuedActions.length})
          </h3>
          {failedActions.length > 0 && (
            <span className="px-2 py-1 text-xs font-medium text-red-600 bg-red-100 rounded-full">
              {failedActions.length} failed
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {failedActions.length > 0 && isOnline && (
            <button
              onClick={retryFailedActions}
              className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-100 rounded hover:bg-blue-200 transition-colors"
            >
              Retry Failed
            </button>
          )}
          
          <button
            onClick={clearQueue}
            className="px-3 py-1 text-xs font-medium text-red-600 bg-red-100 rounded hover:bg-red-200 transition-colors"
          >
            Clear All
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg
              className={`w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      {/* Queue Summary */}
      {!isExpanded && (
        <div className="p-4">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>{pendingActions.length} pending</span>
            {failedActions.length > 0 && (
              <span className="text-red-600">{failedActions.length} failed</span>
            )}
          </div>
        </div>
      )}

      {/* Expanded Queue List */}
      {isExpanded && (
        <div className="max-h-64 overflow-y-auto">
          {queuedActions.map((action) => (
            <div
              key={action.id}
              className="flex items-center justify-between p-3 border-b border-gray-100 last:border-b-0"
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <div className={`p-1 rounded ${getActionStatusColor(action)}`}>
                  {getActionIcon(action.type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {action.action}
                    </span>
                    <span className="text-xs text-gray-500 uppercase">
                      {action.type}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-gray-500">
                      {formatDateTime(action.timestamp)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getActionStatusColor(action)}`}>
                      {getActionStatusText(action)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Data Preview */}
              {action.data && (
                <div className="text-xs text-gray-400 max-w-32 truncate">
                  {typeof action.data === 'object' 
                    ? JSON.stringify(action.data).substring(0, 30) + '...'
                    : String(action.data).substring(0, 30)
                  }
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      {isExpanded && (
        <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          {isOnline ? (
            <span className="flex items-center space-x-1">
              <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span>Actions will be processed automatically when online</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1">
              <svg className="w-3 h-3 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>Actions queued for when connection is restored</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default OfflineQueue;