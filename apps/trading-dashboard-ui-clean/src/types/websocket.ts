/**
 * WebSocket message types and real-time communication interfaces
 */

import type { TradeLogEntry, PerformanceMetrics, TradingSignal, Position } from './trading';
import type { SystemHealth, AgentStatus, AgentConfig } from './system';
import type { Notification } from './notifications';

// Base WebSocket message structure
export interface WebSocketMessage<T = any> {
  type: string;
  data: T;
  timestamp: Date;
  id: string;
  channel?: string;
}

// Trading-related WebSocket messages
export interface TradingUpdate extends WebSocketMessage {
  type: 'TRADE_OPENED' | 'TRADE_CLOSED' | 'TRADE_UPDATED' | 'POSITION_UPDATE' | 'PNL_UPDATE';
  data: TradeLogEntry | PerformanceMetrics | Position;
}

export interface TradingSignalUpdate extends WebSocketMessage {
  type: 'SIGNAL_GENERATED' | 'SIGNAL_EXECUTED' | 'SIGNAL_CANCELLED';
  data: TradingSignal;
}

// System-related WebSocket messages
export interface SystemUpdate extends WebSocketMessage {
  type: 'METRICS_UPDATE' | 'HEALTH_CHECK' | 'HEALTH_UPDATE' | 'ERROR_ALERT' | 'CONNECTION_STATUS';
  data: SystemHealth | Notification;
}

// Agent-related WebSocket messages
export interface AgentUpdate extends WebSocketMessage {
  type: 'STATUS_CHANGE' | 'CONFIG_UPDATE' | 'AGENT_ERROR' | 'AGENT_LOG';
  data: AgentStatus | AgentConfig | { level: string; message: string };
}

// Notification WebSocket messages
export interface NotificationUpdate extends WebSocketMessage {
  type: 'NOTIFICATION_NEW' | 'NOTIFICATION_UPDATE' | 'NOTIFICATION_DISMISSED' | 'NOTIFICATION';
  data: Notification;
}

// Market data WebSocket messages
export interface MarketDataUpdate extends WebSocketMessage {
  type: 'PRICE_UPDATE' | 'CANDLE_UPDATE' | 'VOLUME_UPDATE' | 'ORDERBOOK_UPDATE';
  data: {
    symbol: string;
    price?: number;
    candle?: {
      time: number;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    };
    volume?: number;
    orderbook?: {
      bids: [number, number][];
      asks: [number, number][];
    };
  };
}

// WebSocket connection management
export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  timeout: number;
}

export interface WebSocketConnectionState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';
  lastConnected?: Date;
  lastDisconnected?: Date;
  reconnectAttempts: number;
  error?: string;
}

// WebSocket subscription management
export interface WebSocketSubscription {
  channel: string;
  params?: Record<string, any>;
  active: boolean;
  lastUpdate?: Date;
}

// Heartbeat and ping/pong messages
export interface HeartbeatMessage extends WebSocketMessage {
  type: 'PING' | 'PONG';
  data: {
    timestamp: number;
    clientId: string;
  };
}

// Error messages
export interface WebSocketError extends WebSocketMessage {
  type: 'ERROR';
  data: {
    code: string;
    message: string;
    details?: any;
  };
}

// Authentication messages
export interface AuthMessage extends WebSocketMessage {
  type: 'AUTH_REQUEST' | 'AUTH_SUCCESS' | 'AUTH_FAILURE';
  data: {
    token?: string;
    userId?: string;
    permissions?: string[];
    error?: string;
  };
}

// Union type for all possible WebSocket messages
export type AnyWebSocketMessage = 
  | TradingUpdate
  | TradingSignalUpdate
  | SystemUpdate
  | AgentUpdate
  | NotificationUpdate
  | MarketDataUpdate
  | HeartbeatMessage
  | WebSocketError
  | AuthMessage;

// WebSocket event handlers
export interface WebSocketEventHandlers {
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: AnyWebSocketMessage) => void;
  onReconnect?: (attempt: number) => void;
  onReconnectFailed?: () => void;
}

// Channel-specific message types
export type TradingChannelMessage = TradingUpdate | TradingSignalUpdate;
export type SystemChannelMessage = SystemUpdate;
export type AgentChannelMessage = AgentUpdate;
export type NotificationChannelMessage = NotificationUpdate;
export type MarketDataChannelMessage = MarketDataUpdate;