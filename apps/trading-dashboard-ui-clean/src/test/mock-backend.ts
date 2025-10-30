/**
 * Mock backend server for testing
 */

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

// Mock data
const mockPerformanceData = {
  totalPnl: 1234.56,
  dailyPnl: 12.34,
  winRate: 66.7,
  totalTrades: 42,
  currentDrawdown: 5.2,
  maxDrawdown: 12.3,
  portfolioValue: 25000,
  dailyChange: 12.34,
  dailyChangePercent: 0.05,
  lastUpdate: new Date().toISOString(),
};

const mockAgentStatus = {
  state: 'running',
  uptime: 3600,
  lastAction: new Date().toISOString(),
  activePositions: 2,
  dailyTrades: 10,
  version: '1.0.0',
};

const mockSystemHealth = {
  cpu: 20,
  memory: 30,
  diskUsage: 40,
  networkLatency: 50,
  errorRate: 1,
  uptime: 10000,
  connections: {
    database: true,
    broker: true,
    llm: true,
    websocket: true,
  },
  lastUpdate: new Date().toISOString(),
};

const mockTradingHistory = {
  items: [
    {
      id: '1',
      timestamp: new Date().toISOString(),
      symbol: 'BTCUSDT',
      side: 'LONG',
      entryPrice: 50000,
      exitPrice: 51000,
      quantity: 0.1,
      pnl: 100,
      status: 'CLOSED',
      pattern: 'breakout',
      confidence: 85,
    },
    {
      id: '2',
      timestamp: new Date().toISOString(),
      symbol: 'ETHUSDT',
      side: 'SHORT',
      entryPrice: 3000,
      exitPrice: 2950,
      quantity: 1,
      pnl: 50,
      status: 'CLOSED',
      pattern: 'reversal',
      confidence: 78,
    },
  ],
  total: 2,
  page: 1,
  pageSize: 20,
  hasNext: false,
};

// Mock handlers
export const handlers = [
  // Authentication
  http.post('http://localhost:8000/auth/login', () => {
    return HttpResponse.json({
      token: 'mock-jwt-token',
      refreshToken: 'mock-refresh-token',
    });
  }),

  http.post('http://localhost:8000/auth/refresh', () => {
    return HttpResponse.json({
      token: 'new-mock-jwt-token',
      refreshToken: 'new-mock-refresh-token',
    });
  }),

  // Trading endpoints
  http.get('http://localhost:8000/trading/performance', () => {
    return HttpResponse.json(mockPerformanceData);
  }),

  http.get('http://localhost:8000/trading/trades', () => {
    return HttpResponse.json(mockTradingHistory);
  }),

  // System endpoints
  http.get('http://localhost:8000/system/health', () => {
    return HttpResponse.json(mockSystemHealth);
  }),

  http.get('http://localhost:8000/system/agents', () => {
    return HttpResponse.json(mockAgentStatus);
  }),

  // Agent control
  http.post('http://localhost:8000/system/agents/:agentId/control', () => {
    return HttpResponse.json({ success: true });
  }),
];

// Setup mock server
export const mockServer = setupServer(...handlers);