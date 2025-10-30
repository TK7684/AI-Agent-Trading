// useOffline Hook - React hook for offline functionality
import { useEffect, useCallback } from 'react';
import { useOfflineStore, offlineService, type QueuedAction } from '@/services/offlineService';
import { persistenceService } from '@/services/persistenceService';
import { useNotificationStore } from '@/stores/notificationStore';

export interface OfflineHookReturn {
  isOnline: boolean;
  isServiceWorkerSupported: boolean;
  isServiceWorkerRegistered: boolean;
  offlineMode: 'full' | 'limited' | 'read-only';
  offlineDuration: number;
  queuedActions: QueuedAction[];
  queueAction: (type: 'trade' | 'config' | 'system', action: string, data: any) => void;
  clearQueue: () => void;
  retryFailedActions: () => Promise<void>;
  getOfflineCapabilities: () => OfflineCapabilities;
}

export interface OfflineCapabilities {
  canViewData: boolean;
  canModifySettings: boolean;
  canExecuteTrades: boolean;
  canReceiveNotifications: boolean;
  hasDataPersistence: boolean;
  hasBackgroundSync: boolean;
}

export function useOffline(): OfflineHookReturn {
  const {
    isOnline,
    isServiceWorkerSupported,
    isServiceWorkerRegistered,
    offlineMode,
    offlineDuration,
    queuedActions,
    addQueuedAction,
    clearQueuedActions,
  } = useOfflineStore();

  const { addNotification } = useNotificationStore();

  // Initialize offline service on mount
  useEffect(() => {
    let mounted = true;

    const initializeOfflineService = async () => {
      try {
        await offlineService.initialize();
        await persistenceService.initialize();
        
        if (mounted) {
          console.log('[useOffline] Offline services initialized');
        }
      } catch (error) {
        console.error('[useOffline] Failed to initialize offline services:', error);
        
        if (mounted) {
          addNotification({
            type: 'warning',
            title: 'Offline Features Limited',
            message: 'Some offline features may not be available due to initialization errors.',
            persistent: false,
            priority: 'normal',
            category: 'system',
          });
        }
      }
    };

    initializeOfflineService();

    return () => {
      mounted = false;
      offlineService.destroy();
    };
  }, [addNotification]);

  // Monitor online status changes
  useEffect(() => {
    if (!isOnline) {
      addNotification({
        type: 'warning',
        title: 'Connection Lost',
        message: 'You are now offline. Some features may be limited.',
        persistent: true,
        priority: 'normal',
        category: 'system',
      });
    } else {
      addNotification({
        type: 'success',
        title: 'Connection Restored',
        message: 'You are back online. Syncing queued actions...',
        persistent: false,
        priority: 'normal',
        category: 'system',
      });
    }
  }, [isOnline, addNotification]);

  // Queue action for offline execution
  const queueAction = useCallback((
    type: 'trade' | 'config' | 'system',
    action: string,
    data: any
  ) => {
    const maxRetries = type === 'trade' ? 5 : 3; // More retries for trading actions
    
    addQueuedAction({
      type,
      action,
      data,
      maxRetries,
    });

    // Also queue in persistence service for durability
    persistenceService.queueAction({
      type,
      action,
      data,
      maxRetries,
    }).catch(error => {
      console.error('[useOffline] Failed to persist queued action:', error);
    });

    addNotification({
      type: 'info',
      title: 'Action Queued',
      message: `${action} has been queued and will be executed when connection is restored.`,
      persistent: false,
      priority: 'normal',
      category: 'system',
    });
  }, [addQueuedAction, addNotification]);

  // Clear all queued actions
  const clearQueue = useCallback(() => {
    clearQueuedActions();
    addNotification({
      type: 'info',
      title: 'Queue Cleared',
      message: 'All queued actions have been cleared.',
      persistent: false,
      priority: 'normal',
      category: 'system',
    });
  }, [clearQueuedActions, addNotification]);

  // Retry failed actions manually
  const retryFailedActions = useCallback(async () => {
    if (!isOnline) {
      addNotification({
        type: 'error',
        title: 'Cannot Retry',
        message: 'Cannot retry actions while offline.',
        persistent: false,
        priority: 'normal',
        category: 'system',
      });
      return;
    }

    const failedActions = queuedActions.filter(
      action => action.retryCount >= action.maxRetries
    );

    if (failedActions.length === 0) {
      addNotification({
        type: 'info',
        title: 'No Failed Actions',
        message: 'There are no failed actions to retry.',
        persistent: false,
        priority: 'normal',
        category: 'system',
      });
      return;
    }

    addNotification({
      type: 'info',
      title: 'Retrying Actions',
      message: `Retrying ${failedActions.length} failed actions...`,
      persistent: false,
      priority: 'normal',
      category: 'system',
    });

    // Reset retry counts and let the service handle retries
    failedActions.forEach(action => {
      // Reset retry count by removing and re-adding
      useOfflineStore.getState().removeQueuedAction(action.id);
      addQueuedAction({
        type: action.type,
        action: action.action,
        data: action.data,
        maxRetries: action.maxRetries,
      });
    });
  }, [isOnline, queuedActions, addQueuedAction, addNotification]);

  // Get current offline capabilities
  const getOfflineCapabilities = useCallback((): OfflineCapabilities => {
    return {
      canViewData: true, // Always can view cached data
      canModifySettings: offlineMode !== 'read-only',
      canExecuteTrades: offlineMode === 'full',
      canReceiveNotifications: isServiceWorkerRegistered,
      hasDataPersistence: isServiceWorkerSupported,
      hasBackgroundSync: isServiceWorkerRegistered && 'serviceWorker' in navigator,
    };
  }, [offlineMode, isServiceWorkerSupported, isServiceWorkerRegistered]);

  return {
    isOnline,
    isServiceWorkerSupported,
    isServiceWorkerRegistered,
    offlineMode,
    offlineDuration,
    queuedActions,
    queueAction,
    clearQueue,
    retryFailedActions,
    getOfflineCapabilities,
  };
}

// Hook for offline-aware API calls
export function useOfflineApi() {
  const { isOnline, queueAction, getOfflineCapabilities } = useOffline();

  const makeRequest = useCallback(async (
    url: string,
    options: RequestInit = {},
    fallbackData?: any
  ) => {
    if (isOnline) {
      try {
        const response = await fetch(url, options);
        
        if (response.ok) {
          const data = await response.json();
          
          // Cache successful responses
          if (options.method === 'GET' || !options.method) {
            await persistenceService.cacheApiResponse(url, data);
          }
          
          return { data, fromCache: false, success: true };
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      } catch (error) {
        console.error('[useOfflineApi] Request failed:', error);
        
        // Try to get cached data
        const cachedData = await persistenceService.getCachedApiResponse(url);
        if (cachedData) {
          return { data: cachedData, fromCache: true, success: true };
        }
        
        // Queue write operations for later
        if (options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)) {
          queueAction('system', 'api-request', { url, options });
          return { 
            data: null, 
            fromCache: false, 
            success: false, 
            queued: true,
            error: 'Request queued for when connection is restored'
          };
        }
        
        throw error;
      }
    } else {
      // Offline mode
      const cachedData = await persistenceService.getCachedApiResponse(url);
      
      if (cachedData) {
        return { data: cachedData, fromCache: true, success: true };
      }
      
      if (fallbackData) {
        return { data: fallbackData, fromCache: false, success: true, fallback: true };
      }
      
      // Queue write operations
      if (options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)) {
        queueAction('system', 'api-request', { url, options });
        return { 
          data: null, 
          fromCache: false, 
          success: false, 
          queued: true,
          error: 'Request queued for when connection is restored'
        };
      }
      
      throw new Error('No cached data available for this request');
    }
  }, [isOnline, queueAction]);

  return {
    makeRequest,
    isOnline,
    capabilities: getOfflineCapabilities(),
  };
}