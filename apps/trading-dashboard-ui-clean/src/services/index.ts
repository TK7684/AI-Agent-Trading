// Service initialization and configuration
import { ApiService } from './apiService';
import { WebSocketService } from './websocketService';
import { API_ENDPOINTS, WEBSOCKET_ENDPOINTS } from '@/utils/constants';

// Initialize API service with environment configuration
export const apiService = new ApiService(API_ENDPOINTS.BASE_URL);

// Initialize WebSocket service with environment configuration
export const webSocketService = new WebSocketService({
  url: WEBSOCKET_ENDPOINTS.BASE_URL,
  maxReconnectAttempts: 10,
  reconnectInterval: 5000,
  heartbeatInterval: 30000,
  timeout: 10000,
});

// Set up authentication token management
export const setAuthToken = (token: string, refreshToken?: string) => {
  apiService.setAuthToken(token, refreshToken);
  webSocketService.setToken(token);
};

export const clearAuthToken = () => {
  apiService.clearAuthToken();
  webSocketService.setToken(undefined);
};

// Export services
export { ApiService, WebSocketService };
export * from './apiService';
export * from './websocketService';
export * from './offlineService';
export * from './persistenceService';