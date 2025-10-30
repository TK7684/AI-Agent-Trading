# Trading Dashboard UI Design Document

## Overview

The Trading Dashboard UI is a modern, responsive web application that provides real-time monitoring and control capabilities for the autonomous trading system. Built using React with TypeScript, the dashboard integrates with the existing Python backend through WebSocket connections and REST APIs to deliver live trading data, performance metrics, and system controls. The interface emphasizes visual clarity, immediate feedback, and intuitive navigation to help traders monitor their AI agent's performance effectively.

## Architecture

### Frontend Architecture

```
Frontend (React + TypeScript)
├── Components/
│   ├── Dashboard/           # Main dashboard layout
│   ├── Trading/            # Trading-specific components
│   ├── Charts/             # Chart and visualization components
│   ├── Notifications/      # Alert and notification system
│   ├── Controls/           # Agent control components
│   └── Common/             # Shared UI components
├── Services/
│   ├── WebSocketService    # Real-time data connection
│   ├── ApiService          # REST API client
│   ├── NotificationService # Alert management
│   └── StorageService      # Local storage management
├── Stores/                 # State management (Zustand)
│   ├── TradingStore        # Trading data and metrics
│   ├── SystemStore         # System health and performance
│   ├── UIStore             # UI state and preferences
│   └── NotificationStore   # Notifications and alerts
└── Utils/
    ├── formatters.ts       # Data formatting utilities
    ├── calculations.ts     # Financial calculations
    └── constants.ts        # Application constants
```

### Backend Integration

```
Python Backend Integration
├── WebSocket Endpoints
│   ├── /ws/trading         # Real-time trading updates
│   ├── /ws/system          # System metrics stream
│   └── /ws/notifications   # Alert notifications
├── REST API Endpoints
│   ├── /api/trading/       # Trading data and history
│   ├── /api/system/        # System control and status
│   ├── /api/config/        # Configuration management
│   └── /api/health/        # Health checks
└── Data Models
    ├── TradingMetrics      # From monitoring.py
    ├── SystemMetrics       # From monitoring.py
    ├── Portfolio           # From base.py
    └── Trade               # From base.py
```

## Components and Interfaces

### 1. Main Dashboard Layout

**DashboardLayout Component**
- Responsive grid system using CSS Grid
- Collapsible sidebar navigation
- Header with system status indicators
- Main content area with widget containers
- Footer with connection status

```typescript
interface DashboardLayoutProps {
  children: React.ReactNode;
  sidebarCollapsed: boolean;
  onSidebarToggle: () => void;
}

interface WidgetConfig {
  id: string;
  type: 'performance' | 'chart' | 'logs' | 'controls' | 'system';
  position: { x: number; y: number; w: number; h: number };
  visible: boolean;
  config: Record<string, any>;
}
```

### 2. Performance Metrics Widget

**PerformanceWidget Component**
- Real-time P&L display with color coding
- Win rate and trade statistics
- Drawdown indicators with visual alerts
- Portfolio value and percentage changes

```typescript
interface PerformanceMetrics {
  totalPnl: number;
  dailyPnl: number;
  winRate: number;
  totalTrades: number;
  currentDrawdown: number;
  maxDrawdown: number;
  portfolioValue: number;
  dailyChange: number;
  dailyChangePercent: number;
}

interface PerformanceWidgetProps {
  metrics: PerformanceMetrics;
  isLoading: boolean;
  lastUpdate: Date;
}
```

### 3. Trading Charts Widget

**TradingChartsWidget Component**
- Multi-timeframe price charts using Lightweight Charts
- Technical indicator overlays
- Trading signal markers
- Interactive tooltips and crosshairs

```typescript
interface ChartData {
  symbol: string;
  timeframe: string;
  data: CandlestickData[];
  indicators: IndicatorData[];
  signals: SignalMarker[];
}

interface SignalMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown' | 'circle';
  text: string;
}

interface TradingChartsWidgetProps {
  symbols: string[];
  activeSymbol: string;
  activeTimeframe: string;
  onSymbolChange: (symbol: string) => void;
  onTimeframeChange: (timeframe: string) => void;
}
```

### 4. Trading Logs Widget

**TradingLogsWidget Component**
- Paginated trade history table
- Advanced filtering and search
- Export functionality
- Real-time log updates

```typescript
interface TradeLogEntry {
  id: string;
  timestamp: Date;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl?: number;
  status: 'OPEN' | 'CLOSED' | 'CANCELLED';
  pattern?: string;
  confidence: number;
}

interface LogFilter {
  dateRange: { start: Date; end: Date };
  symbols: string[];
  status: string[];
  profitLoss: 'all' | 'profit' | 'loss';
  searchText: string;
}

interface TradingLogsWidgetProps {
  logs: TradeLogEntry[];
  filter: LogFilter;
  onFilterChange: (filter: LogFilter) => void;
  onExport: (format: 'csv' | 'json') => void;
}
```

### 5. Agent Control Widget

**AgentControlWidget Component**
- Start/stop/pause controls
- Configuration forms
- Status indicators
- Emergency stop functionality

```typescript
interface AgentStatus {
  state: 'running' | 'paused' | 'stopped' | 'error';
  uptime: number;
  lastAction: Date;
  activePositions: number;
  dailyTrades: number;
}

interface AgentConfig {
  symbols: string[];
  timeframes: string[];
  riskLimits: {
    maxDailyLoss: number;
    maxDrawdown: number;
    maxPositions: number;
  };
  tradingHours: {
    enabled: boolean;
    start: string;
    end: string;
    timezone: string;
  };
}

interface AgentControlWidgetProps {
  status: AgentStatus;
  config: AgentConfig;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onPause: () => Promise<void>;
  onConfigUpdate: (config: AgentConfig) => Promise<void>;
}
```

### 6. Notification System

**NotificationCenter Component**
- Toast notifications for immediate alerts
- Notification history panel
- Sound alerts for critical events
- Customizable notification preferences

```typescript
interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent: boolean;
  actions?: NotificationAction[];
}

interface NotificationAction {
  label: string;
  action: () => void;
  style: 'primary' | 'secondary' | 'danger';
}

interface NotificationCenterProps {
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onDismiss: (id: string) => void;
  onClearAll: () => void;
}
```

### 7. System Health Widget

**SystemHealthWidget Component**
- Real-time system metrics
- Performance indicators
- Error rate monitoring
- Connection status

```typescript
interface SystemHealth {
  cpu: number;
  memory: number;
  diskUsage: number;
  networkLatency: number;
  errorRate: number;
  uptime: number;
  connections: {
    database: boolean;
    broker: boolean;
    llm: boolean;
  };
}

interface SystemHealthWidgetProps {
  health: SystemHealth;
  alerts: SystemAlert[];
  onRefresh: () => void;
}
```

## Data Models

### WebSocket Message Types

```typescript
// Real-time trading updates
interface TradingUpdate {
  type: 'TRADE_OPENED' | 'TRADE_CLOSED' | 'POSITION_UPDATE' | 'PNL_UPDATE';
  data: TradeLogEntry | PerformanceMetrics;
  timestamp: Date;
}

// System metrics updates
interface SystemUpdate {
  type: 'METRICS_UPDATE' | 'HEALTH_CHECK' | 'ERROR_ALERT';
  data: SystemHealth | Notification;
  timestamp: Date;
}

// Agent status updates
interface AgentUpdate {
  type: 'STATUS_CHANGE' | 'CONFIG_UPDATE' | 'SIGNAL_GENERATED';
  data: AgentStatus | AgentConfig | TradingSignal;
  timestamp: Date;
}
```

### API Response Types

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: Date;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}
```

## Error Handling

### Error Boundary Strategy

```typescript
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class DashboardErrorBoundary extends Component<Props, ErrorBoundaryState> {
  // Catches JavaScript errors anywhere in the child component tree
  // Logs errors and displays fallback UI
  // Provides error reporting functionality
}
```

### Connection Error Handling

```typescript
interface ConnectionManager {
  websocket: WebSocket | null;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  reconnectDelay: number;
  
  connect(): Promise<void>;
  disconnect(): void;
  reconnect(): Promise<void>;
  onConnectionLost(): void;
  onConnectionRestored(): void;
}
```

## Testing Strategy

### Unit Testing
- Component testing with React Testing Library
- Service layer testing with Jest
- State management testing with Zustand test utilities
- Utility function testing

### Integration Testing
- WebSocket connection testing
- API integration testing
- End-to-end user workflows
- Cross-browser compatibility testing

### Performance Testing
- Component rendering performance
- Large dataset handling
- Memory leak detection
- Bundle size optimization

## Security Considerations

### Authentication & Authorization
```typescript
interface AuthService {
  login(credentials: LoginCredentials): Promise<AuthResult>;
  logout(): Promise<void>;
  refreshToken(): Promise<string>;
  getCurrentUser(): User | null;
  hasPermission(permission: string): boolean;
}

interface SecurityHeaders {
  'Content-Security-Policy': string;
  'X-Frame-Options': string;
  'X-Content-Type-Options': string;
  'Strict-Transport-Security': string;
}
```

### Data Protection
- Sensitive data masking in logs
- Secure WebSocket connections (WSS)
- API key management
- Local storage encryption for preferences

## Performance Optimizations

### React Optimizations
```typescript
// Memoization for expensive calculations
const MemoizedChart = React.memo(TradingChart, (prevProps, nextProps) => {
  return prevProps.data === nextProps.data && 
         prevProps.symbol === nextProps.symbol;
});

// Virtual scrolling for large datasets
interface VirtualizedTableProps {
  items: any[];
  itemHeight: number;
  containerHeight: number;
  renderItem: (item: any, index: number) => React.ReactNode;
}
```

### Data Management
- Efficient state updates with Zustand
- Data normalization for complex nested structures
- Selective re-rendering with React.memo
- Debounced API calls for search and filters

### Bundle Optimization
- Code splitting by route and feature
- Dynamic imports for heavy components
- Tree shaking for unused code elimination
- Compression and minification

## Accessibility Features

### WCAG 2.1 Compliance
- Semantic HTML structure
- ARIA labels and roles
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Focus management

### Responsive Design
```typescript
interface BreakpointConfig {
  mobile: '320px';
  tablet: '768px';
  desktop: '1024px';
  wide: '1440px';
}

interface ResponsiveProps {
  breakpoint: keyof BreakpointConfig;
  children: React.ReactNode;
}
```

## Deployment Architecture

### Build Process
```typescript
interface BuildConfig {
  environment: 'development' | 'staging' | 'production';
  apiBaseUrl: string;
  websocketUrl: string;
  enableAnalytics: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
}
```

### Container Configuration
```dockerfile
# Multi-stage build for optimized production image
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### Environment Variables
```typescript
interface EnvironmentConfig {
  REACT_APP_API_URL: string;
  REACT_APP_WS_URL: string;
  REACT_APP_ENVIRONMENT: string;
  REACT_APP_VERSION: string;
  REACT_APP_SENTRY_DSN?: string;
}
```

This design provides a comprehensive foundation for building a professional trading dashboard that integrates seamlessly with your existing autonomous trading system while providing the friendly UX/UI experience you requested.