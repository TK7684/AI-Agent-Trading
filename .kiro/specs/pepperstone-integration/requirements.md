# Requirements Document

## Introduction

The Pepperstone Integration feature enables the autonomous trading system to connect with Pepperstone broker for Forex and CFD trading operations. This integration provides secure API connectivity through cTrader Open API or MetaTrader 5 bridge, real-time market data streaming, order execution, and account management capabilities. The system will support both approaches with proper authentication, rate limiting, and error handling to ensure reliable 24/7 operation across multiple asset classes including FX pairs, indices, commodities, and cryptocurrencies.

## Requirements

### Requirement 1

**User Story:** As a trader, I want secure API authentication with Pepperstone, so that I can safely connect my trading account through cTrader or MT5 without exposing credentials.

#### Acceptance Criteria

1. WHEN using cTrader Open API THEN the system SHALL implement OAuth2 authentication flow with Client ID and Secret
2. WHEN using MT5 bridge THEN the system SHALL securely connect to local MT5 terminal with proper account validation
3. WHEN credentials are configured THEN the system SHALL store OAuth tokens or MT5 connection details securely using environment variables
4. WHEN authentication fails THEN the system SHALL log errors securely without exposing sensitive credentials
5. WHEN API permissions are validated THEN the system SHALL verify trading permissions for FX, CFDs, and other instruments

### Requirement 2

**User Story:** As a trader, I want real-time market data from Pepperstone, so that my trading decisions are based on current FX and CFD market conditions.

#### Acceptance Criteria

1. WHEN market data is requested THEN the system SHALL connect to cTrader streaming API or MT5 data feeds for real-time price updates
2. WHEN subscribing to data THEN the system SHALL support tick data, bid/ask spreads, and candlestick data for multiple timeframes
3. WHEN market data is received THEN the system SHALL handle FX pairs (EURUSD, GBPUSD, etc.), indices (US30, SPX500), commodities (XAUUSD, XTIUSD), and crypto CFDs
4. WHEN connection drops THEN the system SHALL automatically reconnect with exponential backoff and maintain data continuity
5. WHEN data quality issues occur THEN the system SHALL detect stale prices and trigger reconnection if no updates received for 10 seconds

### Requirement 3

**User Story:** As a trader, I want to execute FX and CFD orders on Pepperstone, so that I can trade multiple asset classes with proper leverage and margin management.

#### Acceptance Criteria

1. WHEN placing FX orders THEN the system SHALL support Market, Limit, Stop, and Stop-Limit order types with proper lot sizing
2. WHEN placing CFD orders THEN the system SHALL handle different contract sizes and margin requirements per instrument type
3. WHEN orders are submitted THEN the system SHALL include unique order identifiers for tracking and idempotency
4. WHEN order status changes THEN the system SHALL track order lifecycle (Pending, Filled, Partially Filled, Cancelled, Rejected)
5. WHEN leverage is applied THEN the system SHALL manage margin requirements and available margin per instrument class

### Requirement 4

**User Story:** As a trader, I want proper rate limiting and connection management, so that my requests don't overwhelm the cTrader API or MT5 terminal.

#### Acceptance Criteria

1. WHEN using cTrader API THEN the system SHALL respect API rate limits and implement request queuing
2. WHEN using MT5 bridge THEN the system SHALL limit polling frequency to prevent terminal overload (max 4 requests/second)
3. WHEN rate limits are approached THEN the system SHALL implement backoff strategies and prioritize critical operations
4. WHEN connection issues occur THEN the system SHALL implement circuit breakers and graceful degradation
5. WHEN multiple requests are needed THEN the system SHALL batch compatible operations to optimize performance

### Requirement 5

**User Story:** As a trader, I want account and position management for FX and CFDs, so that I can track my balances, positions, and margin usage across different instrument types.

#### Acceptance Criteria

1. WHEN account info is requested THEN the system SHALL retrieve account balance, equity, margin used, and free margin
2. WHEN positions are queried THEN the system SHALL get current positions with unrealized P&L, swap costs, and margin per position
3. WHEN trade history is needed THEN the system SHALL fetch recent trades, order history, and transaction records
4. WHEN margin is calculated THEN the system SHALL check available margin before placing orders, considering instrument-specific requirements
5. WHEN account updates occur THEN the system SHALL receive real-time balance and position updates through streaming APIs

### Requirement 6

**User Story:** As a trader, I want comprehensive error handling for Pepperstone API issues, so that temporary problems don't crash my FX/CFD trading system.

#### Acceptance Criteria

1. WHEN API errors occur THEN the system SHALL categorize errors (Network, Authentication, Insufficient Margin, Invalid Symbol, Market Closed)
2. WHEN recoverable errors happen THEN the system SHALL implement automatic retry with exponential backoff (max 3 retries for trading operations)
3. WHEN critical errors occur THEN the system SHALL trigger circuit breakers and notify operators immediately
4. WHEN market hours end THEN the system SHALL detect trading session closures and pause operations gracefully
5. WHEN connection issues arise THEN the system SHALL attempt reconnection while maintaining order state consistency

### Requirement 7

**User Story:** As a trader, I want instrument and market information management, so that I can trade valid FX pairs and CFDs with correct contract specifications.

#### Acceptance Criteria

1. WHEN system starts THEN it SHALL fetch and cache current trading instruments, contract sizes, pip values, and margin requirements
2. WHEN order parameters are validated THEN the system SHALL check minimum lot size, maximum position size, and trading hours
3. WHEN new instruments are available THEN the system SHALL automatically update instrument information daily
4. WHEN trading rules change THEN the system SHALL detect and apply new specifications without manual intervention
5. WHEN market sessions change THEN the system SHALL handle different trading hours for FX, indices, commodities, and crypto CFDs

### Requirement 8

**User Story:** As a trader, I want demo account support for safe development, so that I can test integrations without risking real funds.

#### Acceptance Criteria

1. WHEN development mode is enabled THEN the system SHALL connect to cTrader demo accounts or MT5 demo servers
2. WHEN switching environments THEN the system SHALL use separate credentials for demo vs live accounts
3. WHEN demo trading occurs THEN the system SHALL clearly mark all operations as demo mode in logs and UI
4. WHEN testing is complete THEN the system SHALL provide easy configuration switch to live trading mode
5. WHEN demo limitations exist THEN the system SHALL handle reduced instrument availability and simulated execution

### Requirement 9

**User Story:** As a trader, I want monitoring and logging of Pepperstone operations, so that I can track API usage and troubleshoot FX/CFD trading issues.

#### Acceptance Criteria

1. WHEN API calls are made THEN the system SHALL log request/response details with timestamps and latency
2. WHEN monitoring metrics are collected THEN the system SHALL track API success rate, execution quality, and slippage
3. WHEN performance issues occur THEN the system SHALL alert on high latency (>500ms), error rates (>3%), or connection failures
4. WHEN audit trails are created THEN the system SHALL maintain detailed logs of all trading operations for regulatory compliance
5. WHEN system health is checked THEN the system SHALL provide connection status, last successful operation, and margin utilization

### Requirement 10

**User Story:** As a trader, I want unified broker abstraction, so that I can switch between Binance and Pepperstone without changing my core trading logic.

#### Acceptance Criteria

1. WHEN implementing broker interfaces THEN the system SHALL provide unified methods for account info, order placement, and position management
2. WHEN symbol mapping is needed THEN the system SHALL translate internal symbols to broker-specific formats (BTCUSDT vs XBTUSD)
3. WHEN order types differ THEN the system SHALL map common order types to broker-specific implementations
4. WHEN position sizing varies THEN the system SHALL handle different lot sizes, contract sizes, and minimum trade amounts
5. WHEN switching brokers THEN the system SHALL maintain consistent risk management and position tracking across platforms
</content>
</file></function_results>

<function_calls>
<invoke name="fsWrite">
<parameter name="path">.kiro/specs/pepperstone-integration/design.mdign Document