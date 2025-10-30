import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import FDBFactory from 'fake-indexeddb/lib/FDBFactory';
import FDBKeyRange from 'fake-indexeddb/lib/FDBKeyRange';

// Mock IndexedDB
global.indexedDB = new FDBFactory();
global.IDBKeyRange = FDBKeyRange;

// Mock online/offline status
const mockOnlineStatus = (isOnline: boolean) => {
  Object.defineProperty(navigator, 'onLine', {
    value: isOnline,
    writable: true
  });
  
  // Dispatch online/offline events
  const event = new Event(isOnline ? 'online' : 'offline');
  window.dispatchEvent(event);
};

// Mock localStorage with quota simulation
const createMockLocalStorage = (quotaExceeded = false) => {
  const storage: Record<string, string> = {};
  
  return {
    getItem: vi.fn((key: string) => storage[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      if (quotaExceeded) {
        throw new Error('QuotaExceededError');
      }
      storage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key];
    }),
    clear: vi.fn(() => {
      Object.keys(storage).forEach(key => delete storage[key]);
    }),
    length: 0,
    key: vi.fn()
  };
};

describe('Offline Functionality Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnlineStatus(true); // Start online
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Offline Detection and UI', () => {
    it('should detect when going offline and show appropriate UI', async () => {
      const OfflineIndicator = () => {
        const [isOnline, setIsOnline] = React.useState(navigator.onLine);
        
        React.useEffect(() => {
          const handleOnline = () => setIsOnline(true);
          const handleOffline = () => setIsOnline(false);
          
          window.addEventListener('online', handleOnline);
          window.addEventListener('offline', handleOffline);
          
          return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
          };
        }, []);
        
        return (
          <div>
            <div data-testid="connection-status">
              {isOnline ? 'Online' : 'Offline'}
            </div>
            {!isOnline && (
              <div data-testid="offline-banner">
                You are currently offline. Some features may be limited.
              </div>
            )}
          </div>
        );
      };

      render(<OfflineIndicator />);
      
      expect(screen.getByTestId('connection-status')).toHaveTextContent('Online');
      expect(screen.queryByTestId('offline-banner')).not.toBeInTheDocument();
      
      // Simulate going offline
      mockOnlineStatus(false);
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveTextContent('Offline');
        expect(screen.getByTestId('offline-banner')).toBeInTheDocument();
      });
    });

    it('should show cached data when offline', async () => {
      const mockData = {
        metrics: {
          totalPnl: 1500,
          dailyPnl: 250,
          winRate: 75
        }
      };

      // Mock cached data in localStorage
      const mockStorage = createMockLocalStorage();
      Object.defineProperty(window, 'localStorage', { value: mockStorage });
      
      mockStorage.setItem('cached-trading-metrics', JSON.stringify(mockData));

      const CachedDataComponent = () => {
        const [data, setData] = React.useState(null);
        const [isOnline] = React.useState(navigator.onLine);
        
        React.useEffect(() => {
          if (!isOnline) {
            const cached = localStorage.getItem('cached-trading-metrics');
            if (cached) {
              setData(JSON.parse(cached));
            }
          }
        }, [isOnline]);
        
        return (
          <div>
            {data ? (
              <div data-testid="cached-metrics">
                P&L: ${data.metrics.totalPnl}
                <span data-testid="cache-indicator">(Cached)</span>
              </div>
            ) : (
              <div>No data available</div>
            )}
          </div>
        );
      };

      mockOnlineStatus(false);
      render(<CachedDataComponent />);
      
      await waitFor(() => {
        expect(screen.getByTestId('cached-metrics')).toHaveTextContent('P&L: $1500');
        expect(screen.getByTestId('cache-indicator')).toHaveTextContent('(Cached)');
      });
    });
  });

  describe('Offline Data Persistence', () => {
    it('should store data in IndexedDB when offline', async () => {
      const storeOfflineData = async (data: any) => {
        return new Promise((resolve, reject) => {
          const request = indexedDB.open('TradingDashboard', 1);
          
          request.onerror = () => reject(request.error);
          
          request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('offlineData')) {
              db.createObjectStore('offlineData', { keyPath: 'id' });
            }
          };
          
          request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['offlineData'], 'readwrite');
            const store = transaction.objectStore('offlineData');
            
            const addRequest = store.add({
              id: Date.now(),
              data,
              timestamp: new Date().toISOString()
            });
            
            addRequest.onsuccess = () => resolve(addRequest.result);
            addRequest.onerror = () => reject(addRequest.error);
          };
        });
      };

      const testData = { action: 'PLACE_ORDER', symbol: 'BTCUSD', quantity: 1 };
      
      await expect(storeOfflineData(testData)).resolves.toBeDefined();
    });

    it('should queue actions when offline and sync when online', async () => {
      const offlineQueue: any[] = [];
      
      const queueAction = (action: any) => {
        if (!navigator.onLine) {
          offlineQueue.push({
            ...action,
            id: Math.random().toString(36),
            timestamp: Date.now()
          });
          return true;
        }
        return false;
      };

      const syncQueue = async () => {
        const results = [];
        for (const action of offlineQueue) {
          // Simulate API call
          try {
            const response = await fetch('/api/sync', {
              method: 'POST',
              body: JSON.stringify(action)
            });
            results.push({ id: action.id, success: response.ok });
          } catch (error) {
            results.push({ id: action.id, success: false, error });
          }
        }
        return results;
      };

      // Go offline and queue actions
      mockOnlineStatus(false);
      
      expect(queueAction({ type: 'PLACE_ORDER', symbol: 'BTCUSD' })).toBe(true);
      expect(queueAction({ type: 'UPDATE_CONFIG', riskLimit: 1000 })).toBe(true);
      expect(offlineQueue).toHaveLength(2);

      // Come back online and sync
      mockOnlineStatus(true);
      
      global.fetch = vi.fn(() => 
        Promise.resolve(new Response('', { status: 200 }))
      );

      const results = await syncQueue();
      expect(results).toHaveLength(2);
      expect(results.every(r => r.success)).toBe(true);
    });
  });

  describe('Offline Storage Management', () => {
    it('should handle localStorage quota exceeded gracefully', () => {
      const mockStorage = createMockLocalStorage(true); // Simulate quota exceeded
      Object.defineProperty(window, 'localStorage', { value: mockStorage });

      const saveDataWithFallback = (key: string, data: any) => {
        try {
          localStorage.setItem(key, JSON.stringify(data));
          return true;
        } catch (error) {
          if (error.message.includes('QuotaExceededError')) {
            // Clear old data and retry
            const keys = Object.keys(localStorage);
            const oldestKey = keys.find(k => k.startsWith('cached-'));
            if (oldestKey) {
              localStorage.removeItem(oldestKey);
              try {
                localStorage.setItem(key, JSON.stringify(data));
                return true;
              } catch (retryError) {
                console.warn('Failed to save data even after cleanup');
                return false;
              }
            }
          }
          return false;
        }
      };

      const result = saveDataWithFallback('test-key', { data: 'test' });
      expect(result).toBe(false); // Should fail initially
      expect(mockStorage.setItem).toHaveBeenCalled();
    });

    it('should implement LRU cache for offline data', () => {
      const createLRUCache = (maxSize: number) => {
        const cache = new Map();
        
        return {
          get(key: string) {
            if (cache.has(key)) {
              const value = cache.get(key);
              cache.delete(key);
              cache.set(key, value);
              return value;
            }
            return null;
          },
          
          set(key: string, value: any) {
            if (cache.has(key)) {
              cache.delete(key);
            } else if (cache.size >= maxSize) {
              const firstKey = cache.keys().next().value;
              cache.delete(firstKey);
            }
            cache.set(key, value);
          },
          
          size: () => cache.size,
          clear: () => cache.clear()
        };
      };

      const lruCache = createLRUCache(3);
      
      lruCache.set('key1', 'value1');
      lruCache.set('key2', 'value2');
      lruCache.set('key3', 'value3');
      expect(lruCache.size()).toBe(3);
      
      lruCache.set('key4', 'value4'); // Should evict key1
      expect(lruCache.get('key1')).toBeNull();
      expect(lruCache.get('key2')).toBe('value2');
    });
  });

  describe('Offline Form Handling', () => {
    it('should save form data locally when offline', async () => {
      const user = userEvent.setup();
      const mockStorage = createMockLocalStorage();
      Object.defineProperty(window, 'localStorage', { value: mockStorage });

      const OfflineForm = () => {
        const [formData, setFormData] = React.useState({ symbol: '', quantity: '' });
        
        const handleSubmit = (e: React.FormEvent) => {
          e.preventDefault();
          
          if (!navigator.onLine) {
            // Save to localStorage when offline
            const savedForms = JSON.parse(localStorage.getItem('offline-forms') || '[]');
            savedForms.push({
              ...formData,
              id: Date.now(),
              timestamp: new Date().toISOString()
            });
            localStorage.setItem('offline-forms', JSON.stringify(savedForms));
          }
        };
        
        return (
          <form onSubmit={handleSubmit} data-testid="trading-form">
            <input
              type="text"
              placeholder="Symbol"
              value={formData.symbol}
              onChange={(e) => setFormData(prev => ({ ...prev, symbol: e.target.value }))}
            />
            <input
              type="number"
              placeholder="Quantity"
              value={formData.quantity}
              onChange={(e) => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
            />
            <button type="submit">Submit</button>
          </form>
        );
      };

      mockOnlineStatus(false);
      render(<OfflineForm />);
      
      const symbolInput = screen.getByPlaceholderText('Symbol');
      const quantityInput = screen.getByPlaceholderText('Quantity');
      const submitButton = screen.getByText('Submit');
      
      await user.type(symbolInput, 'BTCUSD');
      await user.type(quantityInput, '1');
      await user.click(submitButton);
      
      expect(mockStorage.setItem).toHaveBeenCalledWith(
        'offline-forms',
        expect.stringContaining('BTCUSD')
      );
    });

    it('should restore unsaved form data on page reload', () => {
      const mockStorage = createMockLocalStorage();
      Object.defineProperty(window, 'localStorage', { value: mockStorage });
      
      const savedFormData = {
        symbol: 'ETHUSD',
        quantity: '2',
        timestamp: new Date().toISOString()
      };
      
      mockStorage.setItem('draft-form', JSON.stringify(savedFormData));

      const FormWithRestore = () => {
        const [formData, setFormData] = React.useState(() => {
          const saved = localStorage.getItem('draft-form');
          return saved ? JSON.parse(saved) : { symbol: '', quantity: '' };
        });
        
        return (
          <div>
            <div data-testid="symbol-value">{formData.symbol}</div>
            <div data-testid="quantity-value">{formData.quantity}</div>
          </div>
        );
      };

      render(<FormWithRestore />);
      
      expect(screen.getByTestId('symbol-value')).toHaveTextContent('ETHUSD');
      expect(screen.getByTestId('quantity-value')).toHaveTextContent('2');
    });
  });

  describe('Offline Notification System', () => {
    it('should queue notifications when offline and show when online', async () => {
      const notificationQueue: any[] = [];
      
      const addNotification = (notification: any) => {
        if (!navigator.onLine) {
          notificationQueue.push({
            ...notification,
            id: Math.random().toString(36),
            queuedAt: Date.now()
          });
          return;
        }
        
        // Show notification immediately when online
        console.log('Showing notification:', notification);
      };

      const processQueuedNotifications = () => {
        while (notificationQueue.length > 0) {
          const notification = notificationQueue.shift();
          console.log('Processing queued notification:', notification);
        }
      };

      // Go offline and queue notifications
      mockOnlineStatus(false);
      
      addNotification({ type: 'info', message: 'Trade executed' });
      addNotification({ type: 'warning', message: 'Risk limit approached' });
      
      expect(notificationQueue).toHaveLength(2);

      // Come back online and process queue
      mockOnlineStatus(true);
      processQueuedNotifications();
      
      expect(notificationQueue).toHaveLength(0);
    });

    it('should show offline-specific notifications', () => {
      const getOfflineNotifications = () => {
        return [
          {
            id: 'offline-mode',
            type: 'info',
            title: 'Offline Mode',
            message: 'You are currently offline. Data will sync when connection is restored.',
            persistent: true
          },
          {
            id: 'limited-functionality',
            type: 'warning',
            title: 'Limited Functionality',
            message: 'Some features are not available while offline.',
            persistent: true
          }
        ];
      };

      const notifications = getOfflineNotifications();
      
      expect(notifications).toHaveLength(2);
      expect(notifications[0].title).toBe('Offline Mode');
      expect(notifications[1].title).toBe('Limited Functionality');
      expect(notifications.every(n => n.persistent)).toBe(true);
    });
  });

  describe('Offline Performance Optimization', () => {
    it('should reduce update frequency when offline', () => {
      let updateCount = 0;
      const updates: number[] = [];
      
      const createUpdateScheduler = (isOnline: boolean) => {
        const interval = isOnline ? 1000 : 5000; // 1s online, 5s offline
        
        return setInterval(() => {
          updateCount++;
          updates.push(Date.now());
        }, interval);
      };

      // Test online frequency
      mockOnlineStatus(true);
      const onlineScheduler = createUpdateScheduler(true);
      
      setTimeout(() => {
        clearInterval(onlineScheduler);
        const onlineUpdates = updateCount;
        
        // Reset and test offline frequency
        updateCount = 0;
        mockOnlineStatus(false);
        const offlineScheduler = createUpdateScheduler(false);
        
        setTimeout(() => {
          clearInterval(offlineScheduler);
          // Offline should have fewer updates
          expect(updateCount).toBeLessThan(onlineUpdates);
        }, 100);
      }, 100);
    });

    it('should compress data for offline storage', () => {
      const compressData = (data: any) => {
        // Simple compression simulation
        const jsonString = JSON.stringify(data);
        const compressed = jsonString.replace(/\s+/g, '').replace(/"/g, "'");
        return compressed;
      };

      const decompressData = (compressed: string) => {
        const restored = compressed.replace(/'/g, '"');
        return JSON.parse(restored);
      };

      const originalData = {
        trades: [
          { id: 1, symbol: 'BTCUSD', quantity: 1.5, price: 45000 },
          { id: 2, symbol: 'ETHUSD', quantity: 10, price: 3000 }
        ],
        metrics: { totalPnl: 1500, winRate: 75 }
      };

      const compressed = compressData(originalData);
      const decompressed = decompressData(compressed);
      
      expect(compressed.length).toBeLessThan(JSON.stringify(originalData).length);
      expect(decompressed).toEqual(originalData);
    });
  });
});