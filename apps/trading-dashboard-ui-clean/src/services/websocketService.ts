// WebSocket service for real-time data connection
import { API_CONSTANTS, WEBSOCKET_ENDPOINTS } from '@/utils/constants';
import type { 
  // TradingUpdate, 
  // SystemUpdate, 
  AnyWebSocketMessage,
  WebSocketConfig,
  WebSocketConnectionState,
  WebSocketEventHandlers,
  WebSocketSubscription
} from '@/types';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private heartbeatInterval: number;
  private timeout: number;
  private isConnecting = false;
  private isReconnecting = false;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private connectionTimeout: NodeJS.Timeout | null = null;
  
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private subscriptions: Map<string, WebSocketSubscription> = new Map();
  private eventHandlers: WebSocketEventHandlers = {};
  
  private connectionState: WebSocketConnectionState = {
    status: 'disconnected',
    reconnectAttempts: 0,
  };
  
  private clientId: string;
  private baseUrl: string;
  private token?: string;
  
  constructor(config?: Partial<WebSocketConfig>) {
    this.maxReconnectAttempts = config?.maxReconnectAttempts ?? API_CONSTANTS.WEBSOCKET.maxReconnectAttempts;
    this.reconnectDelay = config?.reconnectInterval ?? API_CONSTANTS.WEBSOCKET.reconnectInterval;
    this.heartbeatInterval = config?.heartbeatInterval ?? API_CONSTANTS.WEBSOCKET.heartbeatInterval;
    this.timeout = config?.timeout ?? API_CONSTANTS.WEBSOCKET.timeout;
    this.baseUrl = config?.url ?? WEBSOCKET_ENDPOINTS.BASE_URL;
    this.clientId = this.generateClientId();
    this.token = (config as any)?.token;
    
    // Bind methods to preserve context
    this.handleOpen = this.handleOpen.bind(this);
    this.handleClose = this.handleClose.bind(this);
    this.handleError = this.handleError.bind(this);
    this.handleMessage = this.handleMessage.bind(this);
  }
  
  setToken(token?: string): void {
    this.token = token;
  }
  
  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    if (this.isConnecting || this.connectionState.status === 'connected') {
      return;
    }
    
    try {
      this.isConnecting = true;
      this.updateConnectionState('connecting');
      
      const query = new URLSearchParams();
      query.set('clientId', this.clientId);
      if (this.token) query.set('token', this.token);
      const wsUrl = `${this.baseUrl}${WEBSOCKET_ENDPOINTS.TRADING}?${query.toString()}`;
      this.ws = new WebSocket(wsUrl);
      
      // Set up event handlers
      this.ws.addEventListener('open', this.handleOpen);
      this.ws.addEventListener('close', this.handleClose);
      this.ws.addEventListener('error', this.handleError);
      this.ws.addEventListener('message', this.handleMessage);
      
      // Set connection timeout
      this.connectionTimeout = setTimeout(() => {
        if (this.connectionState.status === 'connecting') {
          this.handleConnectionTimeout();
        }
      }, this.timeout);
      
    } catch (error) {
      this.handleConnectionError(error as Error);
    }
  }
  
  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.cleanup();
    this.updateConnectionState('disconnected');
  }
  
  /**
   * Subscribe to a specific event/channel
   */
  subscribe(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
    
    // If connected, send subscription message
    if (this.connectionState.status === 'connected') {
      this.sendSubscriptionMessage(event);
    }
  }
  
  /**
   * Unsubscribe from a specific event/channel
   */
  unsubscribe(event: string, callback: (data: any) => void): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(callback);
      if (eventListeners.size === 0) {
        this.listeners.delete(event);
        // Send unsubscription message if connected
        if (this.connectionState.status === 'connected') {
          this.sendUnsubscriptionMessage(event);
        }
      }
    }
  }
  
  /**
   * Send a message to the WebSocket server
   */
  send(message: any): void {
    if (this.ws && this.connectionState.status === 'connected') {
      try {
        const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
        this.ws.send(messageStr);
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        this.handleError(error as Event);
      }
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
    }
  }
  
  /**
   * Get current connection status
   */
  getConnectionStatus(): boolean {
    return this.connectionState.status === 'connected';
  }
  
  /**
   * Get detailed connection state
   */
  getConnectionState(): WebSocketConnectionState {
    return { ...this.connectionState };
  }

  /**
   * Get base URL for debugging
   */
  getBaseUrl(): string {
    return this.baseUrl;
  }
  
  /**
   * Set event handlers for WebSocket events
   */
  setEventHandlers(handlers: WebSocketEventHandlers): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };
  }
  
  /**
   * Subscribe to a specific channel with parameters
   */
  subscribeToChannel(channel: string, params?: Record<string, any>): void {
    const subscription: WebSocketSubscription = {
      channel,
      params,
      active: true,
      lastUpdate: new Date(),
    };
    
    this.subscriptions.set(channel, subscription);
    
    if (this.connectionState.status === 'connected') {
      this.send({
        type: 'SUBSCRIBE',
        channel,
        params,
        clientId: this.clientId,
      });
    }
  }
  
  /**
   * Unsubscribe from a specific channel
   */
  unsubscribeFromChannel(channel: string): void {
    this.subscriptions.delete(channel);
    
    if (this.connectionState.status === 'connected') {
      this.send({
        type: 'UNSUBSCRIBE',
        channel,
        clientId: this.clientId,
      });
    }
  }
  
  /**
   * Handle WebSocket open event
   */
  private handleOpen(event: Event): void {
    this.isConnecting = false;
    this.isReconnecting = false;
    this.reconnectAttempts = 0;
    
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    
    this.updateConnectionState('connected', new Date());
    this.startHeartbeat();
    
    // Re-subscribe to channels after reconnection
    this.resubscribeToChannels();
    
    // Call custom event handler
    if (this.eventHandlers.onOpen) {
      this.eventHandlers.onOpen(event);
    }
    
    console.log('WebSocket connected successfully');
  }
  
  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    this.isConnecting = false;
    this.isReconnecting = false;
    
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    
    this.stopHeartbeat();
    this.updateConnectionState('disconnected', undefined, new Date());
    
    // Call custom event handler
    if (this.eventHandlers.onClose) {
      this.eventHandlers.onClose(event);
    }
    
    // Attempt reconnection if not manually disconnected
    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnection();
    }
    
    console.log('WebSocket disconnected:', event.code, event.reason);
  }
  
  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    this.updateConnectionState('error', undefined, undefined, 'WebSocket error occurred');
    
    // Call custom event handler
    if (this.eventHandlers.onError) {
      this.eventHandlers.onError(event);
    }
    
    console.error('WebSocket error:', event);
  }
  
  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: AnyWebSocketMessage = JSON.parse(event.data);
      
      // Call custom message handler
      if (this.eventHandlers.onMessage) {
        this.eventHandlers.onMessage(message);
      }
      
      // Route message to appropriate listeners
      this.routeMessage(message);
      
      // Update subscription last update time
      if (message.channel) {
        const subscription = this.subscriptions.get(message.channel);
        if (subscription) {
          subscription.lastUpdate = new Date();
        }
      }
      
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }
  
  /**
   * Route incoming messages to appropriate listeners
   */
  private routeMessage(message: AnyWebSocketMessage): void {
    // Route by message type
    const typeListeners = this.listeners.get(message.type);
    if (typeListeners) {
      typeListeners.forEach(callback => {
        try {
          callback(message.data);
        } catch (error) {
          console.error('Error in message listener:', error);
        }
      });
    }
    
    // Route by channel if specified
    if (message.channel) {
      const channelListeners = this.listeners.get(`channel:${message.channel}`);
      if (channelListeners) {
        channelListeners.forEach(callback => {
          try {
            callback(message.data);
          } catch (error) {
            console.error('Error in channel listener:', error);
          }
        });
      }
    }
  }
  
  /**
   * Handle connection timeout
   */
  private handleConnectionTimeout(): void {
    this.isConnecting = false;
    this.updateConnectionState('error', undefined, undefined, 'Connection timeout');
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    // Attempt reconnection
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnection();
    }
  }
  
  /**
   * Handle connection errors
   */
  private handleConnectionError(error: Error): void {
    this.isConnecting = false;
    this.updateConnectionState('error', undefined, undefined, error.message);
    
    // Attempt reconnection
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnection();
    }
  }
  
  /**
   * Schedule reconnection with exponential backoff
   */
  private scheduleReconnection(): void {
    if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }
    
    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );
    
    this.updateConnectionState('reconnecting');
    
    // Call custom reconnect handler
    if (this.eventHandlers.onReconnect) {
      this.eventHandlers.onReconnect(this.reconnectAttempts);
    }
    
    this.reconnectTimer = setTimeout(() => {
      this.isReconnecting = false;
      this.connect();
    }, delay);
    
    console.log(`Scheduling WebSocket reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
  }
  
  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.connectionState.status === 'connected') {
        this.send({
          type: 'PING',
          data: {
            timestamp: Date.now(),
            clientId: this.clientId,
          },
        });
      }
    }, this.heartbeatInterval);
  }
  
  /**
   * Stop heartbeat timer
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  /**
   * Send subscription message to server
   */
  private sendSubscriptionMessage(event: string): void {
    this.send({
      type: 'SUBSCRIBE',
      event,
      clientId: this.clientId,
    });
  }
  
  /**
   * Send unsubscription message to server
   */
  private sendUnsubscriptionMessage(event: string): void {
    this.send({
      type: 'UNSUBSCRIBE',
      event,
      clientId: this.clientId,
    });
  }
  
  /**
   * Resubscribe to all active channels after reconnection
   */
  private resubscribeToChannels(): void {
    this.subscriptions.forEach((subscription, channel) => {
      if (subscription.active) {
        this.send({
          type: 'SUBSCRIBE',
          channel,
          params: subscription.params,
          clientId: this.clientId,
        });
      }
    });
  }
  
  /**
   * Update connection state
   */
  private updateConnectionState(
    status: WebSocketConnectionState['status'],
    lastConnected?: Date,
    lastDisconnected?: Date,
    error?: string
  ): void {
    this.connectionState = {
      ...this.connectionState,
      status,
      lastConnected: lastConnected || this.connectionState.lastConnected,
      lastDisconnected: lastDisconnected || this.connectionState.lastDisconnected,
      reconnectAttempts: this.reconnectAttempts,
      error,
    };
  }
  
  /**
   * Clean up resources
   */
  private cleanup(): void {
    if (this.ws) {
      this.ws.removeEventListener('open', this.handleOpen);
      this.ws.removeEventListener('close', this.handleClose);
      this.ws.removeEventListener('error', this.handleError);
      this.ws.removeEventListener('message', this.handleMessage);
      this.ws.close();
      this.ws = null;
    }
    
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    
    this.isConnecting = false;
    this.isReconnecting = false;
  }
  
  /**
   * Generate unique client ID
   */
  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  /**
   * Destructor to clean up resources
   */
  destroy(): void {
    this.cleanup();
    this.listeners.clear();
    this.subscriptions.clear();
  }
}