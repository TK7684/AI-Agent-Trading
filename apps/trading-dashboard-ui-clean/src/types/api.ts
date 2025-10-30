/**
 * REST API response structures and request types
 */

// Base API response structure
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  timestamp: Date;
  requestId?: string;
}

// Paginated API response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
  totalPages: number;
}

// API Error structure
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  field?: string; // For validation errors
  stack?: string; // Only in development
}

// Authentication types
export interface LoginRequest {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface LoginResponse {
  token: string;
  refreshToken: string;
  user: User;
  expiresAt: Date;
  permissions: string[];
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'trader' | 'viewer';
  preferences: UserPreferences;
  lastLogin?: Date;
  createdAt: Date;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  timezone: string;
  dashboardLayout: Record<string, any>;
  notifications: Record<string, boolean>;
}

// Trading API types
export interface TradingHistoryRequest {
  symbol?: string;
  startDate?: Date;
  endDate?: Date;
  status?: ('OPEN' | 'CLOSED' | 'CANCELLED')[];
  page?: number;
  pageSize?: number;
  sortBy?: 'timestamp' | 'symbol' | 'pnl';
  sortOrder?: 'asc' | 'desc';
}

export interface PerformanceRequest {
  period: 'day' | 'week' | 'month' | 'year' | 'all';
  startDate?: Date;
  endDate?: Date;
  groupBy?: 'day' | 'week' | 'month';
}

export interface ChartDataRequest {
  symbol: string;
  timeframe: '15m' | '1h' | '4h' | '1d';
  startTime?: Date;
  endTime?: Date;
  indicators?: string[];
  limit?: number;
}

// System API types
export interface SystemStatusResponse {
  status: 'healthy' | 'warning' | 'critical';
  uptime: number;
  version: string;
  environment: string;
  services: ServiceStatus[];
  lastHealthCheck: Date;
}

export interface ServiceStatus {
  name: string;
  status: 'online' | 'offline' | 'degraded';
  responseTime?: number;
  lastCheck: Date;
  error?: string;
}

export interface SystemMetricsRequest {
  period: 'hour' | 'day' | 'week';
  metrics: ('cpu' | 'memory' | 'disk' | 'network')[];
  resolution?: number; // Data points per period
}

// Agent control API types
export interface AgentControlRequest {
  action: 'start' | 'stop' | 'pause' | 'resume' | 'restart';
  force?: boolean; // For emergency stops
}

export interface AgentConfigUpdateRequest {
  symbols?: string[];
  timeframes?: string[];
  riskLimits?: Partial<{
    maxDailyLoss: number;
    maxDrawdown: number;
    maxPositions: number;
    maxPositionSize: number;
  }>;
  tradingHours?: Partial<{
    enabled: boolean;
    start: string;
    end: string;
    timezone: string;
  }>;
}

// Configuration API types
export interface ConfigurationResponse {
  trading: TradingConfig;
  system: SystemConfig;
  ui: UIConfig;
}

export interface TradingConfig {
  symbols: string[];
  timeframes: string[];
  defaultRiskLimits: Record<string, number>;
  brokerSettings: Record<string, any>;
}

export interface SystemConfig {
  logLevel: string;
  maxLogSize: number;
  backupEnabled: boolean;
  monitoringInterval: number;
}

export interface UIConfig {
  defaultTheme: string;
  availableLanguages: string[];
  defaultDashboardLayout: Record<string, any>;
  featureFlags: Record<string, boolean>;
}

// Notification API types
export interface NotificationListRequest {
  category?: string[];
  priority?: string[];
  read?: boolean;
  startDate?: Date;
  endDate?: Date;
  page?: number;
  pageSize?: number;
}

export interface NotificationUpdateRequest {
  read?: boolean;
  acknowledged?: boolean;
}

export interface BulkNotificationRequest {
  ids: string[];
  action: 'mark_read' | 'mark_unread' | 'delete' | 'acknowledge';
}

// Health check types
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  checks: HealthCheck[];
  timestamp: Date;
  duration: number; // Check duration in ms
}

export interface HealthCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn';
  duration: number;
  output?: string;
  error?: string;
}

// Export/Import types
export interface ExportRequest {
  type: 'trades' | 'performance' | 'logs' | 'configuration';
  format: 'csv' | 'json' | 'xlsx';
  filters?: Record<string, any>;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface ExportResponse {
  downloadUrl: string;
  filename: string;
  size: number;
  expiresAt: Date;
}

// Batch operation types
export interface BatchRequest<T> {
  operations: BatchOperation<T>[];
  transactional?: boolean; // All or nothing
}

export interface BatchOperation<T> {
  id: string;
  operation: 'create' | 'update' | 'delete';
  data: T;
}

export interface BatchResponse<T> {
  results: BatchResult<T>[];
  success: boolean;
  totalProcessed: number;
  totalErrors: number;
}

export interface BatchResult<T> {
  id: string;
  success: boolean;
  data?: T;
  error?: ApiError;
}

// Request/Response interceptor types
export interface RequestInterceptor {
  onRequest?: (config: RequestConfig) => RequestConfig | Promise<RequestConfig>;
  onRequestError?: (error: any) => any;
}

export interface ResponseInterceptor {
  onResponse?: (response: ApiResponse) => ApiResponse | Promise<ApiResponse>;
  onResponseError?: (error: any) => any;
}

export interface RequestConfig {
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  params?: Record<string, any>;
  data?: any;
  timeout?: number;
  retries?: number;
  dedupe?: boolean;
}

// Common query parameters
export interface CommonQueryParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  search?: string;
  filters?: Record<string, any>;
}