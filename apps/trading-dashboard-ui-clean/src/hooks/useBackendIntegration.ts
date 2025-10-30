/**
 * React hook for backend integration
 */

import { useEffect, useState, useCallback } from 'react';
import { backendIntegration } from '@/services/BackendIntegration';
import { useTradingStore } from '@/stores/tradingStore';
import { useSystemStore } from '@/stores/systemStore';
import { env } from '@/config/environment';
import type { LoginRequest } from '@/types';

interface BackendConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  isAuthenticated: boolean;
  error: string | null;
  lastConnectionAttempt: Date | null;
}

export function useBackendIntegration() {
  const [connectionState, setConnectionState] = useState<BackendConnectionState>({
    isConnected: false,
    isConnecting: false,
    isAuthenticated: false,
    error: null,
    lastConnectionAttempt: null,
  });

  // Store actions
  const {
    setPerformanceMetrics,
    setTradingLogs,
    addTradingLog,
    setAgentStatus,
    setLoadingMetrics,
    setLoadingLogs,
    setLoadingStatus,
  } = useTradingStore();

  const {
    setSystemHealth,
    setConnectionStatus,
    setIsConnected,
    setLoadingHealth,
  } = useSystemStore();

  /**
   * Initialize backend connection
   */
  const initialize = useCallback(async () => {
    if (connectionState.isConnecting) return;

    setConnectionState(prev => ({
      ...prev,
      isConnecting: true,
      error: null,
      lastConnectionAttempt: new Date(),
    }));

    try {
      await backendIntegration.initialize();
      
      setConnectionState(prev => ({
        ...prev,
        isConnected: true,
        isConnecting: false,
      }));

      // Update system store
      setIsConnected(true);
      setConnectionStatus({ api: true, websocket: true });

      // Set up real-time subscriptions
      setupRealtimeSubscriptions();

      if (env.debugMode) {
        console.log('Backend integration initialized successfully');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      setConnectionState(prev => ({
        ...prev,
        isConnected: false,
        isConnecting: false,
        error: errorMessage,
      }));

      // Update system store
      setIsConnected(false);
      setConnectionStatus({ api: false, websocket: false });

      console.error('Backend integration failed:', error);
    }
  }, [connectionState.isConnecting, setIsConnected, setConnectionStatus]);

  /**
   * Authenticate with backend
   */
  const authenticate = useCallback(async (credentials: LoginRequest) => {
    try {
      const result = await backendIntegration.authenticate(credentials);
      
      setConnectionState(prev => ({
        ...prev,
        isAuthenticated: true,
        error: null,
      }));

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
      
      setConnectionState(prev => ({
        ...prev,
        isAuthenticated: false,
        error: errorMessage,
      }));

      throw error;
    }
  }, []);

  /**
   * Logout and cleanup
   */
  const logout = useCallback(async () => {
    try {
      await backendIntegration.logout();
      
      setConnectionState(prev => ({
        ...prev,
        isAuthenticated: false,
        error: null,
      }));
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }, []);

  /**
   * Fetch performance metrics
   */
  const fetchPerformanceMetrics = useCallback(async () => {
    setLoadingMetrics(true);
    try {
      const metrics = await backendIntegration.getPerformanceMetrics();
      setPerformanceMetrics(metrics);
    } catch (error) {
      console.error('Failed to fetch performance metrics:', error);
    } finally {
      setLoadingMetrics(false);
    }
  }, [setLoadingMetrics, setPerformanceMetrics]);

  /**
   * Fetch agent status
   */
  const fetchAgentStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const status = await backendIntegration.getAgentStatus();
      setAgentStatus(status);
    } catch (error) {
      console.error('Failed to fetch agent status:', error);
    } finally {
      setLoadingStatus(false);
    }
  }, [setLoadingStatus, setAgentStatus]);

  /**
   * Fetch system health
   */
  const fetchSystemHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const health = await backendIntegration.getSystemHealth();
      setSystemHealth(health);
    } catch (error) {
      console.error('Failed to fetch system health:', error);
    } finally {
      setLoadingHealth(false);
    }
  }, [setLoadingHealth, setSystemHealth]);

  /**
   * Fetch trading history
   */
  const fetchTradingHistory = useCallback(async (params?: any) => {
    setLoadingLogs(true);
    try {
      const logs = await backendIntegration.getTradingHistory(params);
      setTradingLogs(logs);
    } catch (error) {
      console.error('Failed to fetch trading history:', error);
    } finally {
      setLoadingLogs(false);
    }
  }, [setLoadingLogs, setTradingLogs]);

  /**
   * Control agent
   */
  const controlAgent = useCallback(async (action: 'start' | 'stop' | 'pause') => {
    try {
      await backendIntegration.controlAgent(action);
      // Refresh agent status after control action
      await fetchAgentStatus();
    } catch (error) {
      console.error(`Failed to ${action} agent:`, error);
      throw error;
    }
  }, [fetchAgentStatus]);

  /**
   * Set up real-time subscriptions
   */
  const setupRealtimeSubscriptions = useCallback(() => {
    // Subscribe to trading updates
    backendIntegration.subscribeToTradingUpdates((data) => {
      if (data.type === 'TRADE_OPENED' || data.type === 'TRADE_CLOSED') {
        addTradingLog(data.data);
      } else if (data.type === 'PNL_UPDATE') {
        setPerformanceMetrics(data.data);
      }
    });

    // Subscribe to system updates
    backendIntegration.subscribeToSystemUpdates((data) => {
      if (data.type === 'HEALTH_CHECK') {
        setSystemHealth(data.data);
      }
    });

    // Subscribe to agent updates
    backendIntegration.subscribeToAgentUpdates((data) => {
      if (data.type === 'STATUS_CHANGE') {
        setAgentStatus(data.data);
      }
    });
  }, [addTradingLog, setPerformanceMetrics, setSystemHealth, setAgentStatus]);

  /**
   * Refresh all data
   */
  const refreshAllData = useCallback(async () => {
    if (!connectionState.isConnected || !connectionState.isAuthenticated) return;

    try {
      await Promise.all([
        fetchPerformanceMetrics(),
        fetchAgentStatus(),
        fetchSystemHealth(),
        fetchTradingHistory(),
      ]);
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  }, [
    connectionState.isConnected,
    connectionState.isAuthenticated,
    fetchPerformanceMetrics,
    fetchAgentStatus,
    fetchSystemHealth,
    fetchTradingHistory,
  ]);

  /**
   * Check connection status
   */
  const checkConnectionStatus = useCallback(() => {
    const status = backendIntegration.getConnectionStatus();
    
    setConnectionState(prev => ({
      ...prev,
      isConnected: status.api && status.websocket,
    }));

    setConnectionStatus({
      api: status.api,
      websocket: status.websocket,
    });

    return status;
  }, [setConnectionStatus]);

  // Initialize on mount
  useEffect(() => {
    initialize();

    // Set up periodic connection status checks
    const statusCheckInterval = setInterval(checkConnectionStatus, 30000); // Every 30 seconds

    return () => {
      clearInterval(statusCheckInterval);
      backendIntegration.destroy();
    };
  }, [initialize, checkConnectionStatus]);

  // Auto-refresh data when connected AND authenticated
  useEffect(() => {
    if (connectionState.isConnected && connectionState.isAuthenticated && !connectionState.isConnecting) {
      refreshAllData();

      // Set up periodic data refresh
      const refreshInterval = setInterval(refreshAllData, 60000); // Every minute

      return () => clearInterval(refreshInterval);
    }
  }, [connectionState.isConnected, connectionState.isAuthenticated, connectionState.isConnecting, refreshAllData]);

  return {
    // Connection state
    ...connectionState,
    
    // Actions
    initialize,
    authenticate,
    logout,
    controlAgent,
    refreshAllData,
    checkConnectionStatus,
    
    // Data fetchers
    fetchPerformanceMetrics,
    fetchAgentStatus,
    fetchSystemHealth,
    fetchTradingHistory,
    
    // Backend services
    apiService: backendIntegration.getApiService(),
    wsService: backendIntegration.getWebSocketService(),
  };
}