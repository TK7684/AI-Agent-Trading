/**
 * Backend integration service to connect frontend with Python backend API
 */

import { ApiService } from './apiService';
import { WebSocketService } from './websocketService';
import { env } from '@/config/environment';
import type { 
  PerformanceMetrics, 
  TradeLogEntry, 
  AgentStatus, 
  SystemHealth,
  LoginRequest,
  LoginResponse
} from '@/types';

export class BackendIntegration {
  private apiService: ApiService;
  private wsService: WebSocketService;
  private isInitialized = false;

  constructor() {
    this.apiService = new ApiService(env.apiBaseUrl);
    this.wsService = new WebSocketService({
      url: env.wsBaseUrl,
      maxReconnectAttempts: 10,
      reconnectInterval: 5000,
      heartbeatInterval: 30000,
      timeout: 10000,
    });
  }

  /**
   * Initialize the backend integration
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Test API connection (health endpoint doesn't require auth)
      await this.testApiConnection();
      
      // Initialize WebSocket connection (but don't connect until authenticated)
      this.setupWebSocketHandlers();
      
      this.isInitialized = true;
      console.log('Backend integration initialized successfully');
    } catch (error) {
      console.error('Failed to initialize backend integration:', error);
      throw error;
    }
  }

  /**
   * Test API connection to backend
   */
  private async testApiConnection(): Promise<void> {
    try {
      // Use health endpoint which doesn't require auth
      const response = await this.apiService.get('/system/health');
      if (!response.success) {
        throw new Error(`API connection test failed: ${response.error?.message}`);
      }
      console.log('API connection test successful');
    } catch (error) {
      console.error('API connection test failed:', error);
      // Don't throw error in development mode to allow graceful degradation
      if (env.environment === 'production') {
        throw error;
      }
    }
  }

  /**
   * Setup WebSocket event handlers (but don't connect yet)
   */
  private setupWebSocketHandlers(): void {
    this.wsService.setEventHandlers({
      onOpen: (_event) => {
        console.log('WebSocket connected to backend');
      },
      onClose: (_event) => {
        console.log('WebSocket disconnected from backend');
      },
      onError: (event) => {
        console.error('WebSocket error:', event);
      },
      onMessage: (message) => {
        if (env.debugMode) {
          console.log('WebSocket message received:', message);
        }
      },
      onReconnect: (attempt) => {
        console.log(`WebSocket reconnection attempt ${attempt}`);
      },
    });
  }

  /**
   * Initialize WebSocket connection after authentication
   */
  private async initializeWebSocket(): Promise<void> {
    try {
      // Connect to WebSocket
      await this.wsService.connect();
      console.log('WebSocket connection initialized');
    } catch (error) {
      console.error('WebSocket initialization failed:', error);
      throw error;
    }
  }

  /**
   * Authenticate with backend
   */
  async authenticate(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.apiService.login(credentials);
    
    if (response.success && response.data) {
      // Set token for WebSocket connection
      this.wsService.setToken(response.data.token);
      
      // Initialize WebSocket connection now that we're authenticated
      await this.initializeWebSocket();
      
      return response.data;
    } else {
      throw new Error(response.error?.message || 'Authentication failed');
    }
  }

  /**
   * Logout and cleanup
   */
  async logout(): Promise<void> {
    await this.apiService.logout();
    this.wsService.setToken(undefined);
    this.wsService.disconnect();
  }

  /**
   * Get performance metrics from backend
   */
  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    const response = await this.apiService.getPerformance({ period: 'day' });
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error(response.error?.message || 'Failed to fetch performance metrics');
    }
  }

  /**
   * Get agent status from backend
   */
  async getAgentStatus(): Promise<AgentStatus> {
    const response = await this.apiService.getAgentStatus();
    
    if (response.success && response.data) {
      return response.data;
    } else {
      throw new Error(response.error?.message || 'Failed to fetch agent status');
    }
  }

  /**
   * Get system health from backend
   */
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await this.apiService.getSystemHealth();
    
    if (response.success && response.data) {
      // Map SystemStatusResponse to SystemHealth
      return {
        cpu: 0, // Default values - should be provided by backend
        memory: 0,
        diskUsage: 0,
        networkLatency: 0,
        errorRate: 0,
        uptime: response.data.uptime,
        connections: {
          database: response.data.services.find(s => s.name === 'database')?.status === 'online' || false,
          broker: response.data.services.find(s => s.name === 'broker')?.status === 'online' || false,
          llm: response.data.services.find(s => s.name === 'llm')?.status === 'online' || false,
          websocket: response.data.services.find(s => s.name === 'websocket')?.status === 'online' || false,
        },
        lastUpdate: response.data.lastHealthCheck,
      };
    } else {
      throw new Error(response.error?.message || 'Failed to fetch system health');
    }
  }

  /**
   * Get trading history from backend
   */
  async getTradingHistory(params?: any): Promise<TradeLogEntry[]> {
    const response = await this.apiService.getTradingHistory(params || {});
    
    if (response.success && response.data) {
      return response.data.items || [];
    } else {
      throw new Error(response.error?.message || 'Failed to fetch trading history');
    }
  }

  /**
   * Control agent (start/stop/pause)
   */
  async controlAgent(action: 'start' | 'stop' | 'pause'): Promise<void> {
    const response = await this.apiService.controlAgent('default', { action });
    
    if (!response.success) {
      throw new Error(response.error?.message || `Failed to ${action} agent`);
    }
  }

  /**
   * Subscribe to real-time trading updates
   */
  subscribeToTradingUpdates(callback: (data: any) => void): void {
    this.wsService.subscribe('TRADE_OPENED', callback);
    this.wsService.subscribe('TRADE_CLOSED', callback);
    this.wsService.subscribe('POSITION_UPDATE', callback);
    this.wsService.subscribe('PNL_UPDATE', callback);
  }

  /**
   * Subscribe to real-time system updates
   */
  subscribeToSystemUpdates(callback: (data: any) => void): void {
    this.wsService.subscribe('METRICS_UPDATE', callback);
    this.wsService.subscribe('HEALTH_CHECK', callback);
    this.wsService.subscribe('ERROR_ALERT', callback);
  }

  /**
   * Subscribe to agent status updates
   */
  subscribeToAgentUpdates(callback: (data: any) => void): void {
    this.wsService.subscribe('STATUS_CHANGE', callback);
    this.wsService.subscribe('CONFIG_UPDATE', callback);
    this.wsService.subscribe('SIGNAL_GENERATED', callback);
  }

  /**
   * Unsubscribe from all events
   */
  unsubscribeAll(): void {
    // This would need to be implemented based on the WebSocketService API
    console.log('Unsubscribing from all WebSocket events');
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): {
    api: boolean;
    websocket: boolean;
  } {
    return {
      api: this.apiService.isAuthenticated(),
      websocket: this.wsService.getConnectionStatus(),
    };
  }

  /**
   * Get API service instance
   */
  getApiService(): ApiService {
    return this.apiService;
  }

  /**
   * Get WebSocket service instance
   */
  getWebSocketService(): WebSocketService {
    return this.wsService;
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.wsService.destroy();
    this.isInitialized = false;
  }
}

// Create singleton instance
export const backendIntegration = new BackendIntegration();