// REST API service layer for HTTP requests to Python backend
import { API_ENDPOINTS, API_CONSTANTS } from '@/utils/constants';
import { RequestDeduplicator, debounce } from '@/utils/performance';
import type { 
  ApiResponse, 
  PaginatedResponse, 
  ApiError,
  LoginRequest,
  LoginResponse,
  User,
  TradingHistoryRequest,
  PerformanceRequest,
  ChartDataRequest,
  SystemStatusResponse,
  SystemMetricsRequest,
  AgentControlRequest,
  AgentConfigUpdateRequest,
  ConfigurationResponse,
  NotificationListRequest,
  NotificationUpdateRequest,
  BulkNotificationRequest,
  // HealthCheckResponse,
  ExportRequest,
  ExportResponse,
  BatchRequest,
  BatchResponse,
  RequestInterceptor,
  ResponseInterceptor,
  RequestConfig,
  CommonQueryParams
} from '@/types';

export class ApiService {
  private baseUrl: string;
  private authToken: string | null = null;
  private refreshToken: string | null = null;
  private isRefreshing = false;
  private refreshSubscribers: Array<(token: string) => void> = [];
  
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  
  private retryAttempts = new Map<string, number>();
  private requestDeduplicator: RequestDeduplicator;
  
  // Debounced methods for search operations
  private debouncedSearch: ReturnType<typeof debounce>;
  private debouncedFilter: ReturnType<typeof debounce>;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || API_ENDPOINTS.BASE_URL;
    this.requestDeduplicator = new RequestDeduplicator(5000); // 5 second cache
    
    // Initialize debounced methods
    this.debouncedSearch = debounce(this.performSearch.bind(this), 300, { trailing: true });
    this.debouncedFilter = debounce(this.performFilter.bind(this), 150, { trailing: true });
    
    this.setupDefaultInterceptors();
  }

  /**
   * Build request key for deduplication
   */
  private buildRequestKey(config: RequestConfig): string {
    const { url, method, params, data } = config;
    return `${method || 'GET'}:${url}?p=${params ? JSON.stringify(params) : ''}&d=${data ? JSON.stringify(data) : ''}`;
  }

  /**
   * Setup default request and response interceptors
   */
  private setupDefaultInterceptors(): void {
    // Default request interceptor for authentication
    this.addRequestInterceptor({
      onRequest: async (config) => {
        if (this.authToken) {
          config.headers = {
            ...config.headers,
            'Authorization': `Bearer ${this.authToken}`,
            'Content-Type': 'application/json',
          };
        }
        return config;
      },
      onRequestError: (error) => {
        console.error('Request interceptor error:', error);
        return error;
      }
    });
    
    // Default response interceptor for token refresh
    this.addResponseInterceptor({
      onResponse: (response) => {
        return response;
      },
      onResponseError: async (error) => {
        if (error.status === 401 && this.refreshToken && !this.isRefreshing) {
          return this.handleTokenRefresh(error);
        }
        return error;
      }
    });
  }
  
  /**
   * Add request interceptor
   */
  addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }
  
  /**
   * Add response interceptor
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }
  
  /**
   * Remove request interceptor
   */
  removeRequestInterceptor(interceptor: RequestInterceptor): void {
    const index = this.requestInterceptors.indexOf(interceptor);
    if (index > -1) {
      this.requestInterceptors.splice(index, 1);
    }
  }
  
  /**
   * Remove response interceptor
   */
  removeResponseInterceptor(interceptor: ResponseInterceptor): void {
    const index = this.responseInterceptors.indexOf(interceptor);
    if (index > -1) {
      this.responseInterceptors.splice(index, 1);
    }
  }
  
  /**
   * Generic HTTP request method
   */
  private async request<T>(config: RequestConfig): Promise<ApiResponse<T>> {
    const requestId = this.generateRequestId();
    
    try {
      // Apply request interceptors
      let processedConfig = config;
      for (const interceptor of this.requestInterceptors) {
        if (interceptor.onRequest) {
          processedConfig = await interceptor.onRequest(processedConfig);
        }
      }
      
      // Build full URL with query parameters
      const url = this.buildUrl(processedConfig.url, processedConfig.params);
      
      // Prepare fetch options
      const fetchOptions: RequestInit = {
        method: processedConfig.method,
        headers: processedConfig.headers,
        body: processedConfig.data ? JSON.stringify(processedConfig.data) : undefined,
      };
      
      // Set timeout
      const timeout = processedConfig.timeout || API_CONSTANTS.TIMEOUT.default;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      // Make the request
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      // Parse response
      const responseData = await this.parseResponse(response);
      
      // Apply response interceptors
      let processedResponse = responseData;
      for (const interceptor of this.responseInterceptors) {
        if (interceptor.onResponse) {
          processedResponse = await interceptor.onResponse(processedResponse);
        }
      }
      
      return {
        ...processedResponse,
        requestId,
        timestamp: new Date(),
      };
      
    } catch (error) {
      // Apply response error interceptors
      let processedError = error;
      for (const interceptor of this.responseInterceptors) {
        if (interceptor.onResponseError) {
          processedError = await interceptor.onResponseError(processedError);
        }
      }
      
      return this.handleRequestError(error, requestId);
    }
  }
  
  /**
   * Build full URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, any>): string {
    const url = new URL(endpoint, this.baseUrl);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach(v => url.searchParams.append(key, String(v)));
          } else {
            url.searchParams.append(key, String(value));
          }
        }
      });
    }
    
    return url.toString();
  }
  
  /**
   * Parse fetch response
   */
  private async parseResponse(response: Response): Promise<ApiResponse> {
    const contentType = response.headers.get('content-type');
    
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      return {
        success: response.ok,
        data: response.ok ? data : undefined,
        error: response.ok ? undefined : {
          code: response.status.toString(),
          message: data.message || response.statusText,
          details: data.details,
        },
        timestamp: new Date(),
      };
    } else {
      const text = await response.text();
      return {
        success: response.ok,
        data: response.ok ? text : undefined,
        error: response.ok ? undefined : {
          code: response.status.toString(),
          message: response.statusText,
          details: { response: text },
        },
        timestamp: new Date(),
      };
    }
  }
  
  /**
   * Handle request errors
   */
  private handleRequestError(error: any, requestId: string): ApiResponse {
    let apiError: ApiError;
    
    if (error.name === 'AbortError') {
      apiError = {
        code: 'TIMEOUT',
        message: 'Request timeout',
        details: { timeout: API_CONSTANTS.TIMEOUT.default },
      };
    } else if (error instanceof TypeError) {
      apiError = {
        code: 'NETWORK_ERROR',
        message: 'Network error',
        details: { originalError: error.message },
      };
    } else {
      apiError = {
        code: 'UNKNOWN_ERROR',
        message: 'Unknown error occurred',
        details: { originalError: error },
      };
    }
    
    return {
      success: false,
      error: apiError,
      requestId,
      timestamp: new Date(),
    };
  }
  
  /**
   * Handle token refresh
   */
  private async handleTokenRefresh(originalError: any): Promise<any> {
    if (this.isRefreshing) {
      // Wait for current refresh to complete
      return new Promise((resolve) => {
        this.refreshSubscribers.push((token) => resolve(token));
      });
    }
    
    this.isRefreshing = true;
    
    try {
      const response = await this.post<LoginResponse>('/auth/refresh', {
        refreshToken: this.refreshToken,
      });
      
      if (response.success && response.data) {
        this.authToken = response.data.token;
        this.refreshToken = response.data.refreshToken;
        
        // Notify subscribers
        this.refreshSubscribers.forEach(callback => callback(this.authToken!));
        this.refreshSubscribers = [];
        
        // Retry original request
        return this.retryRequest(originalError.config);
      } else {
        // Refresh failed, clear tokens
        this.clearAuthToken();
        throw originalError;
      }
    } catch (refreshError) {
      this.clearAuthToken();
      throw originalError;
    } finally {
      this.isRefreshing = false;
    }
  }
  
  /**
   * Retry failed request
   */
  private async retryRequest(config: RequestConfig): Promise<any> {
    // Implementation would retry the original request with new token
    // This is a simplified version
    return this.request(config);
  }
  
  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  /**
   * GET request with retry logic
   */
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.requestWithRetry<T>({
      url: endpoint,
      method: 'GET',
      params,
    });
  }
  
  /**
   * POST request with retry logic
   */
  async post<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    return this.requestWithRetry<T>({
      url: endpoint,
      method: 'POST',
      data,
    });
  }
  
  /**
   * PUT request with retry logic
   */
  async put<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    return this.requestWithRetry<T>({
      url: endpoint,
      method: 'PUT',
      data,
    });
  }
  
  /**
   * DELETE request with retry logic
   */
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.requestWithRetry<T>({
      url: endpoint,
      method: 'DELETE',
    });
  }
  
  /**
   * PATCH request with retry logic
   */
  async patch<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    return this.requestWithRetry<T>({
      url: endpoint,
      method: 'PATCH',
      data,
    });
  }
  
  /**
   * Request with retry logic and enhanced deduplication
   */
  private async requestWithRetry<T>(config: RequestConfig): Promise<ApiResponse<T>> {
    const maxRetries = config.retries || API_CONSTANTS.RETRY.attempts;
    const dedupe = config.dedupe !== false; // default true
    const cacheTTL = config.cacheTTL || 5000; // 5 second default cache
    
    // Use enhanced deduplicator for better performance
    if (dedupe) {
      const key = this.buildRequestKey(config);
      return this.requestDeduplicator.dedupe(
        key,
        () => this.executeRequestWithRetry<T>(config, maxRetries),
        cacheTTL
      );
    }

    return this.executeRequestWithRetry<T>(config, maxRetries);
  }

  /**
   * Execute request with retry logic
   */
  private async executeRequestWithRetry<T>(config: RequestConfig, maxRetries: number): Promise<ApiResponse<T>> {
    let lastError: any;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await this.request<T>(config);
        if (response.success || attempt === maxRetries) {
          return response;
        }
        if (response.error && this.isRetryableError(response.error)) {
          lastError = response;
          if (attempt < maxRetries) {
            const delay = this.calculateRetryDelay(attempt);
            await this.sleep(delay);
            continue;
          }
        }
        return response;
      } catch (error) {
        lastError = error;
        if (attempt < maxRetries && this.isRetryableError(error)) {
          const delay = this.calculateRetryDelay(attempt);
          await this.sleep(delay);
          continue;
        }
        throw error;
      }
    }
    return lastError;
  }
  
  /**
   * Check if error is retryable
   */
  private isRetryableError(error: any): boolean {
    if (error.error && error.error.code) {
      const retryableCodes = ['TIMEOUT', 'NETWORK_ERROR', 'SERVER_ERROR', '500', '502', '503', '504'];
      return retryableCodes.includes(error.error.code);
    }
    
    if (error.status) {
      const retryableStatuses = [408, 429, 500, 502, 503, 504];
      return retryableStatuses.includes(error.status);
    }
    
    return false;
  }
  
  /**
   * Calculate retry delay with exponential backoff
   */
  private calculateRetryDelay(attempt: number): number {
    const baseDelay = API_CONSTANTS.RETRY.delay;
    const multiplier = API_CONSTANTS.RETRY.backoffMultiplier;
    return Math.min(baseDelay * Math.pow(multiplier, attempt), 30000); // Max 30 seconds
  }
  
  /**
   * Sleep utility
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  // ===== AUTHENTICATION METHODS =====
  
  /**
   * Login user
   */
  async login(credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> {
    const response = await this.post<LoginResponse>(API_ENDPOINTS.AUTH.LOGIN, credentials);
    
    if (response.success && response.data) {
      this.authToken = response.data.token;
      this.refreshToken = response.data.refreshToken;
    }
    
    return response;
  }
  
  /**
   * Logout user
   */
  async logout(): Promise<ApiResponse<void>> {
    const response = await this.post<void>(API_ENDPOINTS.AUTH.LOGOUT, {});
    this.clearAuthToken();
    return response;
  }
  
  /**
   * Verify authentication token
   */
  async verifyAuth(): Promise<ApiResponse<User>> {
    return this.get<User>(API_ENDPOINTS.AUTH.VERIFY);
  }
  
  /**
   * Refresh authentication token
   */
  async refreshAuth(): Promise<ApiResponse<LoginResponse>> {
    if (!this.refreshToken) {
      return {
        success: false,
        error: {
          code: 'NO_REFRESH_TOKEN',
          message: 'No refresh token available',
        },
        timestamp: new Date(),
      };
    }
    
    const response = await this.post<LoginResponse>(API_ENDPOINTS.AUTH.REFRESH, {
      refreshToken: this.refreshToken,
    });
    
    if (response.success && response.data) {
      this.authToken = response.data.token;
      this.refreshToken = response.data.refreshToken;
    }
    
    return response;
  }
  
  // ===== TRADING API METHODS =====
  
  /**
   * Get trading positions
   */
  async getPositions(params?: CommonQueryParams): Promise<ApiResponse<PaginatedResponse<any>>> {
    return this.get<PaginatedResponse<any>>(API_ENDPOINTS.TRADING.POSITIONS, params);
  }
  
  /**
   * Get trading history
   */
  async getTradingHistory(request: TradingHistoryRequest): Promise<ApiResponse<PaginatedResponse<any>>> {
    return this.get<PaginatedResponse<any>>(API_ENDPOINTS.TRADING.TRADES, request);
  }
  
  /**
   * Get trading signals
   */
  async getTradingSignals(params?: CommonQueryParams): Promise<ApiResponse<PaginatedResponse<any>>> {
    return this.get<PaginatedResponse<any>>(API_ENDPOINTS.TRADING.SIGNALS, params);
  }
  
  /**
   * Get performance metrics
   */
  async getPerformance(request: PerformanceRequest): Promise<ApiResponse<any>> {
    return this.get<any>(API_ENDPOINTS.TRADING.PERFORMANCE, request);
  }
  
  /**
   * Get chart data
   */
  async getChartData(request: ChartDataRequest): Promise<ApiResponse<any>> {
    return this.get<any>('/trading/chart-data', request);
  }
  
  // ===== SYSTEM API METHODS =====
  
  /**
   * Get system health status
   */
  async getSystemHealth(): Promise<ApiResponse<SystemStatusResponse>> {
    return this.get<SystemStatusResponse>(API_ENDPOINTS.SYSTEM.HEALTH);
  }
  
  /**
   * Get system metrics
   */
  async getSystemMetrics(request: SystemMetricsRequest): Promise<ApiResponse<any>> {
    return this.get<any>(API_ENDPOINTS.SYSTEM.METRICS, request);
  }
  
  /**
   * Get system configuration
   */
  async getSystemConfig(): Promise<ApiResponse<ConfigurationResponse>> {
    return this.get<ConfigurationResponse>(API_ENDPOINTS.SYSTEM.CONFIG);
  }
  
  /**
   * Update system configuration
   */
  async updateSystemConfig(config: Partial<ConfigurationResponse>): Promise<ApiResponse<ConfigurationResponse>> {
    return this.put<ConfigurationResponse>(API_ENDPOINTS.SYSTEM.CONFIG, config);
  }
  
  // ===== AGENT CONTROL METHODS =====
  
  /**
   * Get agent status
   */
  async getAgentStatus(): Promise<ApiResponse<any>> {
    return this.get<any>(API_ENDPOINTS.SYSTEM.AGENTS);
  }
  
  /**
   * Control agent
   */
  async controlAgent(agentId: string, request: AgentControlRequest): Promise<ApiResponse<any>> {
    return this.post<any>(`${API_ENDPOINTS.SYSTEM.AGENTS}/${agentId}/control`, request);
  }
  
  /**
   * Update agent configuration
   */
  async updateAgentConfig(agentId: string, config: AgentConfigUpdateRequest): Promise<ApiResponse<any>> {
    return this.put<any>(`${API_ENDPOINTS.SYSTEM.AGENTS}/${agentId}/config`, config);
  }
  
  // ===== NOTIFICATION METHODS =====
  
  /**
   * Get notifications
   */
  async getNotifications(request: NotificationListRequest): Promise<ApiResponse<PaginatedResponse<any>>> {
    return this.get<PaginatedResponse<any>>('/notifications', request);
  }
  
  /**
   * Update notification
   */
  async updateNotification(id: string, request: NotificationUpdateRequest): Promise<ApiResponse<any>> {
    return this.put<any>(`/notifications/${id}`, request);
  }
  
  /**
   * Bulk notification operations
   */
  async bulkNotificationOperations(request: BulkNotificationRequest): Promise<ApiResponse<any>> {
    return this.post<any>('/notifications/bulk', request);
  }
  
  // ===== EXPORT/IMPORT METHODS =====
  
  /**
   * Export data
   */
  async exportData(request: ExportRequest): Promise<ApiResponse<ExportResponse>> {
    return this.post<ExportResponse>('/export', request);
  }
  
  /**
   * Get export status
   */
  async getExportStatus(exportId: string): Promise<ApiResponse<any>> {
    return this.get<any>(`/export/${exportId}/status`);
  }
  
  // ===== BATCH OPERATIONS =====
  
  /**
   * Execute batch operations
   */
  async executeBatch<T>(request: BatchRequest<T>): Promise<ApiResponse<BatchResponse<T>>> {
    return this.post<BatchResponse<T>>('/batch', request);
  }
  
  // ===== UTILITY METHODS =====
  
  /**
   * Set authentication token
   */
  setAuthToken(token: string, refreshToken?: string): void {
    this.authToken = token;
    if (refreshToken) {
      this.refreshToken = refreshToken;
    }
  }
  
  /**
   * Clear authentication tokens
   */
  clearAuthToken(): void {
    this.authToken = null;
    this.refreshToken = null;
  }
  
  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.authToken;
  }
  
  /**
   * Get current auth token
   */
  getAuthToken(): string | null {
    return this.authToken;
  }
  
  /**
   * Set base URL
   */
  setBaseUrl(url: string): void {
    this.baseUrl = url;
  }
  
  /**
   * Get base URL
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }
  
  /**
   * Clear request queue
   */
  clearRequestQueue(): void {
    // this.requestQueue = [];
    // this.isProcessingQueue = false;
    console.log('Request queue cleared - implementation pending');
  }
  
  /**
   * Get request statistics
   */
  getRequestStats(): { totalRequests: number; failedRequests: number; retryAttempts: number; cacheStats: any } {
    return {
      totalRequests: this.retryAttempts.size,
      failedRequests: Array.from(this.retryAttempts.values()).filter(attempts => attempts > 0).length,
      retryAttempts: Array.from(this.retryAttempts.values()).reduce((sum, attempts) => sum + attempts, 0),
      cacheStats: this.requestDeduplicator.getCacheStats(),
    };
  }

  // ===== OPTIMIZED SEARCH AND FILTER METHODS =====

  /**
   * Debounced search for trading logs
   */
  searchTradingLogs(query: string, filters?: any): Promise<ApiResponse<PaginatedResponse<any>>> {
    return new Promise((resolve, reject) => {
      this.debouncedSearch.cancel(); // Cancel previous search
      this.debouncedSearch(query, filters, resolve, reject);
    });
  }

  /**
   * Debounced filter for trading data
   */
  filterTradingData(filters: any): Promise<ApiResponse<PaginatedResponse<any>>> {
    return new Promise((resolve, reject) => {
      this.debouncedFilter.cancel(); // Cancel previous filter
      this.debouncedFilter(filters, resolve, reject);
    });
  }

  /**
   * Internal search implementation
   */
  private async performSearch(
    query: string, 
    filters: any, 
    resolve: (value: ApiResponse<PaginatedResponse<any>>) => void,
    reject: (reason?: any) => void
  ): Promise<void> {
    try {
      const params = {
        search: query,
        ...filters,
        cacheTTL: 2000, // Shorter cache for search results
      };
      const response = await this.get<PaginatedResponse<any>>(API_ENDPOINTS.TRADING.TRADES, params);
      resolve(response);
    } catch (error) {
      reject(error);
    }
  }

  /**
   * Internal filter implementation
   */
  private async performFilter(
    filters: any,
    resolve: (value: ApiResponse<PaginatedResponse<any>>) => void,
    reject: (reason?: any) => void
  ): Promise<void> {
    try {
      const response = await this.get<PaginatedResponse<any>>(API_ENDPOINTS.TRADING.TRADES, {
        ...filters,
        cacheTTL: 3000, // Medium cache for filter results
      });
      resolve(response);
    } catch (error) {
      reject(error);
    }
  }

  /**
   * Clear search and filter caches
   */
  clearSearchCache(): void {
    this.requestDeduplicator.clearCache('trades');
    this.debouncedSearch.cancel();
    this.debouncedFilter.cancel();
  }

  /**
   * Batch request optimization for multiple endpoints
   */
  async batchOptimizedRequests<T>(requests: Array<{ endpoint: string; params?: any }>): Promise<ApiResponse<T[]>> {
    const promises = requests.map(({ endpoint, params }) => 
      this.get<T>(endpoint, { ...params, cacheTTL: 10000 }) // Longer cache for batch requests
    );

    try {
      const responses = await Promise.allSettled(promises);
      const results: T[] = [];
      const errors: ApiError[] = [];

      responses.forEach((response, index) => {
        if (response.status === 'fulfilled' && response.value.success) {
          results.push(response.value.data!);
        } else {
          errors.push({
            code: 'BATCH_REQUEST_FAILED',
            message: `Request ${index} failed`,
            details: response.status === 'rejected' ? response.reason : response.value.error,
          });
        }
      });

      return {
        success: errors.length === 0,
        data: results,
        error: errors.length > 0 ? errors[0] : undefined,
        timestamp: new Date(),
      };
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'BATCH_REQUEST_ERROR',
          message: 'Batch request failed',
          details: error,
        },
        timestamp: new Date(),
      };
    }
  }
}