/**
 * Connection status indicator component
 */

import React from 'react';
import { useBackendIntegration } from '@/hooks/useBackendIntegration';
import { useSystemStore } from '@/stores/systemStore';

interface ConnectionStatusProps {
  className?: string;
  showDetails?: boolean;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className = '',
  showDetails = false,
}) => {
  const { isConnected, isConnecting, error } = useBackendIntegration();
  const { connectionStatus } = useSystemStore();

  const getStatusColor = () => {
    if (isConnecting) return 'text-yellow-500';
    if (isConnected) return 'text-green-500';
    return 'text-red-500';
  };

  const getStatusText = () => {
    if (isConnecting) return 'Connecting...';
    if (isConnected) return 'Connected';
    return 'Disconnected';
  };

  const getStatusIcon = () => {
    if (isConnecting) {
      return (
        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-yellow-500"></div>
      );
    }
    
    if (isConnected) {
      return (
        <div className="h-3 w-3 bg-green-500 rounded-full"></div>
      );
    }
    
    return (
      <div className="h-3 w-3 bg-red-500 rounded-full"></div>
    );
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {getStatusIcon()}
      <span className={`text-sm font-medium ${getStatusColor()}`}>
        {getStatusText()}
      </span>
      
      {showDetails && (
        <div className="ml-4 flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1">
            <div className={`h-2 w-2 rounded-full ${connectionStatus.api ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>API</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`h-2 w-2 rounded-full ${connectionStatus.websocket ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>WebSocket</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`h-2 w-2 rounded-full ${connectionStatus.database ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>Database</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`h-2 w-2 rounded-full ${connectionStatus.broker ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>Broker</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`h-2 w-2 rounded-full ${connectionStatus.llm ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>LLM</span>
          </div>
        </div>
      )}
      
      {error && (
        <div className="ml-2 text-xs text-red-400" title={error}>
          ⚠️
        </div>
      )}
    </div>
  );
};