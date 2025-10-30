/**
 * Main types export file
 */

// Trading types
export * from './trading';
export * from './system';
export * from './notifications';
export * from './websocket';
export * from './api';

// Re-export commonly used types with aliases for convenience
export type {
  PerformanceMetrics as TradingPerformance,
  TradeLogEntry as Trade,
  TradingSignal as Signal,
  Portfolio,
  Position,
  ChartData,
} from './trading';

export type {
  SystemHealth,
  AgentStatus,
  AgentConfig,
  SystemAlert,
} from './system';

export type {
  Notification,
  NotificationPreferences,
  ToastNotification,
} from './notifications';

export type {
  WebSocketMessage,
  TradingUpdate,
  SystemUpdate,
  AgentUpdate,
} from './websocket';

export type {
  ApiResponse,
  PaginatedResponse,
  ApiError,
  LoginResponse,
  User,
} from './api';