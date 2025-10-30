/**
 * Integration tests for backend connection
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { backendIntegration } from './BackendIntegration';
import { env } from '@/config/environment';
import { mockServer } from '@/test/mock-backend';

describe('Backend Integration', () => {
  beforeAll(async () => {
    // Start mock server
    mockServer.listen();
    
    // Initialize backend integration for testing
    try {
      await backendIntegration.initialize();
    } catch (error) {
      console.warn('Backend initialization failed:', error);
    }
  });

  afterAll(() => {
    // Clean up
    mockServer.close();
    backendIntegration.destroy();
  });

  it('should have correct environment configuration', () => {
    expect(env.apiBaseUrl).toBeDefined();
    expect(env.wsBaseUrl).toBeDefined();
    expect(env.environment).toBeDefined();
  });

  it('should create backend integration instance', () => {
    expect(backendIntegration).toBeDefined();
    expect(backendIntegration.getApiService()).toBeDefined();
    expect(backendIntegration.getWebSocketService()).toBeDefined();
  });

  it('should handle authentication flow', async () => {
    const result = await backendIntegration.authenticate({
      email: 'test@example.com',
      password: 'password123'
    });
    
    expect(result).toBeDefined();
    expect(result.token).toBe('mock-jwt-token');
    expect(result.refreshToken).toBe('mock-refresh-token');
  });

  it('should fetch system health data', async () => {
    const health = await backendIntegration.getSystemHealth();
    
    expect(health).toBeDefined();
    expect(health.cpu).toBe(20);
    expect(health.memory).toBe(30);
    expect(health.connections).toBeDefined();
    expect(health.connections.database).toBe(true);
  });

  it('should fetch performance metrics', async () => {
    const metrics = await backendIntegration.getPerformanceMetrics();
    
    expect(metrics).toBeDefined();
    expect(metrics.totalPnl).toBe(1234.56);
    expect(metrics.winRate).toBe(66.7);
  });

  it('should fetch agent status', async () => {
    const status = await backendIntegration.getAgentStatus();
    
    expect(status).toBeDefined();
    expect(status.state).toBe('running');
    expect(status.activePositions).toBe(2);
  });

  it('should fetch trading history', async () => {
    const history = await backendIntegration.getTradingHistory();
    
    expect(history).toBeDefined();
    expect(Array.isArray(history)).toBe(true);
    expect(history.length).toBe(2);
    expect(history[0].symbol).toBe('BTCUSDT');
  });

  it('should provide connection status', () => {
    const status = backendIntegration.getConnectionStatus();
    expect(status).toHaveProperty('api');
    expect(status).toHaveProperty('websocket');
    expect(typeof status.api).toBe('boolean');
    expect(typeof status.websocket).toBe('boolean');
  });
});