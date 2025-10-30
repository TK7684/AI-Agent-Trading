import { beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Mock server for E2E tests
const server = setupServer(
  // Trading API endpoints
  rest.get('/api/trading/metrics', (req, res, ctx) => {
    return res(ctx.json({
      totalPnl: 1500.50,
      dailyPnl: 250.25,
      winRate: 68.5,
      totalTrades: 42,
      currentDrawdown: 125.75,
      maxDrawdown: 300.00,
      portfolioValue: 15000.00,
      dailyChange: 250.25,
      dailyChangePercent: 1.69
    }));
  }),

  rest.get('/api/trading/logs', (req, res, ctx) => {
    const logs = Array.from({ length: 10 }, (_, i) => ({
      id: `trade-${i}`,
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      symbol: `SYMBOL${i}`,
      side: i % 2 === 0 ? 'LONG' : 'SHORT',
      entryPrice: 100 + i * 10,
      exitPrice: 105 + i * 10,
      quantity: 1 + i * 0.5,
      pnl: (i % 2 === 0 ? 1 : -1) * (50 + i * 10),
      status: 'CLOSED',
      pattern: `pattern-${i}`,
      confidence: 0.8 + i * 0.02
    }));
    
    return res(ctx.json({ logs, total: logs.length }));
  }),

  // System API endpoints
  rest.get('/api/system/health', (req, res, ctx) => {
    return res(ctx.json({
      cpu: 45.2,
      memory: 62.8,
      diskUsage: 35.1,
      networkLatency: 25,
      errorRate: 0.02,
      uptime: 86400000,
      connections: {
        database: true,
        broker: true,
        llm: true
      }
    }));
  }),

  rest.get('/api/system/status', (req, res, ctx) => {
    return res(ctx.json({
      state: 'running',
      uptime: 3600000,
      lastAction: new Date().toISOString(),
      activePositions: 3,
      dailyTrades: 15
    }));
  }),

  // Agent control endpoints
  rest.post('/api/agent/start', (req, res, ctx) => {
    return res(ctx.json({ success: true, message: 'Agent started successfully' }));
  }),

  rest.post('/api/agent/stop', (req, res, ctx) => {
    return res(ctx.json({ success: true, message: 'Agent stopped successfully' }));
  }),

  rest.post('/api/agent/pause', (req, res, ctx) => {
    return res(ctx.json({ success: true, message: 'Agent paused successfully' }));
  }),

  // Configuration endpoints
  rest.get('/api/config', (req, res, ctx) => {
    return res(ctx.json({
      symbols: ['BTCUSD', 'ETHUSD'],
      timeframes: ['15m', '1h', '4h'],
      riskLimits: {
        maxDailyLoss: 1000,
        maxDrawdown: 500,
        maxPositions: 5
      },
      tradingHours: {
        enabled: true,
        start: '09:00',
        end: '17:00',
        timezone: 'UTC'
      }
    }));
  }),

  rest.put('/api/config', (req, res, ctx) => {
    return res(ctx.json({ success: true, message: 'Configuration updated' }));
  }),

  // WebSocket simulation endpoints
  rest.get('/api/ws/connect', (req, res, ctx) => {
    return res(ctx.json({ 
      url: 'ws://localhost:8080/ws',
      token: 'mock-ws-token'
    }));
  })
);

// Setup and teardown
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterAll(() => {
  server.close();
});

beforeEach(() => {
  server.resetHandlers();
});

afterEach(() => {
  server.resetHandlers();
});

// Mock WebSocket for E2E tests
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    
    // Echo back for testing
    setTimeout(() => {
      if (this.onmessage) {
        this.onmessage(new MessageEvent('message', { data }));
      }
    }, 50);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  addEventListener(type: string, listener: EventListener) {
    if (type === 'open') this.onopen = listener as any;
    if (type === 'close') this.onclose = listener as any;
    if (type === 'message') this.onmessage = listener as any;
    if (type === 'error') this.onerror = listener as any;
  }

  removeEventListener(type: string, listener: EventListener) {
    if (type === 'open') this.onopen = null;
    if (type === 'close') this.onclose = null;
    if (type === 'message') this.onmessage = null;
    if (type === 'error') this.onerror = null;
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

// Mock localStorage for E2E tests
const localStorageMock = {
  getItem: (key: string) => {
    return localStorageMock.store[key] || null;
  },
  setItem: (key: string, value: string) => {
    localStorageMock.store[key] = value;
  },
  removeItem: (key: string) => {
    delete localStorageMock.store[key];
  },
  clear: () => {
    localStorageMock.store = {};
  },
  store: {} as Record<string, string>
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Mock performance.memory for memory tests
Object.defineProperty(performance, 'memory', {
  value: {
    usedJSHeapSize: 10000000,
    totalJSHeapSize: 20000000,
    jsHeapSizeLimit: 100000000
  },
  writable: true
});

// Export server for test-specific handlers
export { server };