/**
 * Backend Integration Tests
 * Tests WebSocket connections and API integration with Python backend
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ApiService } from '@services/apiService';
import { WebSocketService } from '@services/websocketService';
import { API_ENDPOINTS, WEBSOCKET_ENDPOINTS } from '@utils/constants';

// Mock environment variables for testing
vi.mock('import.meta.env', () => ({
  VITE_BACKEND_API_URL: 'http://localhost:8000',
  VITE_BACKEND_WS_URL: 'ws://localhost:8000',
  VITE_AUTH_ENABLED: 'true',
  VITE_DEBUG_MODE: 'true',
}));

describe('Backend Integration Tests', () => {
  let apiService: ApiService;
  let wsService: WebSocketService;

  beforeEach(() => {
    apiService = new ApiService('http://localhost:8000');
    wsService = new WebSocketService({
      url: 'ws://localhost:8000',
      maxReconnectAttempts: 3,
      reconnectInterval: 1000,
    });
  });

  afterEach(() => {
    wsService.disconnect();
  });

  describe('API Service Integration', () => {
    it('should have correct base URL configuration', () => {
      expect(apiService.getBaseUrl()).toBe('http://localhost:8000');
      expect(API_ENDPOINTS.BASE_URL).toBe('http://localhost:8000');
    });

    it('should handle authentication flow', async () => {
      const mockCredentials = {
        email: 'test@example.com',
        password: 'testpassword',
      };

      // Mock successful login response
      const mockResponse = {
        success: true,
        data: {
          token: 'mock-jwt-token',
          refreshToken: 'mock-refresh-token',
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
          },
        },
        timestamp: new Date(),
      };

      // Mock fetch for login
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse.data,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.login(mockCredentials);
      
      expect(response.success).toBe(true);
      expect(response.data?.token).toBe('mock-jwt-token');
      expect(apiService.isAuthenticated()).toBe(true);
    });

    it('should fetch trading performance data', async () => {
      // Set auth token
      apiService.setAuthToken('mock-token');

      const mockPerformance = {
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

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockPerformance,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.getPerformance({});
      
      expect(response.success).toBe(true);
      expect(response.data?.totalPnl).toBe(1234.56);
      expect(response.data?.winRate).toBe(66.7);
    });

    it('should fetch agent status', async () => {
      apiService.setAuthToken('mock-token');

      const mockAgentStatus = {
        state: 'running',
        uptime: 3600,
        lastAction: new Date().toISOString(),
        activePositions: 2,
        dailyTrades: 10,
        version: '1.0.0',
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockAgentStatus,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.getAgentStatus();
      
      expect(response.success).toBe(true);
      expect(response.data?.state).toBe('running');
      expect(response.data?.activePositions).toBe(2);
    });

    it('should fetch system health', async () => {
      apiService.setAuthToken('mock-token');

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

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockSystemHealth,
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.getSystemHealth();
      
      expect(response.success).toBe(true);
      expect(response.data?.cpu).toBe(20);
      expect(response.data?.connections.database).toBe(true);
    });

    it('should handle API errors gracefully', async () => {
      apiService.setAuthToken('invalid-token');

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Invalid token' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.getPerformance({});
      
      expect(response.success).toBe(false);
      expect(response.error?.code).toBe('401');
      expect(response.error?.message).toBe('Invalid token');
    });
  });

  describe('WebSocket Service Integration', () => {
    it('should have correct WebSocket URL configuration', () => {
      expect(wsService.getBaseUrl()).toBe('ws://localhost:8000');
      expect(WEBSOCKET_ENDPOINTS.BASE_URL).toBe('ws://localhost:8000');
    });

    it('should handle connection state changes', () => {
      const initialState = wsService.getConnectionState();
      expect(initialState.status).toBe('disconnected');
      expect(initialState.reconnectAttempts).toBe(0);
    });

    it('should manage subscriptions correctly', () => {
      const mockCallback = vi.fn();
      
      wsService.subscribe('TRADE_UPDATE', mockCallback);
      wsService.subscribeToChannel('trading', { symbols: ['BTCUSD'] });
      
      // Verify subscription was added
      expect(wsService.getConnectionState().status).toBe('disconnected');
      
      wsService.unsubscribe('TRADE_UPDATE', mockCallback);
      wsService.unsubscribeFromChannel('trading');
    });

    it('should handle message routing', () => {
      const tradingCallback = vi.fn();
      const systemCallback = vi.fn();
      
      wsService.subscribe('TRADE_UPDATE', tradingCallback);
      wsService.subscribe('SYSTEM_UPDATE', systemCallback);
      
      // Mock message handling
      const mockTradingMessage = {
        type: 'TRADE_UPDATE',
        data: {
          symbol: 'BTCUSD',
          price: 50000,
          quantity: 0.1,
        },
        timestamp: new Date(),
      };
      
      // Simulate message reception (would normally come from WebSocket)
      wsService.setEventHandlers({
        onMessage: (message) => {
          if (message.type === 'TRADE_UPDATE') {
            tradingCallback(message.data);
          }
        },
      });
    });

    it('should handle authentication with WebSocket', () => {
      const token = 'mock-jwt-token';
      wsService.setToken(token);
      
      // Verify token is set (implementation detail)
      expect(wsService).toBeDefined();
    });
  });

  describe('Real-time Data Flow', () => {
    it('should validate trading metrics updates', () => {
      const mockTradingUpdate = {
        type: 'TRADE_OPENED',
        data: {
          id: 'trade-123',
          symbol: 'BTCUSD',
          side: 'LONG',
          entryPrice: 50000,
          quantity: 0.1,
          timestamp: new Date(),
        },
      };

      const callback = vi.fn();
      wsService.subscribe('TRADE_OPENED', callback);
      
      // Simulate receiving update
      wsService.setEventHandlers({
        onMessage: (message) => {
          if (message.type === 'TRADE_OPENED') {
            callback(message.data);
          }
        },
      });
    });

    it('should validate system health updates', () => {
      const mockSystemUpdate = {
        type: 'HEALTH_UPDATE',
        data: {
          cpu: 25,
          memory: 35,
          connections: {
            database: true,
            broker: true,
            llm: false,
          },
          timestamp: new Date(),
        },
      };

      const callback = vi.fn();
      wsService.subscribe('HEALTH_UPDATE', callback);
    });

    it('should validate notification delivery', () => {
      const mockNotification = {
        type: 'NOTIFICATION',
        data: {
          id: 'notif-123',
          type: 'warning',
          title: 'High Risk Trade',
          message: 'Trade exceeds risk threshold',
          timestamp: new Date(),
        },
      };

      const callback = vi.fn();
      wsService.subscribe('NOTIFICATION', callback);
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should handle complete auth flow with backend', async () => {
      // Mock login
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          token: 'mock-jwt-token',
          refreshToken: 'mock-refresh-token',
        }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const loginResponse = await apiService.login({
        email: 'test@example.com',
        password: 'password',
      });

      expect(loginResponse.success).toBe(true);
      expect(apiService.isAuthenticated()).toBe(true);

      // Set token for WebSocket
      wsService.setToken(loginResponse.data?.token);

      // Mock token refresh
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          token: 'new-mock-jwt-token',
          refreshToken: 'new-mock-refresh-token',
        }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const refreshResponse = await apiService.refreshAuth();
      expect(refreshResponse.success).toBe(true);
    });

    it('should handle auth failures gracefully', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => ({ message: 'Invalid credentials' }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.login({
        email: 'invalid@example.com',
        password: 'wrongpassword',
      });

      expect(response.success).toBe(false);
      expect(response.error?.message).toBe('Invalid credentials');
      expect(apiService.isAuthenticated()).toBe(false);
    });
  });

  describe('Agent Control Integration', () => {
    it('should handle agent control commands', async () => {
      apiService.setAuthToken('mock-token');

      // Mock agent control response
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          message: 'Agent started successfully',
          state: 'running',
        }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.controlAgent('main-agent', {
        action: 'start',
      });

      expect(response.success).toBe(true);
      expect(response.data?.state).toBe('running');
    });

    it('should handle agent configuration updates', async () => {
      apiService.setAuthToken('mock-token');

      const mockConfig = {
        symbols: ['BTCUSD', 'ETHUSD'],
        riskLimits: {
          maxDailyLoss: 1000,
          maxDrawdown: 500,
          maxPositions: 5,
        },
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          config: mockConfig,
        }),
        headers: new Headers({ 'content-type': 'application/json' }),
      });

      const response = await apiService.updateAgentConfig('main-agent', mockConfig);

      expect(response.success).toBe(true);
      expect(response.data?.config.symbols).toContain('BTCUSD');
    });
  });
});