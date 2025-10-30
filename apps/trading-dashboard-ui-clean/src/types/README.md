# Trading Dashboard UI - Data Models and Types

This directory contains all TypeScript interfaces, types, and Zod validation schemas for the trading dashboard UI application.

## Overview

The data models are organized into several categories:

- **Trading**: Core trading-related data structures
- **System**: System health and agent management
- **Notifications**: Alert and notification system
- **WebSocket**: Real-time communication messages
- **API**: REST API request/response structures

## File Structure

```
types/
├── index.ts           # Main exports
├── trading.ts         # Trading-related interfaces
├── system.ts          # System and agent interfaces
├── notifications.ts   # Notification interfaces
├── websocket.ts       # WebSocket message types
└── api.ts            # API request/response types

schemas/
├── index.ts           # Main validation exports
├── trading.ts         # Trading data validation
├── system.ts          # System data validation
└── notifications.ts   # Notification validation

utils/
├── index.ts           # Main utility exports
├── formatters.ts      # Data formatting functions
├── calculations.ts    # Financial calculations
└── constants.ts       # Application constants
```

## Key Interfaces

### Trading Types

#### PerformanceMetrics
Represents real-time trading performance data:
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
  lastUpdate: Date;
}
```

#### TradeLogEntry
Individual trade record:
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
  duration?: number;
  fees?: number;
}
```

#### TradingSignal
AI-generated trading signals:
```typescript
interface TradingSignal {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  confidence: number;
  pattern: string;
  timestamp: Date;
  price: number;
  reasoning?: string;
}
```

### System Types

#### SystemHealth
System performance and health metrics:
```typescript
interface SystemHealth {
  cpu: number;
  memory: number;
  diskUsage: number;
  networkLatency: number;
  errorRate: number;
  uptime: number;
  connections: ConnectionStatus;
  lastUpdate: Date;
}
```

#### AgentStatus
Trading agent status and statistics:
```typescript
interface AgentStatus {
  state: 'running' | 'paused' | 'stopped' | 'error' | 'starting' | 'stopping';
  uptime: number;
  lastAction: Date;
  activePositions: number;
  dailyTrades: number;
  version: string;
  configHash?: string;
}
```

#### AgentConfig
Trading agent configuration:
```typescript
interface AgentConfig {
  symbols: string[];
  timeframes: Timeframe[];
  riskLimits: RiskLimits;
  tradingHours: TradingHours;
  llmConfig: LLMConfig;
  enabled: boolean;
}
```

### Notification Types

#### Notification
Base notification structure:
```typescript
interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent: boolean;
  priority: NotificationPriority;
  category: NotificationCategory;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
  expiresAt?: Date;
}
```

## Validation Schemas

All data structures have corresponding Zod validation schemas that provide:

- Runtime type checking
- Data sanitization
- Error reporting
- Type inference

### Usage Example

```typescript
import { validatePerformanceMetrics } from '../schemas';

const data = {
  totalPnl: 1500.50,
  dailyPnl: 250.75,
  winRate: 65.5,
  // ... other fields
};

const result = validatePerformanceMetrics(data);
if (result.success) {
  // Data is valid, use result.data
  console.log('Valid metrics:', result.data);
} else {
  // Handle validation errors
  console.error('Validation errors:', result.error.issues);
}
```

## Utility Functions

### Formatters

The `formatters.ts` file provides functions for displaying data in user-friendly formats:

- `formatCurrency()` - Format monetary values
- `formatPercentage()` - Format percentage values
- `formatDate()` - Format dates and times
- `formatPnL()` - Format P&L with color indicators
- `formatSymbol()` - Format trading symbols (e.g., "BTCUSDT" → "BTC/USDT")

### Calculations

The `calculations.ts` file provides financial and trading calculations:

- `calculatePnL()` - Calculate profit/loss
- `calculateWinRate()` - Calculate win rate percentage
- `calculateMaxDrawdown()` - Calculate maximum drawdown
- `calculatePositionSize()` - Calculate position size based on risk
- `calculateSMA()` - Simple moving average
- `calculateRSI()` - Relative Strength Index

### Constants

The `constants.ts` file contains application-wide constants:

- Trading limits and defaults
- System thresholds
- UI configuration
- API settings
- Chart colors and settings

## WebSocket Messages

Real-time communication uses typed WebSocket messages:

```typescript
// Trading updates
interface TradingUpdate extends WebSocketMessage {
  type: 'TRADE_OPENED' | 'TRADE_CLOSED' | 'TRADE_UPDATED' | 'POSITION_UPDATE' | 'PNL_UPDATE';
  data: TradeLogEntry | PerformanceMetrics | Position;
}

// System updates
interface SystemUpdate extends WebSocketMessage {
  type: 'METRICS_UPDATE' | 'HEALTH_CHECK' | 'ERROR_ALERT' | 'CONNECTION_STATUS';
  data: SystemHealth | Notification;
}

// Agent updates
interface AgentUpdate extends WebSocketMessage {
  type: 'STATUS_CHANGE' | 'CONFIG_UPDATE' | 'AGENT_ERROR' | 'AGENT_LOG';
  data: AgentStatus | AgentConfig | { level: string; message: string };
}
```

## API Types

REST API communication uses structured request/response types:

```typescript
// Base response structure
interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  timestamp: Date;
  requestId?: string;
}

// Paginated responses
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
  totalPages: number;
}
```

## Best Practices

1. **Type Safety**: Always use TypeScript interfaces for data structures
2. **Validation**: Validate all external data using Zod schemas
3. **Immutability**: Treat all data as immutable
4. **Error Handling**: Use the `ApiResponse` structure for consistent error handling
5. **Documentation**: Document complex types with JSDoc comments
6. **Naming**: Use descriptive names that clearly indicate the data's purpose

## Integration with Backend

The types are designed to match the Python backend data structures:

- `PerformanceMetrics` matches the monitoring system output
- `TradeLogEntry` matches the trade database schema
- `SystemHealth` matches the system monitoring metrics
- `AgentStatus` matches the agent state management

This ensures seamless data flow between the frontend and backend systems.