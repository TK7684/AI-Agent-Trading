/**
 * Integration Service
 * Manages the connection and data flow between frontend and Python backend
 */

import { ApiService } from './apiService';
import { WebSocketService } from './websocketService';
import { NotificationService } from './notificationService';
import { API_ENDPOINTS, WEBSOCKET_ENDPOINTS } from '@/utils/constants';
import type {
  LoginRequest,
  LoginResponse,
  PerformanceMetrics,
  AgentStatus,
  SystemHealth,
  TradingUpdate,
  SystemUpdate,
  AnyWebSocketMessage,
} from '@/types';

export interface IntegrationConfig {
  apiBaseUrl?: string;
  wsBaseUrl?: string;
  authEnabled?: boolean;
  debugMode?: boolean;
  autoReconnect?: boolean;
}

export interface ConnectionStatus {
  api: boolean;
  websocket: boolean;
  authenticated: boolean;
  lastUpdate: Date;
}

export class IntegrationService {
  private apiService: ApiService;
  private wsService: WebSocketService;
  private notificationService: NotificationService;
  private config: IntegrationConfig;
  private connectionStatus: ConnectionStatus;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private dataUpdateCallbacks: Map<string, Set<(data: any) => void>> = new Map();

  constructor(config: IntegrationConfig = {}) {
    this.config = {
      apiBaseUrl: config.apiBaseUrl || API_ENDPOINTS.BASE_URL,
      wsBaseUrl: config.wsBaseUrl || WEBSOCKET_ENDPOINTS.BASE_URL,
      authEnabled: config.authEnabled ?? true,
      debugMode: config.debugMode ?? false,
      autoReconnect: config.autoReconnect ?? true,
    };

    this.connectionStatus = {
      api: false,
      websocket: false,
      authenticated: false,
      lastUpdate: new Date(),
    };

    // Initialize services
    this.apiService = new ApiService(this.config.apiBaseUrl);
    this.wsService = new WebSocketService({
      url: this.config.wsBaseUrl,
      maxReconnectAttempts: this.config.autoReconnect ? 10 : 0,
    });
    this.notificationService = new NotificationService();

    this.setupWebSocketHandlers();
    this.setupApiInterceptors();
  }

  /**
   * Initialize the integration service
   */
  async initialize(): Promise<void> {
    try {
      // Test API connection
      await this.testApiConnection();
      
      // Connect WebSocket if API is available
      if (this.connectionStatus.api) {
        await this.connectWebSocket();
      }

      // Start health monitoring
      this.startHealthMonitoring();

      this.log('Integration service initialized successfully');
    } catch (error) {
      this.log('Failed to initialize integration service:', error);
      throw error;
    }
  }

  /**
   * Authenticate with the backend
   */
  async authenticate(credentials: LoginRequest): Promise<LoginResponse | null> {
    try {
      const response = await this.apiService.login(credentials);
      
      if (response.success && response.data) {
        this.connectionStatus.authenticated = true;
        this.connectionStatus.lastUpdate = new Date();
        
        // Set token for WebSocket
        this.wsService.setToken(response.data.token);
        
        // Reconnect WebSocket with authentication
        if (this.wsService.getConnectionStatus()) {
          this.wsService.disconnect();
        }
        await this.connectWebSocket();
        
        this.log('Authentication successful');
        return response.data;
      } else {
        this.log('Authentication failed:', response.error);
        return null;
      }
    } catch (error) {
      this.log('Authentication error:', error);
      return null;
    }
  }

  /**
   * Logout and disconnect
   */
  async logout(): Promise<void> {
    try {
      await this.apiService.logout();
      this.wsService.disconnect();
      this.connectionStatus.authenticated = false;
      this.connectionStatus.websocket = false;
      this.connectionStatus.lastUpdate = new Date();
      
      this.log('Logout successful');
    } catch (error) {
      this.log('Logout error:', error);
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): ConnectionStatus {
    return { ...this.connectionStatus };
  }

  /**
   * Subscribe to real-time data updates
   */
  subscribeToUpdates(type: string, callback: (data: any) => void): void {
    if (!this.dataUpdateCallbacks.has(type)) {
      this.dataUpdateCallbacks.set(type, new Set());
    }
    this.dataUpdateCallbacks.get(type)!.add(callback);

    // Subscribe to WebSocket events
    this.wsService.subscribe(type, callback);
  }

  /**
   * Unsubscribe from real-time data updates
   */
  unsubscribeFromUpdates(type: string, callback: (data: any) => void): void {
    const callbacks = this.dataUpdateCallbacks.get(type);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.dataUpdateCallbacks.delete(type);
      }
    }

    this.wsService.unsubscribe(type, callback);
  }

  /**
   * Fetch trading performance data
   */
  async getPerformanceData(): Promise<PerformanceMetrics | null> {
    try {
      const response = await this.apiService.getPerformance({ period: 'day' });
      return response.success ? response.data : null;
    } catch (error) {
      this.log('Error fetching performance data:', error);
      return null;
    }
  }

  /**
   * Fetch agent status
   */
  async getAgentStatus(): Promise<AgentStatus | null> {
    try {
      const response = await this.apiService.getAgentStatus();
      return response.success ? response.data : null;
    } catch (error) {
      this.log('Error fetching agent status:', error);
      return null;
    }
  }

  /**
   * Fetch system health
   */
  async getSystemHealth(): Promise<SystemHealth | null> {
    try {
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
      }
      return null;
    } catch (error) {
      this.log('Error fetching system health:', error);
      return null;
    }
  }

  /**
   * Control trading agent
   */
  async controlAgent(agentId: string, action: 'start' | 'stop' | 'pause' | 'resume' | 'restart'): Promise<boolean> {
    try {
      const response = await this.apiService.controlAgent(agentId, { action });
      return response.success;
    } catch (error) {
      this.log('Error controlling agent:', error);
      return false;
    }
  }

  /**
   * Test API connection
   */
  private async testApiConnection(): Promise<void> {
    try {
      // Try to fetch system health as a connection test
      const response = await fetch(`${this.config.apiBaseUrl}/system/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      this.connectionStatus.api = response.ok;
      this.connectionStatus.lastUpdate = new Date();
      
      if (!response.ok) {
        throw new Error(`API connection test failed: ${response.status}`);
      }
      
      this.log('API connection test successful');
    } catch (error) {
      this.connectionStatus.api = false;
      this.log('API connection test failed:', error);
      throw error;
    }
  }

  /**
   * Connect to WebSocket
   */
  private async connectWebSocket(): Promise<void> {
    try {
      await this.wsService.connect();
      this.connectionStatus.websocket = this.wsService.getConnectionStatus();
      this.connectionStatus.lastUpdate = new Date();
      
      this.log('WebSocket connection established');
    } catch (error) {
      this.connectionStatus.websocket = false;
      this.log('WebSocket connection failed:', error);
      throw error;
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupWebSocketHandlers(): void {
    this.wsService.setEventHandlers({
      onOpen: () => {
        this.connectionStatus.websocket = true;
        this.connectionStatus.lastUpdate = new Date();
        this.log('WebSocket connected');
        
        // Subscribe to default channels
        this.wsService.subscribeToChannel('trading');
        this.wsService.subscribeToChannel('system');
        this.wsService.subscribeToChannel('notifications');
      },
      
      onClose: () => {
        this.connectionStatus.websocket = false;
        this.connectionStatus.lastUpdate = new Date();
        this.log('WebSocket disconnected');
      },
      
      onError: (error) => {
        this.connectionStatus.websocket = false;
        this.connectionStatus.lastUpdate = new Date();
        this.log('WebSocket error:', error);
      },
      
      onMessage: (message: AnyWebSocketMessage) => {
        this.handleWebSocketMessage(message);
      },
      
      onReconnect: (attempt: number) => {
        this.log(`WebSocket reconnection attempt ${attempt}`);
      },
    });
  }

  /**
   * Setup API request/response interceptors
   */
  private setupApiInterceptors(): void {
    // Add request interceptor for debugging
    if (this.config.debugMode) {
      this.apiService.addRequestInterceptor({
        onRequest: async (config) => {
          this.log('API Request:', config.method, config.url);
          return config;
        },
      });

      this.apiService.addResponseInterceptor({
        onResponse: (response) => {
          this.log('API Response:', response.success ? 'SUCCESS' : 'ERROR');
          return response;
        },
      });
    }
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleWebSocketMessage(message: AnyWebSocketMessage): void {
    this.log('WebSocket message received:', message.type);

    // Route message to subscribers
    const callbacks = this.dataUpdateCallbacks.get(message.type);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(message.data);
        } catch (error) {
          this.log('Error in message callback:', error);
        }
      });
    }

    // Handle specific message types
    switch (message.type) {
      case 'TRADE_OPENED':
      case 'TRADE_CLOSED':
      case 'POSITION_UPDATE':
        this.handleTradingUpdate(message as TradingUpdate);
        break;
        
      case 'HEALTH_UPDATE':
      case 'METRICS_UPDATE':
        this.handleSystemUpdate(message as SystemUpdate);
        break;
        
      case 'NOTIFICATION':
        this.handleNotification(message.data);
        break;
        
      case 'PONG':
        // Handle heartbeat response
        break;
        
      default:
        this.log('Unknown message type:', message.type);
    }
  }

  /**
   * Handle trading updates
   */
  private handleTradingUpdate(update: TradingUpdate): void {
    // Emit to all trading update subscribers
    const callbacks = this.dataUpdateCallbacks.get('trading');
    if (callbacks) {
      callbacks.forEach(callback => callback(update));
    }
  }

  /**
   * Handle system updates
   */
  private handleSystemUpdate(update: SystemUpdate): void {
    // Emit to all system update subscribers
    const callbacks = this.dataUpdateCallbacks.get('system');
    if (callbacks) {
      callbacks.forEach(callback => callback(update));
    }
  }

  /**
   * Handle notifications
   */
  private handleNotification(notification: any): void {
    this.notificationService.show(notification);
  }

  /**
   * Start health monitoring
   */
  private startHealthMonitoring(): void {
    this.healthCheckInterval = setInterval(async () => {
      try {
        // Check API health
        if (this.connectionStatus.api) {
          await this.testApiConnection();
        }

        // Check WebSocket health
        this.connectionStatus.websocket = this.wsService.getConnectionStatus();
        this.connectionStatus.lastUpdate = new Date();
        
      } catch (error) {
        this.log('Health check failed:', error);
      }
    }, 30000); // Check every 30 seconds
  }

  /**
   * Stop health monitoring
   */
  private stopHealthMonitoring(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  /**
   * Logging utility
   */
  private log(message: string, ...args: any[]): void {
    if (this.config.debugMode) {
      console.log(`[IntegrationService] ${message}`, ...args);
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopHealthMonitoring();
    this.wsService.disconnect();
    this.dataUpdateCallbacks.clear();
    this.log('Integration service destroyed');
  }
}

// Export singleton instance
export const integrationService = new IntegrationService({
  apiBaseUrl: import.meta.env.VITE_BACKEND_API_URL,
  wsBaseUrl: import.meta.env.VITE_BACKEND_WS_URL,
  authEnabled: import.meta.env.VITE_AUTH_ENABLED === 'true',
  debugMode: import.meta.env.VITE_DEBUG_MODE === 'true',
  autoReconnect: true,
});