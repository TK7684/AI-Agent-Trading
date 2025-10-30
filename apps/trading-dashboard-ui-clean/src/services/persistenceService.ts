// Persistence Service - IndexedDB for critical dashboard state
// Define minimal types for persistence service
interface TradingMetrics {
  totalPnl: number;
  dailyPnl: number;
  winRate: number;
  totalTrades: number;
}

interface TradeLogEntry {
  id: string;
  timestamp: Date;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl?: number;
  status: 'OPEN' | 'CLOSED' | 'CANCELLED';
}

interface SystemHealth {
  cpu: number;
  memory: number;
  diskUsage: number;
  networkLatency: number;
  errorRate: number;
  uptime: number;
}

interface AgentStatus {
  state: 'running' | 'paused' | 'stopped' | 'error';
  uptime: number;
  lastAction: Date;
  activePositions: number;
  dailyTrades: number;
}

interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent: boolean;
}

export interface PersistentState {
  tradingMetrics: TradingMetrics | null;
  recentTrades: TradeLogEntry[];
  systemHealth: SystemHealth | null;
  agentStatus: AgentStatus | null;
  notifications: Notification[];
  userPreferences: Record<string, any>;
  dashboardLayout: any;
  lastSync: Date;
}

export interface StorageQuota {
  usage: number;
  quota: number;
  available: number;
  percentage: number;
}

class PersistenceService {
  private db: IDBDatabase | null = null;
  private readonly dbName = 'TradingDashboardDB';
  private readonly dbVersion = 1;
  private readonly stores = {
    state: 'dashboard_state',
    trades: 'trading_data',
    cache: 'api_cache',
    queue: 'action_queue',
    preferences: 'user_preferences',
  };

  async initialize(): Promise<void> {
    console.log('[PersistenceService] Initializing IndexedDB');
    
    try {
      this.db = await this.openDatabase();
      console.log('[PersistenceService] IndexedDB initialized successfully');
      
      // Clean up old data periodically
      await this.cleanupOldData();
    } catch (error) {
      console.error('[PersistenceService] Failed to initialize IndexedDB:', error);
      throw error;
    }
  }

  private openDatabase(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => {
        reject(new Error(`Failed to open database: ${request.error}`));
      };

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        this.createObjectStores(db);
      };
    });
  }

  private createObjectStores(db: IDBDatabase): void {
    console.log('[PersistenceService] Creating object stores');

    // Dashboard state store
    if (!db.objectStoreNames.contains(this.stores.state)) {
      const stateStore = db.createObjectStore(this.stores.state, { keyPath: 'key' });
      stateStore.createIndex('timestamp', 'timestamp');
      stateStore.createIndex('type', 'type');
    }

    // Trading data store
    if (!db.objectStoreNames.contains(this.stores.trades)) {
      const tradesStore = db.createObjectStore(this.stores.trades, { 
        keyPath: 'id',
        autoIncrement: true 
      });
      tradesStore.createIndex('timestamp', 'timestamp');
      tradesStore.createIndex('symbol', 'symbol');
      tradesStore.createIndex('status', 'status');
    }

    // API cache store
    if (!db.objectStoreNames.contains(this.stores.cache)) {
      const cacheStore = db.createObjectStore(this.stores.cache, { keyPath: 'url' });
      cacheStore.createIndex('timestamp', 'timestamp');
      cacheStore.createIndex('expiry', 'expiry');
    }

    // Action queue store
    if (!db.objectStoreNames.contains(this.stores.queue)) {
      const queueStore = db.createObjectStore(this.stores.queue, { 
        keyPath: 'id',
        autoIncrement: true 
      });
      queueStore.createIndex('timestamp', 'timestamp');
      queueStore.createIndex('type', 'type');
      queueStore.createIndex('status', 'status');
    }

    // User preferences store
    if (!db.objectStoreNames.contains(this.stores.preferences)) {
      const prefsStore = db.createObjectStore(this.stores.preferences, { keyPath: 'key' });
      prefsStore.createIndex('category', 'category');
    }
  }

  // State persistence methods
  async saveDashboardState(state: Partial<PersistentState>): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.state], 'readwrite');
    const store = transaction.objectStore(this.stores.state);

    const stateRecord = {
      key: 'dashboard_state',
      type: 'state',
      data: state,
      timestamp: new Date(),
    };

    return new Promise((resolve, reject) => {
      const request = store.put(stateRecord);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async loadDashboardState(): Promise<PersistentState | null> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.state], 'readonly');
    const store = transaction.objectStore(this.stores.state);

    return new Promise((resolve, reject) => {
      const request = store.get('dashboard_state');
      
      request.onsuccess = () => {
        const result = request.result;
        resolve(result ? result.data : null);
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  // Trading data persistence
  async saveTradingData(trades: TradeLogEntry[]): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.trades], 'readwrite');
    const store = transaction.objectStore(this.stores.trades);

    const promises = trades.map(trade => {
      return new Promise<void>((resolve, reject) => {
        const request = store.put({
          ...trade,
          timestamp: new Date(trade.timestamp),
        });
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });

    await Promise.all(promises);
  }

  async loadTradingData(limit: number = 100): Promise<TradeLogEntry[]> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.trades], 'readonly');
    const store = transaction.objectStore(this.stores.trades);
    const index = store.index('timestamp');

    return new Promise((resolve, reject) => {
      const trades: TradeLogEntry[] = [];
      const request = index.openCursor(null, 'prev'); // Most recent first

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor && trades.length < limit) {
          trades.push(cursor.value);
          cursor.continue();
        } else {
          resolve(trades);
        }
      };

      request.onerror = () => reject(request.error);
    });
  }

  // API cache methods
  async cacheApiResponse(url: string, data: any, ttl: number = 300000): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.cache], 'readwrite');
    const store = transaction.objectStore(this.stores.cache);

    const cacheRecord = {
      url,
      data,
      timestamp: new Date(),
      expiry: new Date(Date.now() + ttl),
    };

    return new Promise((resolve, reject) => {
      const request = store.put(cacheRecord);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async getCachedApiResponse(url: string): Promise<any | null> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.cache], 'readonly');
    const store = transaction.objectStore(this.stores.cache);

    return new Promise((resolve, reject) => {
      const request = store.get(url);
      
      request.onsuccess = () => {
        const result = request.result;
        
        if (!result) {
          resolve(null);
          return;
        }

        // Check if cache is expired
        if (new Date() > new Date(result.expiry)) {
          // Remove expired cache entry
          this.removeCachedApiResponse(url);
          resolve(null);
          return;
        }

        resolve(result.data);
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  async removeCachedApiResponse(url: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.cache], 'readwrite');
    const store = transaction.objectStore(this.stores.cache);

    return new Promise((resolve, reject) => {
      const request = store.delete(url);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // Action queue methods
  async queueAction(action: any): Promise<number> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.queue], 'readwrite');
    const store = transaction.objectStore(this.stores.queue);

    const queueRecord = {
      ...action,
      timestamp: new Date(),
      status: 'pending',
    };

    return new Promise((resolve, reject) => {
      const request = store.add(queueRecord);
      request.onsuccess = () => resolve(request.result as number);
      request.onerror = () => reject(request.error);
    });
  }

  async getQueuedActions(): Promise<any[]> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.queue], 'readonly');
    const store = transaction.objectStore(this.stores.queue);
    const index = store.index('status');

    return new Promise((resolve, reject) => {
      const request = index.getAll('pending');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async updateActionStatus(id: number, status: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.queue], 'readwrite');
    const store = transaction.objectStore(this.stores.queue);

    return new Promise((resolve, reject) => {
      const getRequest = store.get(id);
      
      getRequest.onsuccess = () => {
        const record = getRequest.result;
        if (record) {
          record.status = status;
          record.updatedAt = new Date();
          
          const putRequest = store.put(record);
          putRequest.onsuccess = () => resolve();
          putRequest.onerror = () => reject(putRequest.error);
        } else {
          reject(new Error('Action not found'));
        }
      };
      
      getRequest.onerror = () => reject(getRequest.error);
    });
  }

  // User preferences methods
  async saveUserPreference(key: string, value: any, category: string = 'general'): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.preferences], 'readwrite');
    const store = transaction.objectStore(this.stores.preferences);

    const prefRecord = {
      key,
      value,
      category,
      timestamp: new Date(),
    };

    return new Promise((resolve, reject) => {
      const request = store.put(prefRecord);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async getUserPreference(key: string): Promise<any | null> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.preferences], 'readonly');
    const store = transaction.objectStore(this.stores.preferences);

    return new Promise((resolve, reject) => {
      const request = store.get(key);
      
      request.onsuccess = () => {
        const result = request.result;
        resolve(result ? result.value : null);
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  async getAllUserPreferences(category?: string): Promise<Record<string, any>> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction([this.stores.preferences], 'readonly');
    const store = transaction.objectStore(this.stores.preferences);

    return new Promise((resolve, reject) => {
      const preferences: Record<string, any> = {};
      let request: IDBRequest;

      if (category) {
        const index = store.index('category');
        request = index.openCursor(IDBKeyRange.only(category));
      } else {
        request = store.openCursor();
      }

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor) {
          preferences[cursor.value.key] = cursor.value.value;
          cursor.continue();
        } else {
          resolve(preferences);
        }
      };

      request.onerror = () => reject(request.error);
    });
  }

  // Storage management
  async getStorageQuota(): Promise<StorageQuota> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      const usage = estimate.usage || 0;
      const quota = estimate.quota || 0;
      
      return {
        usage,
        quota,
        available: quota - usage,
        percentage: quota > 0 ? (usage / quota) * 100 : 0,
      };
    }
    
    return {
      usage: 0,
      quota: 0,
      available: 0,
      percentage: 0,
    };
  }

  async cleanupOldData(): Promise<void> {
    if (!this.db) return;

    const cutoffDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago

    try {
      // Clean up old cache entries
      await this.cleanupExpiredCache();
      
      // Clean up old completed actions
      await this.cleanupCompletedActions(cutoffDate);
      
      // Clean up old trading data (keep last 1000 entries)
      await this.cleanupOldTrades(1000);
      
      console.log('[PersistenceService] Cleanup completed');
    } catch (error) {
      console.error('[PersistenceService] Cleanup failed:', error);
    }
  }

  private async cleanupExpiredCache(): Promise<void> {
    if (!this.db) return;

    const transaction = this.db.transaction([this.stores.cache], 'readwrite');
    const store = transaction.objectStore(this.stores.cache);
    const index = store.index('expiry');
    
    const now = new Date();
    const range = IDBKeyRange.upperBound(now);

    return new Promise((resolve, reject) => {
      const request = index.openCursor(range);
      
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  private async cleanupCompletedActions(cutoffDate: Date): Promise<void> {
    if (!this.db) return;

    const transaction = this.db.transaction([this.stores.queue], 'readwrite');
    const store = transaction.objectStore(this.stores.queue);
    const index = store.index('timestamp');
    
    const range = IDBKeyRange.upperBound(cutoffDate);

    return new Promise((resolve, reject) => {
      const request = index.openCursor(range);
      
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor) {
          const record = cursor.value;
          if (record.status === 'completed' || record.status === 'failed') {
            cursor.delete();
          }
          cursor.continue();
        } else {
          resolve();
        }
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  private async cleanupOldTrades(keepCount: number): Promise<void> {
    if (!this.db) return;

    const transaction = this.db.transaction([this.stores.trades], 'readwrite');
    const store = transaction.objectStore(this.stores.trades);
    const index = store.index('timestamp');

    return new Promise((resolve, reject) => {
      const request = index.openCursor(null, 'prev');
      let count = 0;
      
      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        
        if (cursor) {
          count++;
          if (count > keepCount) {
            cursor.delete();
          }
          cursor.continue();
        } else {
          resolve();
        }
      };
      
      request.onerror = () => reject(request.error);
    });
  }

  // Cleanup and close
  async close(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  async clearAllData(): Promise<void> {
    if (!this.db) return;

    const storeNames = Object.values(this.stores);
    const transaction = this.db.transaction(storeNames, 'readwrite');

    const promises = storeNames.map(storeName => {
      return new Promise<void>((resolve, reject) => {
        const store = transaction.objectStore(storeName);
        const request = store.clear();
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    });

    await Promise.all(promises);
    console.log('[PersistenceService] All data cleared');
  }
}

export const persistenceService = new PersistenceService();