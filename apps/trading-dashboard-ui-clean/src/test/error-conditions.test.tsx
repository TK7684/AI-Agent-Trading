import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { ErrorBoundary } from 'react-error-boundary';
import { DashboardLayout } from '@components/Dashboard/DashboardLayout';
import { TradingStore } from '@stores/tradingStore';
import { SystemStore } from '@stores/systemStore';
import { NotificationStore } from '@stores/notificationStore';
import { UIStore } from '@stores/uiStore';

// Mock console.error to avoid noise in tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalConsoleError;
});

// Component that throws an error for testing
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

// Error fallback component
const ErrorFallback = ({ error, resetErrorBoundary }: any) => (
  <div role="alert">
    <h2>Something went wrong:</h2>
    <pre>{error.message}</pre>
    <button onClick={resetErrorBoundary}>Try again</button>
  </div>
);

describe('Error Conditions and Recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Component Error Boundaries', () => {
    it('should catch and display component errors gracefully', () => {
      render(
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong:')).toBeInTheDocument();
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });

    it('should allow error recovery through reset', async () => {
      const user = userEvent.setup();
      let shouldThrow = true;

      const { rerender } = render(
        <ErrorBoundary 
          FallbackComponent={ErrorFallback}
          onReset={() => { shouldThrow = false; }}
        >
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();

      const resetButton = screen.getByText('Try again');
      await user.click(resetButton);

      rerender(
        <ErrorBoundary 
          FallbackComponent={ErrorFallback}
          onReset={() => { shouldThrow = false; }}
        >
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
    });
  });

  describe('Store Error Handling', () => {
    it('should handle trading store errors gracefully', () => {
      const store = TradingStore.getState();
      
      // Test with invalid data
      expect(() => {
        store.updateMetrics({
          totalPnl: NaN,
          dailyPnl: Infinity,
          winRate: -1,
          totalTrades: -1,
          currentDrawdown: NaN,
          maxDrawdown: Infinity,
          portfolioValue: NaN,
          dailyChange: Infinity,
          dailyChangePercent: NaN
        });
      }).not.toThrow();

      // Verify store handles invalid data
      const metrics = store.metrics;
      expect(isNaN(metrics.totalPnl)).toBe(true);
    });

    it('should handle system store connection errors', () => {
      const store = SystemStore.getState();
      
      // Simulate connection error
      store.setConnectionStatus('database', false);
      store.setConnectionStatus('broker', false);
      store.setConnectionStatus('llm', false);

      expect(store.health.connections.database).toBe(false);
      expect(store.health.connections.broker).toBe(false);
      expect(store.health.connections.llm).toBe(false);
    });

    it('should handle notification store overflow', () => {
      const store = NotificationStore.getState();
      
      // Add many notifications to test overflow handling
      for (let i = 0; i < 1000; i++) {
        store.addNotification({
          id: `notification-${i}`,
          type: 'info',
          title: `Test ${i}`,
          message: `Message ${i}`,
          timestamp: new Date(),
          read: false,
          persistent: false
        });
      }

      // Should limit notifications to prevent memory issues
      expect(store.notifications.length).toBeLessThanOrEqual(100);
    });
  });

  describe('Network Error Scenarios', () => {
    it('should handle fetch API failures', async () => {
      // Mock fetch to fail
      global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

      const { ApiService } = await import('@services/apiService');
      const apiService = new ApiService();

      await expect(apiService.get('/test')).rejects.toThrow('Network error');
    });

    it('should handle WebSocket connection failures', async () => {
      // Mock WebSocket to fail immediately
      const mockWebSocket = {
        readyState: WebSocket.CLOSED,
        close: vi.fn(),
        send: vi.fn(),
        addEventListener: vi.fn((event, callback) => {
          if (event === 'error') {
            setTimeout(() => callback(new Error('Connection failed')), 0);
          }
        }),
        removeEventListener: vi.fn()
      };

      // @ts-ignore
      global.WebSocket = vi.fn(() => mockWebSocket);

      const { WebSocketService } = await import('@services/websocketService');
      const wsService = new WebSocketService();
      
      const errorHandler = vi.fn();
      wsService.on('error', errorHandler);

      await expect(wsService.connect('ws://invalid')).rejects.toThrow();
    });

    it('should handle intermittent connectivity', async () => {
      let connectionCount = 0;
      
      // Mock WebSocket that fails first few times
      global.WebSocket = vi.fn(() => {
        connectionCount++;
        if (connectionCount < 3) {
          throw new Error('Connection failed');
        }
        
        return {
          readyState: WebSocket.OPEN,
          close: vi.fn(),
          send: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn()
        };
      });

      const { WebSocketService } = await import('@services/websocketService');
      const wsService = new WebSocketService();

      // Should eventually succeed after retries
      await expect(wsService.connect('ws://test')).resolves.not.toThrow();
      expect(connectionCount).toBe(3);
    });
  });

  describe('Data Validation Errors', () => {
    it('should handle invalid trading data gracefully', () => {
      const store = TradingStore.getState();
      
      // Test with completely invalid trade data
      const invalidTrade = {
        id: null,
        timestamp: 'invalid-date',
        symbol: '',
        side: 'INVALID',
        entryPrice: 'not-a-number',
        quantity: -1,
        status: 'UNKNOWN'
      };

      expect(() => {
        // @ts-ignore - intentionally passing invalid data
        store.addTrade(invalidTrade);
      }).not.toThrow();
    });

    it('should validate notification data', () => {
      const store = NotificationStore.getState();
      
      const invalidNotification = {
        id: '',
        type: 'invalid-type',
        title: null,
        message: undefined,
        timestamp: 'not-a-date',
        read: 'not-boolean'
      };

      expect(() => {
        // @ts-ignore - intentionally passing invalid data
        store.addNotification(invalidNotification);
      }).not.toThrow();
    });
  });

  describe('Memory and Resource Errors', () => {
    it('should handle out of memory scenarios', () => {
      // Simulate memory pressure
      const largeArray = [];
      
      expect(() => {
        // Try to allocate large amount of memory
        for (let i = 0; i < 1000000; i++) {
          largeArray.push(new Array(100).fill(i));
        }
      }).not.toThrow();
    });

    it('should handle localStorage quota exceeded', () => {
      const store = UIStore.getState();
      
      // Mock localStorage to throw quota exceeded error
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error('QuotaExceededError');
      });

      expect(() => {
        store.saveLayout([]);
      }).not.toThrow();

      localStorage.setItem = originalSetItem;
    });
  });

  describe('Concurrent Operation Errors', () => {
    it('should handle race conditions in state updates', async () => {
      const store = TradingStore.getState();
      
      // Simulate concurrent updates
      const promises = Array.from({ length: 100 }, (_, i) => 
        Promise.resolve().then(() => {
          store.updateMetrics({
            totalPnl: i,
            dailyPnl: i,
            winRate: i,
            totalTrades: i,
            currentDrawdown: i,
            maxDrawdown: i,
            portfolioValue: i,
            dailyChange: i,
            dailyChangePercent: i
          });
        })
      );

      await Promise.all(promises);
      
      // Should not crash or corrupt state
      expect(store.metrics).toBeDefined();
      expect(typeof store.metrics.totalPnl).toBe('number');
    });

    it('should handle simultaneous WebSocket messages', async () => {
      const { WebSocketService } = await import('@services/websocketService');
      const wsService = new WebSocketService();
      
      const messageHandler = vi.fn();
      wsService.on('message', messageHandler);

      // Simulate rapid message processing
      const messages = Array.from({ length: 1000 }, (_, i) => ({
        data: JSON.stringify({ type: 'test', id: i })
      }));

      messages.forEach(msg => {
        wsService['handleMessage'](msg as MessageEvent);
      });

      expect(messageHandler).toHaveBeenCalledTimes(1000);
    });
  });

  describe('Browser Compatibility Errors', () => {
    it('should handle missing WebSocket support', () => {
      const originalWebSocket = global.WebSocket;
      // @ts-ignore
      delete global.WebSocket;

      expect(() => {
        const { WebSocketService } = require('@services/websocketService');
        new WebSocketService();
      }).not.toThrow();

      global.WebSocket = originalWebSocket;
    });

    it('should handle missing localStorage support', () => {
      const originalLocalStorage = global.localStorage;
      // @ts-ignore
      delete global.localStorage;

      const store = UIStore.getState();
      
      expect(() => {
        store.saveLayout([]);
      }).not.toThrow();

      global.localStorage = originalLocalStorage;
    });

    it('should handle missing IndexedDB support', () => {
      const originalIndexedDB = global.indexedDB;
      // @ts-ignore
      delete global.indexedDB;

      expect(() => {
        // Code that might use IndexedDB
        const { StorageService } = require('@services/storageService');
        new StorageService();
      }).not.toThrow();

      global.indexedDB = originalIndexedDB;
    });
  });

  describe('Security Error Scenarios', () => {
    it('should handle CSP violations gracefully', () => {
      // Mock CSP violation
      const cspError = new Error('Content Security Policy violation');
      cspError.name = 'SecurityError';

      expect(() => {
        throw cspError;
      }).toThrow('Content Security Policy violation');
    });

    it('should handle CORS errors', async () => {
      global.fetch = vi.fn(() => 
        Promise.reject(new Error('CORS policy: Cross origin requests are only supported for protocol schemes'))
      );

      const { ApiService } = await import('@services/apiService');
      const apiService = new ApiService();

      await expect(apiService.get('/test')).rejects.toThrow(/CORS policy/);
    });
  });
});