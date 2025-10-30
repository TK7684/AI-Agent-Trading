/**
 * System health and monitoring related TypeScript interfaces
 */

export interface SystemHealth {
  cpu: number; // CPU usage percentage (0-100)
  memory: number; // Memory usage percentage (0-100)
  diskUsage: number; // Disk usage percentage (0-100)
  networkLatency: number; // Network latency in milliseconds
  errorRate: number; // Error rate percentage (0-100)
  uptime: number; // System uptime in seconds
  connections: ConnectionStatus;
  lastUpdate: Date;
}

export interface ConnectionStatus {
  database: boolean;
  broker: boolean;
  llm: boolean;
  websocket: boolean;
}

export interface SystemAlert {
  id: string;
  type: 'performance' | 'connection' | 'error' | 'warning';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  timestamp: Date;
  resolved: boolean;
  source: string;
}

export interface AgentStatus {
  state: 'running' | 'paused' | 'stopped' | 'error' | 'starting' | 'stopping';
  uptime: number; // in seconds
  lastAction: Date;
  activePositions: number;
  dailyTrades: number;
  version: string;
  configHash?: string;
}

export interface AgentConfig {
  symbols: string[];
  timeframes: SystemTimeframe[];
  riskLimits: RiskLimits;
  tradingHours: TradingHours;
  llmConfig: LLMConfig;
  enabled: boolean;
}

export interface RiskLimits {
  maxDailyLoss: number;
  maxDrawdown: number;
  maxPositions: number;
  maxPositionSize: number;
  stopLossPercent: number;
  takeProfitPercent: number;
}

export interface TradingHours {
  enabled: boolean;
  start: string; // HH:MM format
  end: string; // HH:MM format
  timezone: string;
  weekendsEnabled: boolean;
}

export interface LLMConfig {
  provider: string;
  model: string;
  temperature: number;
  maxTokens: number;
  timeout: number; // in milliseconds
}

export interface SystemPerformanceMetrics {
  responseTime: number; // Average response time in ms
  successRate: number; // Success rate percentage (0-100)
  errorCount: number;
  requestCount: number;
  lastHour: {
    requests: number;
    errors: number;
    avgResponseTime: number;
  };
}

export interface DatabaseMetrics {
  connectionCount: number;
  queryTime: number; // Average query time in ms
  slowQueries: number;
  connectionPool: {
    active: number;
    idle: number;
    total: number;
  };
}

export interface BrokerMetrics {
  connectionStatus: boolean;
  latency: number; // in milliseconds
  orderExecutionTime: number; // Average order execution time in ms
  failedOrders: number;
  successfulOrders: number;
}

export type SystemState = 'healthy' | 'warning' | 'critical' | 'unknown';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AgentState = 'running' | 'paused' | 'stopped' | 'error' | 'starting' | 'stopping';
export type SystemTimeframe = '15m' | '1h' | '4h' | '1d';