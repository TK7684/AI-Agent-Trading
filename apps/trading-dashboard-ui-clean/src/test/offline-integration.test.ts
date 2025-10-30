// Offline integration test
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Offline Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock navigator
    Object.defineProperty(window, 'navigator', {
      value: {
        onLine: true,
        serviceWorker: {
          register: vi.fn(() => Promise.resolve({
            installing: null,
            waiting: null,
            active: null,
            addEventListener: vi.fn(),
          })),
          controller: null,
          addEventListener: vi.fn(),
        },
      },
      writable: true,
    });

    // Mock IndexedDB
    Object.defineProperty(window, 'indexedDB', {
      value: {
        open: vi.fn(() => ({
          onsuccess: null,
          onerror: null,
          onupgradeneeded: null,
          result: {
            transaction: vi.fn(() => ({
              objectStore: vi.fn(() => ({
                put: vi.fn(() => ({ onsuccess: null, onerror: null })),
                get: vi.fn(() => ({ onsuccess: null, onerror: null })),
                createIndex: vi.fn(),
              })),
            })),
            createObjectStore: vi.fn(() => ({
              createIndex: vi.fn(),
            })),
            objectStoreNames: {
              contains: vi.fn(() => false),
            },
            close: vi.fn(),
          },
        })),
      },
      writable: true,
    });
  });

  it('should initialize offline services successfully', async () => {
    const { offlineService } = await import('@/services/offlineService');
    
    // Should not throw
    await expect(offlineService.initialize()).resolves.not.toThrow();
    
    expect(navigator.serviceWorker.register).toHaveBeenCalledWith('/sw.js', {
      scope: '/',
    });
  });

  it('should detect online/offline status changes', () => {
    // Initially online
    expect(navigator.onLine).toBe(true);
    
    // Simulate going offline
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
    expect(navigator.onLine).toBe(false);
    
    // Simulate going back online
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    expect(navigator.onLine).toBe(true);
  });

  it('should support service worker registration', () => {
    expect('serviceWorker' in navigator).toBe(true);
    expect(typeof navigator.serviceWorker.register).toBe('function');
  });

  it('should support IndexedDB', () => {
    expect('indexedDB' in window).toBe(true);
    expect(typeof window.indexedDB.open).toBe('function');
  });

  it('should handle offline queue operations', async () => {
    const { useOfflineStore } = await import('@/services/offlineService');
    
    const store = useOfflineStore.getState();
    
    // Initially no queued actions
    expect(store.queuedActions).toHaveLength(0);
    
    // Add a queued action
    store.addQueuedAction({
      type: 'trade',
      action: 'buy',
      data: { symbol: 'BTCUSDT', amount: 100 },
      maxRetries: 3,
    });
    
    // Should have one queued action
    expect(useOfflineStore.getState().queuedActions).toHaveLength(1);
    
    // Clear queue
    store.clearQueuedActions();
    
    // Should be empty again
    expect(useOfflineStore.getState().queuedActions).toHaveLength(0);
  });

  it('should provide offline capabilities based on status', async () => {
    const { useOfflineStore } = await import('@/services/offlineService');
    
    const store = useOfflineStore.getState();
    
    // When online with service worker
    store.setOnlineStatus(true);
    store.setServiceWorkerStatus(true, true);
    store.updateOfflineMode('full');
    
    expect(store.offlineMode).toBe('full');
    
    // When offline with service worker
    store.setOnlineStatus(false);
    store.updateOfflineMode('limited');
    
    expect(store.offlineMode).toBe('limited');
    
    // When offline without service worker
    store.setServiceWorkerStatus(false, false);
    store.updateOfflineMode('read-only');
    
    expect(store.offlineMode).toBe('read-only');
  });
});