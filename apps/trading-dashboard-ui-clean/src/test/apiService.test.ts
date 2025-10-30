import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';
import { ApiService } from '../services/apiService';
import { API_ENDPOINTS, API_CONSTANTS } from '@utils/constants';
import type { 
  LoginRequest, 
  LoginResponse, 
  ApiResponse,
  RequestInterceptor,
  ResponseInterceptor
} from '@types/index';

// Mock fetch globally
global.fetch = vi.fn();

// Mock AbortController
global.AbortController = vi.fn().mockImplementation(() => ({
  signal: {},
  abort: vi.fn(),
}));

describe('ApiService', () => {
  let apiService: ApiService;
  let mockFetch: Mock;
  
  beforeEach(() => {
    apiService = new ApiService();
    mockFetch = fetch as Mock;
    mockFetch.mockClear();
    
    // Reset timers
    vi.clearAllTimers();
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  describe('Constructor and Configuration', () => {
    it('should initialize with default base URL', () => {
      expect(apiService.getBaseUrl()).toBe(API_ENDPOINTS.BASE_URL);
    });
    
    it('should accept custom base URL', () => {
      const customService = new ApiService('https://custom-api.com');
      expect(customService.getBaseUrl()).toBe('https://custom-api.com');
    });
    
    it('should setup default interceptors', () => {
      expect(apiService.isAuthenticated()).toBe(false);
    });
  });
  
  describe('HTTP Request Methods', () => {
    it('should make GET request successfully', async () => {
      const mockResponse = { success: true, data: { id: '123' } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.get('/test');
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({ method: 'GET' })
      );
      expect(result.success).toBe(true);
    });
    
    it('should make POST request successfully', async () => {
      const mockData = { name: 'test' };
      const mockResponse = { success: true, data: { id: '123', ...mockData } };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.post('/test', mockData);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(mockData),
        })
      );
      expect(result.success).toBe(true);
    });
    
    it('should make PUT request successfully', async () => {
      const mockData = { name: 'updated' };
      const mockResponse = { success: true, data: { id: '123', ...mockData } };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.put('/test/123', mockData);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test/123'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(mockData),
        })
      );
      expect(result.success).toBe(true);
    });
    
    it('should make DELETE request successfully', async () => {
      const mockResponse = { success: true, data: null };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.delete('/test/123');
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test/123'),
        expect.objectContaining({ method: 'DELETE' })
      );
      expect(result.success).toBe(true);
    });
    
    it('should make PATCH request successfully', async () => {
      const mockData = { name: 'patched' };
      const mockResponse = { success: true, data: { id: '123', ...mockData } };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.patch('/test/123', mockData);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test/123'),
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(mockData),
        })
      );
      expect(result.success).toBe(true);
    });
  });
  
  describe('URL Building and Query Parameters', () => {
    it('should build URL with query parameters', async () => {
      const mockResponse = { success: true, data: [] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const params = { page: 1, size: 10, search: 'test' };
      await apiService.get('/test', params);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test?page=1&size=10&search=test'),
        expect.any(Object)
      );
    });
    
    it('should handle array query parameters', async () => {
      const mockResponse = { success: true, data: [] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const params = { status: ['active', 'pending'], tags: ['urgent'] };
      await apiService.get('/test', params);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test?status=active&status=pending&tags=urgent'),
        expect.any(Object)
      );
    });
    
    it('should handle undefined and null parameters', async () => {
      const mockResponse = { success: true, data: [] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const params = { page: 1, size: undefined, search: null, active: true };
      await apiService.get('/test', params);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test?page=1&active=true'),
        expect.any(Object)
      );
    });
  });
  
  describe('Authentication Handling', () => {
    it('should add authorization header when token is set', async () => {
      const mockResponse = { success: true, data: { user: 'test' } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      apiService.setAuthToken('test-token');
      
      await apiService.get('/user/profile');
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json',
          }),
        })
      );
    });
    
    it('should handle login and store tokens', async () => {
      const credentials: LoginRequest = { username: 'test', password: 'password' };
      const mockResponse = {
        success: true,
        data: {
          token: 'access-token',
          refreshToken: 'refresh-token',
          user: { id: '123', username: 'test' },
          expiresAt: new Date(),
          permissions: ['read', 'write'],
        },
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.login(credentials);
      
      expect(result.success).toBe(true);
      expect(apiService.isAuthenticated()).toBe(true);
      expect(apiService.getAuthToken()).toBe('access-token');
    });
    
    it('should handle logout and clear tokens', async () => {
      // Set initial tokens
      apiService.setAuthToken('access-token', 'refresh-token');
      expect(apiService.isAuthenticated()).toBe(true);
      
      const mockResponse = { success: true, data: null };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      await apiService.logout();
      
      expect(apiService.isAuthenticated()).toBe(false);
      expect(apiService.getAuthToken()).toBeNull();
    });
    
    it('should verify authentication', async () => {
      const mockResponse = { success: true, data: { id: '123', username: 'test' } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.verifyAuth();
      
      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockResponse.data);
    });
  });
  
  describe('Request/Response Interceptors', () => {
    it('should apply request interceptors', async () => {
      const mockResponse = { success: true, data: [] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const requestInterceptor: RequestInterceptor = {
        onRequest: (config) => {
          config.headers = { ...config.headers, 'X-Custom-Header': 'test' };
          return config;
        },
      };
      
      apiService.addRequestInterceptor(requestInterceptor);
      
      await apiService.get('/test');
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Custom-Header': 'test',
          }),
        })
      );
    });
    
    it('should apply response interceptors', async () => {
      const mockResponse = { success: true, data: [] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const responseInterceptor: ResponseInterceptor = {
        onResponse: (response) => {
          response.data = { ...response.data, intercepted: true };
          return response;
        },
      };
      
      apiService.addResponseInterceptor(responseInterceptor);
      
      const result = await apiService.get('/test');
      
      expect(result.data).toEqual({ ...mockResponse.data, intercepted: true });
    });
    
    it('should handle request interceptor errors', async () => {
      const requestInterceptor: RequestInterceptor = {
        onRequest: () => {
          throw new Error('Interceptor error');
        },
        onRequestError: (error) => {
          return { ...error, handled: true };
        },
      };
      
      apiService.addRequestInterceptor(requestInterceptor);
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('UNKNOWN_ERROR');
    });
    
    it('should remove interceptors', () => {
      const interceptor: RequestInterceptor = { onRequest: (config) => config };
      
      apiService.addRequestInterceptor(interceptor);
      expect(apiService.getRequestStats().totalRequests).toBe(0);
      
      apiService.removeRequestInterceptor(interceptor);
      // Should not affect functionality
      expect(apiService.getRequestStats().totalRequests).toBe(0);
    });
  });
  
  describe('Error Handling and Retry Logic', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Network error'));
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('NETWORK_ERROR');
    });
    
    it('should handle timeout errors', async () => {
      // Mock AbortController to simulate timeout
      const mockAbortController = {
        signal: {},
        abort: vi.fn(),
      };
      
      vi.mocked(AbortController).mockImplementationOnce(() => mockAbortController);
      
      // Mock fetch to never resolve (simulating timeout)
      mockFetch.mockImplementationOnce(() => new Promise(() => {}));
      
      // Fast-forward time to trigger timeout
      vi.useFakeTimers();
      const requestPromise = apiService.get('/test');
      
      vi.advanceTimersByTime(API_CONSTANTS.TIMEOUT.default + 100);
      
      const result = await requestPromise;
      
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('TIMEOUT');
      
      vi.useRealTimers();
    });
    
    it('should retry failed requests with exponential backoff', async () => {
      const mockResponse = { success: true, data: [] };
      
      // First two calls fail, third succeeds
      mockFetch
        .mockRejectedValueOnce(new TypeError('Network error'))
        .mockRejectedValueOnce(new TypeError('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockResponse),
          headers: new Headers({ 'content-type': 'application/json' }),
        });
      
      vi.useFakeTimers();
      
      const requestPromise = apiService.get('/test');
      
      // Fast-forward through retry delays
      vi.advanceTimersByTime(1000); // First retry
      vi.advanceTimersByTime(2000); // Second retry
      
      const result = await requestPromise;
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledTimes(3);
      
      vi.useRealTimers();
    });
    
    it('should not retry non-retryable errors', async () => {
      const mockResponse = { success: false, error: { code: '400', message: 'Bad Request' } };
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(false);
      expect(mockFetch).toHaveBeenCalledTimes(1); // No retries
    });
  });
  
  describe('Trading API Methods', () => {
    it('should get trading positions', async () => {
      const mockResponse = { success: true, data: { items: [], total: 0, page: 1, pageSize: 20 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.getPositions({ page: 1, pageSize: 20 });
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.TRADING.POSITIONS),
        expect.any(Object)
      );
    });
    
    it('should get trading history', async () => {
      const mockResponse = { success: true, data: { items: [], total: 0, page: 1, pageSize: 20 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const request = { symbol: 'BTCUSD', startDate: new Date(), endDate: new Date() };
      const result = await apiService.getTradingHistory(request);
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.TRADING.TRADES),
        expect.any(Object)
      );
    });
    
    it('should get trading signals', async () => {
      const mockResponse = { success: true, data: { items: [], total: 0, page: 1, pageSize: 20 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.getTradingSignals({ page: 1, pageSize: 20 });
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.TRADING.SIGNALS),
        expect.any(Object)
      );
    });
    
    it('should get performance metrics', async () => {
      const mockResponse = { success: true, data: { pnl: 1000, winRate: 0.6 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const request = { period: 'month' as const, startDate: new Date(), endDate: new Date() };
      const result = await apiService.getPerformance(request);
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.TRADING.PERFORMANCE),
        expect.any(Object)
      );
    });
  });
  
  describe('System API Methods', () => {
    it('should get system health', async () => {
      const mockResponse = { success: true, data: { status: 'healthy', uptime: 3600 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.getSystemHealth();
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.SYSTEM.HEALTH),
        expect.any(Object)
      );
    });
    
    it('should get system metrics', async () => {
      const mockResponse = { success: true, data: { cpu: 45, memory: 60 } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const request = { period: 'hour' as const, metrics: ['cpu', 'memory'] };
      const result = await apiService.getSystemMetrics(request);
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.SYSTEM.METRICS),
        expect.any(Object)
      );
    });
    
    it('should get system configuration', async () => {
      const mockResponse = { success: true, data: { trading: {}, system: {}, ui: {} } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.getSystemConfig();
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(API_ENDPOINTS.SYSTEM.CONFIG),
        expect.any(Object)
      );
    });
  });
  
  describe('Agent Control Methods', () => {
    it('should control agent', async () => {
      const mockResponse = { success: true, data: { status: 'running' } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const request = { action: 'start' as const };
      const result = await apiService.controlAgent('agent-123', request);
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/agents/agent-123/control'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
        })
      );
    });
    
    it('should update agent configuration', async () => {
      const mockResponse = { success: true, data: { updated: true } };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const config = { symbols: ['BTCUSD'], timeframes: ['1h'] };
      const result = await apiService.updateAgentConfig('agent-123', config);
      
      expect(result.success).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/agents/agent-123/config'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(config),
        })
      );
    });
  });
  
  describe('Utility Methods', () => {
    it('should set and get base URL', () => {
      const newUrl = 'https://new-api.com';
      apiService.setBaseUrl(newUrl);
      expect(apiService.getBaseUrl()).toBe(newUrl);
    });
    
    it('should clear request queue', () => {
      apiService.clearRequestQueue();
      const stats = apiService.getRequestStats();
      expect(stats.totalRequests).toBe(0);
    });
    
    it('should get request statistics', () => {
      const stats = apiService.getRequestStats();
      expect(stats).toEqual({
        totalRequests: 0,
        failedRequests: 0,
        retryAttempts: 0,
      });
    });
  });
  
  describe('Response Parsing', () => {
    it('should parse JSON responses', async () => {
      const mockData = { id: '123', name: 'test' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockData),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(true);
      expect(result.data).toEqual(mockData);
    });
    
    it('should parse text responses', async () => {
      const mockText = 'Success message';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(mockText),
        headers: new Headers({ 'content-type': 'text/plain' }),
      });
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(true);
      expect(result.data).toBe(mockText);
    });
    
    it('should handle error responses', async () => {
      const mockError = { message: 'Not found', details: { field: 'id' } };
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve(mockError),
        headers: new Headers({ 'content-type': 'application/json' }),
      });
      
      const result = await apiService.get('/test');
      
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('404');
      expect(result.error?.message).toBe('Not found');
    });
  });
});
