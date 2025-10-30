/**
 * Application constants and configuration values
 */

// Trading constants
export const TRADING_CONSTANTS = {
  // Timeframes
  TIMEFRAMES: ['15m', '1h', '4h', '1d'] as const,
  
  // Trade sides
  TRADE_SIDES: ['LONG', 'SHORT'] as const,
  
  // Trade statuses
  TRADE_STATUSES: ['OPEN', 'CLOSED', 'CANCELLED'] as const,
  
  // Signal types
  SIGNAL_TYPES: ['BUY', 'SELL'] as const,
  
  // Default values
  DEFAULT_RISK_PERCENTAGE: 2, // 2% risk per trade
  DEFAULT_STOP_LOSS_PERCENTAGE: 2, // 2% stop loss
  DEFAULT_TAKE_PROFIT_PERCENTAGE: 6, // 6% take profit (3:1 R:R)
  
  // Limits
  MAX_POSITION_SIZE: 1000000, // $1M max position size
  MIN_POSITION_SIZE: 10, // $10 min position size
  MAX_DAILY_TRADES: 100,
  MAX_OPEN_POSITIONS: 20,
} as const;

// System constants
export const SYSTEM_CONSTANTS = {
  // Agent states
  AGENT_STATES: ['running', 'paused', 'stopped', 'error', 'starting', 'stopping'] as const,
  
  // System states
  SYSTEM_STATES: ['healthy', 'warning', 'critical', 'unknown'] as const,
  
  // Alert severities
  ALERT_SEVERITIES: ['low', 'medium', 'high', 'critical'] as const,
  
  // Performance thresholds
  CPU_WARNING_THRESHOLD: 80, // 80% CPU usage
  CPU_CRITICAL_THRESHOLD: 95, // 95% CPU usage
  MEMORY_WARNING_THRESHOLD: 85, // 85% memory usage
  MEMORY_CRITICAL_THRESHOLD: 95, // 95% memory usage
  DISK_WARNING_THRESHOLD: 90, // 90% disk usage
  DISK_CRITICAL_THRESHOLD: 98, // 98% disk usage
  
  // Network thresholds
  NETWORK_LATENCY_WARNING: 500, // 500ms
  NETWORK_LATENCY_CRITICAL: 1000, // 1000ms
  
  // Error rate thresholds
  ERROR_RATE_WARNING: 5, // 5% error rate
  ERROR_RATE_CRITICAL: 10, // 10% error rate
} as const;

// Notification constants
export const NOTIFICATION_CONSTANTS = {
  // Types
  NOTIFICATION_TYPES: ['info', 'success', 'warning', 'error', 'trade', 'system', 'agent'] as const,
  
  // Priorities
  NOTIFICATION_PRIORITIES: ['low', 'normal', 'high', 'critical'] as const,
  
  // Categories
  NOTIFICATION_CATEGORIES: ['trading', 'system', 'performance', 'security', 'configuration', 'maintenance', 'user'] as const,
  
  // Sounds
  NOTIFICATION_SOUNDS: ['default', 'success', 'warning', 'error', 'trade', 'none'] as const,
  
  // Auto-dismiss durations (in milliseconds)
  TOAST_DURATION: {
    info: 5000,
    success: 4000,
    warning: 7000,
    error: 0, // Don't auto-dismiss errors
    trade: 6000,
    system: 8000,
    agent: 5000,
  },
  
  // Maximum notifications to keep in memory
  MAX_NOTIFICATIONS_HISTORY: 1000,
  MAX_TOAST_NOTIFICATIONS: 5,
} as const;

// UI constants
export const UI_CONSTANTS = {
  // Breakpoints (in pixels)
  BREAKPOINTS: {
    mobile: 320,
    tablet: 768,
    desktop: 1024,
    wide: 1440,
  },
  
  // Grid layout
  GRID_LAYOUT: {
    cols: { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 },
    rowHeight: 60,
    margin: [10, 10] as [number, number],
    containerPadding: [10, 10] as [number, number],
  },
  
  // Widget dimensions
  WIDGET_SIZES: {
    small: { w: 3, h: 4 },
    medium: { w: 6, h: 6 },
    large: { w: 9, h: 8 },
    full: { w: 12, h: 10 },
  },
  
  // Animation durations (in milliseconds)
  ANIMATION_DURATION: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
  
  // Debounce delays (in milliseconds)
  DEBOUNCE_DELAY: {
    search: 300,
    resize: 100,
    scroll: 50,
    input: 500,
  },
  
  // Polling intervals (in milliseconds)
  POLLING_INTERVALS: {
    realtime: 1000, // 1 second
    frequent: 5000, // 5 seconds
    normal: 30000, // 30 seconds
    slow: 60000, // 1 minute
  },
} as const;

import { env } from '@/config/environment';

// API endpoints
export const API_ENDPOINTS = {
  BASE_URL: env.apiBaseUrl,
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    VERIFY: '/auth/verify',
  },
  TRADING: {
    POSITIONS: '/trading/positions',
    TRADES: '/trading/trades',
    SIGNALS: '/trading/signals',
    PERFORMANCE: '/trading/performance',
  },
  SYSTEM: {
    HEALTH: '/system/health',
    AGENTS: '/system/agents',
    METRICS: '/system/metrics',
    CONFIG: '/system/config',
  },
} as const;

// WebSocket endpoints
export const WEBSOCKET_ENDPOINTS = {
  BASE_URL: env.wsBaseUrl,
  TRADING: '/ws/trading',
  SYSTEM: '/ws/system',
  MARKET_DATA: '/ws/market-data',
  NOTIFICATIONS: '/ws/notifications',
} as const;

// API constants
export const API_CONSTANTS = {
  // Request timeouts (in milliseconds)
  TIMEOUT: {
    default: 10000, // 10 seconds
    upload: 60000, // 1 minute
    download: 120000, // 2 minutes
  },
  
  // Retry configuration
  RETRY: {
    attempts: 3,
    delay: 1000, // 1 second
    backoffMultiplier: 2,
  },
  
  // Pagination
  PAGINATION: {
    defaultPageSize: 20,
    maxPageSize: 100,
    pageSizeOptions: [10, 20, 50, 100],
  },
  
  // WebSocket
  WEBSOCKET: {
    reconnectInterval: 5000, // 5 seconds
    maxReconnectAttempts: 10,
    heartbeatInterval: 30000, // 30 seconds
    timeout: 5000, // 5 seconds
  },
} as const;

// Chart constants
export const CHART_CONSTANTS = {
  // Colors
  COLORS: {
    bullish: '#00C851', // Green
    bearish: '#FF4444', // Red
    neutral: '#33B5E5', // Blue
    warning: '#FF8800', // Orange
    background: '#1E1E1E', // Dark background
    grid: '#2A2A2A', // Grid lines
    text: '#FFFFFF', // Text color
  },
  
  // Technical indicators
  INDICATORS: {
    MA: {
      periods: [9, 21, 50, 200],
      colors: ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1'],
    },
    RSI: {
      period: 14,
      overbought: 70,
      oversold: 30,
    },
    MACD: {
      fastPeriod: 12,
      slowPeriod: 26,
      signalPeriod: 9,
    },
    BOLLINGER: {
      period: 20,
      standardDeviations: 2,
    },
  },
  
  // Chart settings
  SETTINGS: {
    candleWidth: 0.8,
    volumeHeight: 0.3, // 30% of chart height
    indicatorHeight: 0.2, // 20% of chart height
    minPriceScale: 0.01,
    maxVisibleBars: 500,
  },
} as const;

// Validation constants
export const VALIDATION_CONSTANTS = {
  // String lengths
  MIN_PASSWORD_LENGTH: 8,
  MAX_PASSWORD_LENGTH: 128,
  MAX_USERNAME_LENGTH: 50,
  MAX_EMAIL_LENGTH: 254,
  MAX_SYMBOL_LENGTH: 20,
  MAX_NOTIFICATION_TITLE_LENGTH: 200,
  MAX_NOTIFICATION_MESSAGE_LENGTH: 1000,
  
  // Numeric ranges
  MIN_CONFIDENCE: 0,
  MAX_CONFIDENCE: 100,
  MIN_PRICE: 0.000001,
  MAX_PRICE: 1000000000,
  MIN_QUANTITY: 0.000001,
  MAX_QUANTITY: 1000000000,
  
  // Regex patterns
  PATTERNS: {
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    time: /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/,
    symbol: /^[A-Z0-9]+$/,
    hexColor: /^#[0-9A-Fa-f]{6}$/,
  },
} as const;

// Local storage keys
export const LOCAL_STORAGE_KEYS = {
  DASHBOARD_LAYOUT: 'trading-dashboard-layout',
  USER_PREFERENCES: 'trading-dashboard-preferences',
  NOTIFICATION_SETTINGS: 'trading-dashboard-notifications',
  THEME_SETTINGS: 'trading-dashboard-theme',
  AUTH_TOKEN: 'trading-dashboard-auth-token',
  REFRESH_TOKEN: 'trading-dashboard-refresh-token',
  WIDGET_SETTINGS: 'trading-dashboard-widgets',
  CHART_SETTINGS: 'trading-dashboard-charts',
} as const;

// Export all constants as a single object for convenience
export const CONSTANTS = {
  TRADING: TRADING_CONSTANTS,
  SYSTEM: SYSTEM_CONSTANTS,
  NOTIFICATION: NOTIFICATION_CONSTANTS,
  UI: UI_CONSTANTS,
  API: API_CONSTANTS,
  CHART: CHART_CONSTANTS,
  VALIDATION: VALIDATION_CONSTANTS,
  LOCAL_STORAGE: LOCAL_STORAGE_KEYS,
} as const;