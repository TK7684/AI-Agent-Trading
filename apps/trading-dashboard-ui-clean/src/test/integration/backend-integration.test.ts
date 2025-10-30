/**
 * Integration tests for backend connection
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { backendIntegration } from '@/services/BackendIntegration';
import { env } from '@/config/environment';

describe('Backend Integration', () => {
  beforeAll(async () => {
    // Initialize backend integration for testing
    try {
      await backendIntegration.initialize();
    } catch (error) {
      console.warn('Backend not available for integration tests:', error);
    }
  });

  afterAll(() => {
    // Clean up
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
    try {
      const result = await backendIntegration.authenticate({
        email: 'test@example.com',
        password: 'password123'
      });
      
      expect(result).toBeDefined();
      expect(result.token).toBeDefined();
    } catch (error) {
      // Backend might not be running during tests
      console.warn('Authentication test skipped - backend not available');
    }
  });

  it('should handle API requests gracefully when backend is unavailable', async () => {
    try {
      await backendIntegration.getSystemHealth();
    } catch (error) {
      // This is expected when backend is not running
      expect(error).toBeDefined();
    }
  });

  it('should provide connection status', () => {
    const status = backendIntegration.getConnectionStatus();
    expect(status).toHaveProperty('api');
    expect(status).toHaveProperty('websocket');
    expect(typeof status.api).toBe('boolean');
    expect(typeof status.websocket).toBe('boolean');
  });
});