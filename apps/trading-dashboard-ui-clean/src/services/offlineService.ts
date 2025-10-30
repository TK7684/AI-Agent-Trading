// Offline Service - Handles offline detection and graceful degradation
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface OfflineState {
  isOnline: boolean;
  isServiceWorkerSupported: boolean;
  isServiceWorkerRegistered: boolean;
  lastOnlineTime: Date | null;
  offlineDuration: number;
  queuedActions: QueuedAction[];
  offlineMode: 'full' | 'limited' | 'read-only';
}

export interface QueuedAction {
  id: string;
  type: 'trade' | 'config' | 'system';
  action: string;
  data: any;
  timestamp: Date;
  retryCount: number;
  maxRetries: number;
}

interface OfflineStore extends OfflineState {
  setOnlineStatus: (isOnline: boolean) => void;
  setServiceWorkerStatus: (supported: boolean, registered: boolean) => void;
  addQueuedAction: (action: Omit<QueuedAction, 'id' | 'timestamp' | 'retryCount'>) => void;
  removeQueuedAction: (id: string) => void;
  updateOfflineMode: (mode: 'full' | 'limited' | 'read-only') => void;
  clearQueuedActions: () => void;
  incrementRetryCount: (id: string) => void;
}

export const useOfflineStore = create<OfflineStore>()(
  subscribeWithSelector((set, get) => ({
    isOnline: navigator.onLine,
    isServiceWorkerSupported: 'serviceWorker' in navigator,
    isServiceWorkerRegistered: false,
    lastOnlineTime: navigator.onLine ? new Date() : null,
    offlineDuration: 0,
    queuedActions: [],
    offlineMode: 'full',

    setOnlineStatus: (isOnline: boolean) => {
      const state = get();
      set({
        isOnline,
        lastOnlineTime: isOnline ? new Date() : state.lastOnlineTime,
        offlineDuration: isOnline ? 0 : state.offlineDuration,
      });
    },

    setServiceWorkerStatus: (supported: boolean, registered: boolean) => {
      set({
        isServiceWorkerSupported: supported,
        isServiceWorkerRegistered: registered,
      });
    },

    addQueuedAction: (action) => {
      const newAction: QueuedAction = {
        ...action,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
        retryCount: 0,
      };
      
      set((state) => ({
        queuedActions: [...state.queuedActions, newAction],
      }));
    },

    removeQueuedAction: (id: string) => {
      set((state) => ({
        queuedActions: state.queuedActions.filter(action => action.id !== id),
      }));
    },

    updateOfflineMode: (mode) => {
      set({ offlineMode: mode });
    },

    clearQueuedActions: () => {
      set({ queuedActions: [] });
    },

    incrementRetryCount: (id: string) => {
      set((state) => ({
        queuedActions: state.queuedActions.map(action =>
          action.id === id
            ? { ...action, retryCount: action.retryCount + 1 }
            : action
        ),
      }));
    },
  }))
);

class OfflineService {
  private offlineCheckInterval: NodeJS.Timeout | null = null;
  private serviceWorkerRegistration: ServiceWorkerRegistration | null = null;

  async initialize(): Promise<void> {
    console.log('[OfflineService] Initializing offline service');
    
    // Set up online/offline event listeners
    this.setupOnlineListeners();
    
    // Register service worker
    await this.registerServiceWorker();
    
    // Start offline duration tracking
    this.startOfflineTracking();
    
    // Initialize offline mode based on current status
    this.updateOfflineMode();
  }

  private setupOnlineListeners(): void {
    const updateOnlineStatus = () => {
      const isOnline = navigator.onLine;
      useOfflineStore.getState().setOnlineStatus(isOnline);
      
      if (isOnline) {
        console.log('[OfflineService] Connection restored');
        this.handleConnectionRestored();
      } else {
        console.log('[OfflineService] Connection lost');
        this.handleConnectionLost();
      }
      
      this.updateOfflineMode();
    };

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial status check
    updateOnlineStatus();
  }

  private async registerServiceWorker(): Promise<void> {
    if (!('serviceWorker' in navigator)) {
      console.warn('[OfflineService] Service Worker not supported');
      useOfflineStore.getState().setServiceWorkerStatus(false, false);
      return;
    }

    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      });

      this.serviceWorkerRegistration = registration;
      useOfflineStore.getState().setServiceWorkerStatus(true, true);

      console.log('[OfflineService] Service Worker registered successfully');

      // Handle service worker updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('[OfflineService] New service worker available');
              this.notifyServiceWorkerUpdate();
            }
          });
        }
      });

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', this.handleServiceWorkerMessage.bind(this));

    } catch (error) {
      console.error('[OfflineService] Service Worker registration failed:', error);
      useOfflineStore.getState().setServiceWorkerStatus(true, false);
    }
  }

  private handleServiceWorkerMessage(event: MessageEvent): void {
    const { type, data } = event.data;
    
    switch (type) {
      case 'CACHE_STATUS':
        console.log('[OfflineService] Cache status:', data);
        break;
      case 'SYNC_COMPLETE':
        console.log('[OfflineService] Background sync completed');
        this.handleSyncComplete(data);
        break;
      case 'OFFLINE_FALLBACK':
        console.log('[OfflineService] Serving offline fallback');
        break;
    }
  }

  private startOfflineTracking(): void {
    this.offlineCheckInterval = setInterval(() => {
      const state = useOfflineStore.getState();
      
      if (!state.isOnline && state.lastOnlineTime) {
        const offlineDuration = Date.now() - state.lastOnlineTime.getTime();
        useOfflineStore.setState({ offlineDuration });
      }
    }, 1000);
  }

  private updateOfflineMode(): void {
    const { isOnline, isServiceWorkerRegistered } = useOfflineStore.getState();
    
    let mode: 'full' | 'limited' | 'read-only';
    
    if (isOnline) {
      mode = 'full';
    } else if (isServiceWorkerRegistered) {
      mode = 'limited';
    } else {
      mode = 'read-only';
    }
    
    useOfflineStore.getState().updateOfflineMode(mode);
  }

  private handleConnectionLost(): void {
    // Notify user about offline status
    this.showOfflineNotification();
    
    // Switch to offline mode
    this.updateOfflineMode();
  }

  private handleConnectionRestored(): void {
    // Notify user about restored connection
    this.showOnlineNotification();
    
    // Trigger background sync if service worker is available
    if (this.serviceWorkerRegistration) {
      this.triggerBackgroundSync();
    }
    
    // Process queued actions
    this.processQueuedActions();
  }

  private handleSyncComplete(data: any): void {
    // Remove successfully synced actions from queue
    if (data.syncedActions) {
      data.syncedActions.forEach((actionId: string) => {
        useOfflineStore.getState().removeQueuedAction(actionId);
      });
    }
  }

  private showOfflineNotification(): void {
    // This would integrate with your notification system
    console.log('[OfflineService] Showing offline notification');
  }

  private showOnlineNotification(): void {
    // This would integrate with your notification system
    console.log('[OfflineService] Showing online notification');
  }

  private notifyServiceWorkerUpdate(): void {
    // Notify user about available update
    console.log('[OfflineService] Service worker update available');
  }

  private async triggerBackgroundSync(): Promise<void> {
    if (this.serviceWorkerRegistration && 'sync' in this.serviceWorkerRegistration) {
      try {
        // @ts-ignore - Background Sync API may not be in TypeScript definitions
        await this.serviceWorkerRegistration.sync.register('trading-actions');
        console.log('[OfflineService] Background sync registered');
      } catch (error) {
        console.error('[OfflineService] Background sync registration failed:', error);
      }
    }
  }

  private async processQueuedActions(): Promise<void> {
    const { queuedActions } = useOfflineStore.getState();
    
    for (const action of queuedActions) {
      try {
        await this.retryAction(action);
      } catch (error) {
        console.error('[OfflineService] Failed to retry action:', action.id, error);
        
        if (action.retryCount >= action.maxRetries) {
          console.warn('[OfflineService] Max retries reached for action:', action.id);
          useOfflineStore.getState().removeQueuedAction(action.id);
        } else {
          useOfflineStore.getState().incrementRetryCount(action.id);
        }
      }
    }
  }

  private async retryAction(action: QueuedAction): Promise<void> {
    // This would integrate with your API service to retry the action
    console.log('[OfflineService] Retrying action:', action.id);
    
    // Simulate API call
    const response = await fetch(`/api/${action.type}/${action.action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action.data),
    });
    
    if (response.ok) {
      useOfflineStore.getState().removeQueuedAction(action.id);
      console.log('[OfflineService] Action retried successfully:', action.id);
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  // Public methods for queuing actions
  queueTradingAction(action: string, data: any, maxRetries: number = 3): void {
    useOfflineStore.getState().addQueuedAction({
      type: 'trade',
      action,
      data,
      maxRetries,
    });
  }

  queueConfigAction(action: string, data: any, maxRetries: number = 3): void {
    useOfflineStore.getState().addQueuedAction({
      type: 'config',
      action,
      data,
      maxRetries,
    });
  }

  queueSystemAction(action: string, data: any, maxRetries: number = 3): void {
    useOfflineStore.getState().addQueuedAction({
      type: 'system',
      action,
      data,
      maxRetries,
    });
  }

  // Cache management
  async clearCache(cacheName?: string): Promise<void> {
    if (this.serviceWorkerRegistration) {
      navigator.serviceWorker.controller?.postMessage({
        type: 'CLEAR_CACHE',
        data: { cacheName },
      });
    }
  }

  async getCacheStatus(): Promise<Record<string, number>> {
    return new Promise((resolve) => {
      if (this.serviceWorkerRegistration && navigator.serviceWorker.controller) {
        const channel = new MessageChannel();
        
        channel.port1.onmessage = (event) => {
          if (event.data.type === 'CACHE_STATUS') {
            resolve(event.data.data);
          }
        };
        
        navigator.serviceWorker.controller.postMessage(
          { type: 'GET_CACHE_STATUS' },
          [channel.port2]
        );
      } else {
        resolve({});
      }
    });
  }

  // Cleanup
  destroy(): void {
    if (this.offlineCheckInterval) {
      clearInterval(this.offlineCheckInterval);
    }
  }
}

export const offlineService = new OfflineService();