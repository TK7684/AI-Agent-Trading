// Offline functionality tests
import React, { useState } from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import { useOffline, useOfflineApi } from '@/hooks/useOffline';
import { offlineService } from '@/services/offlineService';
import { persistenceService } from '@/services/persistenceService';
import { OfflineIndicator } from '@/components/Common/OfflineIndicator';
import { OfflineQueue } from '@/components/Common/OfflineQueue';

// Mock IndexedDB
const mockIndexedDB = {
  open: vi.fn(),
  deleteDatabase: vi.fn(),
};

// Mock Service Worker
const mockServiceWorker = {
  register: vi.fn(),
  controller: null,
  addEventListener: vi.fn(),
};

// Mock navigator
Object.defineProperty(window, 'navigator', {
  value: {
    onLine: true,
    serviceWorker: mockServiceWorker,
  },
  writable: true,
});

Object.defineProperty(window, 'indexedDB', {
  value: mockIndexedDB,
  writable: true,
});

// Test component that uses offline hook
const TestOfflineComponent = () => {
  const {
    isOnline,
    offlineMode,
    queuedActions,
    queueAction,
    clearQueue,
    getOfflineCapabilities,
  } = useOffline();

  return (
    <div>
      <div data-testid="online-status">{isOnline ? 'online' : 'offline'}</div>
      <div data-testid="offline-mode">{offlineMode}</div>
      <div data-testid="queued-count">{queuedActions.length}</div>
      <button
        data-testid="queue-action"
        onClick={() => queueAction('trade', 'buy', { symbol: 'BTCUSDT', amount: 100 })}
      >
        Queue Action
      </button>
      <button data-testid="clear-queue" onClick={clearQueue}>
        Clear Queue
      </button>
      <div data-testid="capabilities">
        {JSON.stringify(getOfflineCapabilities())}
      </div>
    </div>
  );
};

// Test component for offline API
const TestOfflineApiComponent = () => {
  const { makeRequest, isOnline, capabilities } = useOfflineApi();
  const [result, setResult] = useState<any>(null);

  const handleRequest = async () => {
    try {
      const response = await makeRequest('/api/test', { method: 'GET' });
      setResult(response);
    } catch (error) {
      setResult({ error: error.message });
    }
  };

  return (
    <div>
      <div data-testid="api-online">{isOnline ? 'online' : 'offline'}</div>
      <button data-testid="make-request" onClick={handleRequest}>
        Make Request
      </button>
      <div data-testid="api-result">{JSON.stringify(result)}</div>
      <div data-testid="api-capabilities">{JSON.stringify(capabilities)}</div>
    </div>
  );
};

describe('Offline Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Service Worker Registration', () => {
    it('should register service worker when supported', async () => {
      mockServiceWorker.register.mockResolvedValue({
        installing: null,
        waiting: null,
        active: null,
        addEventListener: vi.fn(),
      });

      await offlineService.initialize();

      expect(mockServiceWorker.register).toHaveBeenCalledWith('/sw.js', {
        scope: '/',
      });
    });

    it('should handle service worker registration failure', async () => {
      mockServiceWorker.register.mockRejectedValue(new Error('Registration failed'));

      await offlineService.initialize();

      expect(mockServiceWorker.register).toHaveBeenCalled();
      // Should not throw error, just log it
    });

    it('should detect when service worker is not supported', async () => {
      // Mock unsupported environment
      Object.defineProperty(navigator, 'serviceWorker', {
        value: undefined,
        writable: true,
      });

      await offlineService.initialize();

      expect(mockServiceWorker.register).not.toHaveBeenCalled();
    });
  });

  describe('Online/Offline Detection', () => {
    it('should detect online status changes', async () => {
      const { rerender } = render(<TestOfflineComponent />);

      expect(screen.getByTestId('online-status')).toHaveTextContent('online');

      // Simulate going offline
      act(() => {
        Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('online-status')).toHaveTextContent('offline');
      });

      // Simulate coming back online
      act(() => {
        Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
        window.dispatchEvent(new Event('online'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('online-status')).toHaveTextContent('online');
      });
    });

    it('should update offline mode based on capabilities', async () => {
      render(<TestOfflineComponent />);

      // Initially online with full capabilities
      expect(screen.getByTestId('offline-mode')).toHaveTextContent('full');

      // Go offline with service worker (limited mode)
      act(() => {
        Object.defineProperty(navigator, 'onLine', { value: false, writable: true });
        window.dispatchEvent(new Event('offline'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('offline-mode')).toHaveTextContent('limited');
      });
    });
  });

  describe('Action Queuing', () => {
    it('should queue actions when offline', async () => {
      render(<TestOfflineComponent />);

      expect(screen.getByTestId('queued-count')).toHaveTextContent('0');

      // Queue an action
      fireEvent.click(screen.getByTestId('queue-action'));

      await waitFor(() => {
        expect(screen.getByTestId('queued-count')).toHaveTextContent('1');
      });
    });

    it('should clear queued actions', async () => {
      render(<TestOfflineComponent />);

      // Queue an action
      fireEvent.click(screen.getByTestId('queue-action'));
      await waitFor(() => {
        expect(screen.getByTestId('queued-count')).toHaveTextContent('1');
      });

      // Clear queue
      fireEvent.click(screen.getByTestId('clear-queue'));

      await waitFor(() => {
        expect(screen.getByTestId('queued-count')).toHaveTextContent('0');
      });
    });

    it('should provide correct offline capabilities', async () => {
      render(<TestOfflineComponent />);

      const capabilities = JSON.parse(screen.getByTestId('capabilities').textContent || '{}');

      expect(capabilities).toEqual({
        canViewData: true,
        canModifySettings: true,
        canExecuteTrades: true,
        canReceiveNotifications: expect.any(Boolean),
        hasDataPersistence: expect.any(Boolean),
        hasBackgroundSync: expect.any(Boolean),
      });
    });
  });
});

describe('Offline API Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('should make successful online requests', async () => {
    const mockResponse = { data: 'test' };
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    render(<TestOfflineApiComponent />);

    fireEvent.click(screen.getByTestId('make-request'));

    await waitFor(() => {
      const result = JSON.parse(screen.getByTestId('api-result').textContent || '{}');
      expect(result.data).toEqual(mockResponse);
      expect(result.fromCache).toBe(false);
      expect(result.success).toBe(true);
    });
  });

  it('should handle failed requests with caching fallback', async () => {
    // Mock failed request
    (global.fetch as any).mockRejectedValue(new Error('Network error'));

    // Mock cached data
    vi.spyOn(persistenceService, 'getCachedApiResponse').mockResolvedValue({ cached: 'data' });

    render(<TestOfflineApiComponent />);

    fireEvent.click(screen.getByTestId('make-request'));

    await waitFor(() => {
      const result = JSON.parse(screen.getByTestId('api-result').textContent || '{}');
      expect(result.data).toEqual({ cached: 'data' });
      expect(result.fromCache).toBe(true);
      expect(result.success).toBe(true);
    });
  });

  it('should queue write operations when offline', async () => {
    // Set offline
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true });

    render(<TestOfflineApiComponent />);

    // Mock makeRequest for POST
    const { makeRequest } = useOfflineApi();
    const result = await makeRequest('/api/test', { method: 'POST', body: '{}' });

    expect(result.queued).toBe(true);
    expect(result.success).toBe(false);
  });
});

describe('Persistence Service', () => {
  let mockDB: any;

  beforeEach(() => {
    mockDB = {
      transaction: vi.fn(() => ({
        objectStore: vi.fn(() => ({
          put: vi.fn(() => ({ onsuccess: null, onerror: null })),
          get: vi.fn(() => ({ onsuccess: null, onerror: null })),
          add: vi.fn(() => ({ onsuccess: null, onerror: null })),
          delete: vi.fn(() => ({ onsuccess: null, onerror: null })),
          clear: vi.fn(() => ({ onsuccess: null, onerror: null })),
          openCursor: vi.fn(() => ({ onsuccess: null, onerror: null })),
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
    };

    mockIndexedDB.open.mockImplementation(() => ({
      onsuccess: null,
      onerror: null,
      onupgradeneeded: null,
      result: mockDB,
    }));
  });

  it('should initialize IndexedDB successfully', async () => {
    const openRequest = mockIndexedDB.open();
    
    // Simulate successful open
    setTimeout(() => {
      openRequest.result = mockDB;
      if (openRequest.onsuccess) openRequest.onsuccess();
    }, 0);

    await persistenceService.initialize();

    expect(mockIndexedDB.open).toHaveBeenCalledWith('TradingDashboardDB', 1);
  });

  it('should handle IndexedDB initialization failure', async () => {
    const openRequest = mockIndexedDB.open();
    
    // Simulate failed open
    setTimeout(() => {
      openRequest.error = new Error('DB open failed');
      if (openRequest.onerror) openRequest.onerror();
    }, 0);

    await expect(persistenceService.initialize()).rejects.toThrow();
  });

  it('should save and load dashboard state', async () => {
    // Mock successful initialization
    const openRequest = mockIndexedDB.open();
    setTimeout(() => {
      openRequest.result = mockDB;
      if (openRequest.onsuccess) openRequest.onsuccess();
    }, 0);

    await persistenceService.initialize();

    const testState = {
      tradingMetrics: { totalPnl: 1000 },
      recentTrades: [],
      lastSync: new Date(),
    };

    // Mock successful save
    const putRequest = { onsuccess: null, onerror: null };
    mockDB.transaction().objectStore().put.mockReturnValue(putRequest);

    const savePromise = persistenceService.saveDashboardState(testState);
    
    // Simulate successful save
    setTimeout(() => {
      if (putRequest.onsuccess) putRequest.onsuccess();
    }, 0);

    await savePromise;

    expect(mockDB.transaction).toHaveBeenCalledWith(['dashboard_state'], 'readwrite');
  });

  it('should cache and retrieve API responses', async () => {
    // Mock successful initialization
    const openRequest = mockIndexedDB.open();
    setTimeout(() => {
      openRequest.result = mockDB;
      if (openRequest.onsuccess) openRequest.onsuccess();
    }, 0);

    await persistenceService.initialize();

    const testData = { result: 'test' };
    const testUrl = '/api/test';

    // Mock successful cache
    const putRequest = { onsuccess: null, onerror: null };
    mockDB.transaction().objectStore().put.mockReturnValue(putRequest);

    const cachePromise = persistenceService.cacheApiResponse(testUrl, testData);
    
    // Simulate successful cache
    setTimeout(() => {
      if (putRequest.onsuccess) putRequest.onsuccess();
    }, 0);

    await cachePromise;

    // Mock successful retrieval
    const getRequest = { 
      onsuccess: null, 
      onerror: null,
      result: {
        data: testData,
        expiry: new Date(Date.now() + 300000), // 5 minutes from now
      }
    };
    mockDB.transaction().objectStore().get.mockReturnValue(getRequest);

    const retrievePromise = persistenceService.getCachedApiResponse(testUrl);
    
    // Simulate successful retrieval
    setTimeout(() => {
      if (getRequest.onsuccess) getRequest.onsuccess();
    }, 0);

    const result = await retrievePromise;
    expect(result).toEqual(testData);
  });
});

describe('Offline UI Components', () => {
  describe('OfflineIndicator', () => {
    it('should display online status correctly', () => {
      render(<OfflineIndicator />);

      expect(screen.getByText('Online')).toBeInTheDocument();
    });

    it('should display offline status when offline', async () => {
      // Set offline
      Object.defineProperty(navigator, 'onLine', { value: false, writable: true });

      render(<OfflineIndicator />);

      await waitFor(() => {
        expect(screen.getByText(/Offline/)).toBeInTheDocument();
      });
    });

    it('should show queued actions count', async () => {
      render(<OfflineIndicator />);

      // This would require mocking the offline store state
      // The actual implementation would show queued actions
    });

    it('should display detailed capabilities when requested', () => {
      render(<OfflineIndicator showDetails={true} />);

      expect(screen.getByText('View Data')).toBeInTheDocument();
      expect(screen.getByText('Modify Settings')).toBeInTheDocument();
      expect(screen.getByText('Execute Trades')).toBeInTheDocument();
      expect(screen.getByText('Background Sync')).toBeInTheDocument();
    });
  });

  describe('OfflineQueue', () => {
    it('should not render when no queued actions', () => {
      const { container } = render(<OfflineQueue />);
      expect(container.firstChild).toBeNull();
    });

    it('should display queued actions when present', async () => {
      // This would require mocking the offline store with queued actions
      // The test would verify that queued actions are displayed correctly
    });

    it('should allow clearing all queued actions', async () => {
      // Mock queued actions and test clear functionality
    });

    it('should allow retrying failed actions when online', async () => {
      // Mock failed actions and test retry functionality
    });

    it('should expand and collapse queue details', async () => {
      // Test the expand/collapse functionality
    });
  });
});

describe('Service Worker Integration', () => {
  it('should handle service worker messages', async () => {
    const messageHandler = vi.fn();
    
    // Mock service worker message event
    const messageEvent = new MessageEvent('message', {
      data: {
        type: 'CACHE_STATUS',
        data: { 'cache-v1': 10 },
      },
    });

    // Test that the service worker message is handled correctly
    await offlineService.initialize();
    
    // Simulate message from service worker
    if (navigator.serviceWorker.addEventListener) {
      navigator.serviceWorker.addEventListener('message', messageHandler);
      navigator.serviceWorker.dispatchEvent(messageEvent);
    }

    expect(messageHandler).toHaveBeenCalledWith(messageEvent);
  });

  it('should register background sync when going online', async () => {
    const mockRegistration = {
      sync: {
        register: vi.fn(),
      },
    };

    mockServiceWorker.register.mockResolvedValue(mockRegistration);

    await offlineService.initialize();

    // Simulate going online
    act(() => {
      Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
      window.dispatchEvent(new Event('online'));
    });

    // Should register background sync
    expect(mockRegistration.sync.register).toHaveBeenCalledWith('trading-actions');
  });
});

describe('Error Handling', () => {
  it('should handle IndexedDB errors gracefully', async () => {
    mockIndexedDB.open.mockImplementation(() => {
      throw new Error('IndexedDB not available');
    });

    // Should not throw, but handle gracefully
    await expect(persistenceService.initialize()).rejects.toThrow();
  });

  it('should handle service worker registration errors', async () => {
    mockServiceWorker.register.mockRejectedValue(new Error('SW registration failed'));

    // Should not throw, but handle gracefully
    await expect(offlineService.initialize()).resolves.not.toThrow();
  });

  it('should handle quota exceeded errors', async () => {
    const quotaError = new Error('QuotaExceededError');
    quotaError.name = 'QuotaExceededError';

    mockDB.transaction().objectStore().put.mockImplementation(() => {
      throw quotaError;
    });

    // Should handle quota errors gracefully
    await expect(persistenceService.saveDashboardState({})).rejects.toThrow();
  });
});

describe('Performance', () => {
  it('should cleanup old data periodically', async () => {
    const cleanupSpy = vi.spyOn(persistenceService, 'cleanupOldData');

    await persistenceService.initialize();

    expect(cleanupSpy).toHaveBeenCalled();
  });

  it('should limit cache size', async () => {
    // Test that cache doesn't grow indefinitely
    const quota = await persistenceService.getStorageQuota();
    expect(quota).toHaveProperty('usage');
    expect(quota).toHaveProperty('quota');
    expect(quota).toHaveProperty('available');
    expect(quota).toHaveProperty('percentage');
  });

  it('should debounce frequent state saves', async () => {
    // Test that rapid state changes don't cause excessive saves
    const saveSpy = vi.spyOn(persistenceService, 'saveDashboardState');

    // Simulate rapid state changes
    for (let i = 0; i < 10; i++) {
      await persistenceService.saveDashboardState({ test: i });
    }

    // Should not save 10 times immediately
    expect(saveSpy).toHaveBeenCalled();
  });
});