# Requirements Document

## Introduction

The Autonomous Trading System is a multi-LLM powered trading agent that analyzes multiple timeframes, evaluates technical signals, manages risk, and executes trades autonomously. The system integrates multiple language models through a router for optimal accuracy and cost-effectiveness, implements self-learning memory to adapt strategies based on performance, and provides comprehensive debug/repair/self-recovery capabilities for reliable 24/7 operation.

## Requirements

### Requirement 1

**User Story:** As a trader, I want the system to analyze multiple timeframes (15m, 1h, 4h, 1d) with technical indicators and patterns, so that I can capture trading opportunities across different time horizons.

#### Acceptance Criteria

1. WHEN the system performs market analysis THEN it SHALL evaluate 15-minute, 1-hour, 4-hour, and daily timeframes
2. WHEN analyzing each timeframe THEN the system SHALL compute at least 10 technical indicators including RSI, EMA(20/50/200), MACD, Bollinger Bands, ATR, Volume Profile, Stochastics, CCI, and MFI
3. WHEN pattern recognition runs THEN the system SHALL detect support/resistance levels, breakouts, divergences, and candlestick patterns (Pin Bar, Engulfing, Doji)
4. WHEN multiple timeframes are analyzed THEN the system SHALL generate a unified confluence score on a 0-100 scale with reasoning

### Requirement 2

**User Story:** As a trader, I want the system to use multiple LLMs through a smart router, so that I can get the best accuracy and cost-effectiveness without fine-tuning models.

#### Acceptance Criteria

1. WHEN the system needs LLM analysis THEN it SHALL route requests through a pool of at least 5 models (Claude, Gemini, GPT-4 Turbo, Mixtral, Llama)
2. WHEN routing decisions are made THEN the system SHALL support configurable policies (AccuracyFirst, CostAware, LatencyAware)
3. WHEN LLM calls are made THEN the system SHALL log prompt, completion, token cost, and latency for evaluation
4. WHEN an LLM fails THEN the system SHALL automatically fallback to alternative models
5. WHEN prompts are generated THEN they SHALL adapt dynamically to market regime (Bull/Bear/Sideways) and timeframe

### Requirement 3

**User Story:** As a trader, I want the system to learn from its trading performance and adapt strategies, so that it can improve over time without manual intervention.

#### Acceptance Criteria

1. WHEN trades are completed THEN the system SHALL track pattern_id → win_rate, expectancy, avg_R, and holding_time
2. WHEN strategy adaptation occurs THEN the system SHALL use multi-armed bandit algorithms (ε-greedy/UCB) to adjust pattern weights
3. WHEN position sizing is calculated THEN the system SHALL scale risk per trade based on recent accuracy within bounded caps
4. WHEN performance data is available THEN the system SHALL maintain rolling windows of 30-90 days for calibration

### Requirement 4

**User Story:** As a trader, I want comprehensive risk management controls, so that I can protect my capital from excessive losses.

#### Acceptance Criteria

1. WHEN calculating position size THEN the system SHALL limit risk to 0.25-2% per trade with portfolio cap at 20%
2. WHEN leverage is applied THEN the system SHALL enforce maximum 10x leverage with default ≤3x
3. WHEN drawdown occurs THEN the system SHALL trigger SAFE_MODE at 8% daily or 20% monthly drawdown thresholds
4. WHEN in SAFE_MODE THEN the system SHALL block new entries, tighten stops, and implement cool-down periods
5. WHEN managing stops THEN the system SHALL use ATR-based, breakeven, and trailing stop mechanisms
6. WHEN evaluating positions THEN the system SHALL check correlations and block correlated exposures

### Requirement 5

**User Story:** As a trader, I want the system to execute orders safely and reliably, so that I can trust it to operate autonomously without duplicate or stuck orders.

#### Acceptance Criteria

1. WHEN placing orders THEN the system SHALL use idempotent order IDs to prevent duplicates
2. WHEN order execution fails THEN the system SHALL implement retry logic with exponential backoff
3. WHEN API failures occur THEN the system SHALL use circuit breakers to prevent cascading failures
4. WHEN orders are submitted THEN the system SHALL support multiple exchange adapters
5. WHEN position lifecycle management occurs THEN the system SHALL handle Open → Monitor → Adjust → Close with logged reasons

### Requirement 6

**User Story:** As a trader, I want complete audit trails and debugging capabilities, so that I can understand every decision and recover from failures.

#### Acceptance Criteria

1. WHEN any decision is made THEN the system SHALL log every reasoning step with market snapshot
2. WHEN data is persisted THEN the system SHALL use both JSON journal and DB schema for queries
3. WHEN incidents occur THEN the system SHALL classify them as Data, Risk, Exec, or LLM failures
4. WHEN auto-repair is needed THEN the system SHALL reset adapters, rotate keys, switch models, or rollback builds
5. WHEN structured logs are generated THEN they SHALL support replay functionality for debugging

### Requirement 7

**User Story:** As a trader, I want real-time monitoring and metrics, so that I can track system performance and make informed decisions.

#### Acceptance Criteria

1. WHEN the system operates THEN it SHALL provide real-time metrics including Win Rate, P&L, Sharpe Ratio, MAR, HitRate per Pattern, and Cost per Trade
2. WHEN performance is measured THEN the system SHALL maintain ≥99.5% orchestrator uptime
3. WHEN latency is measured THEN the system SHALL achieve <1.0s per timeframe scan (excluding LLM) and LLM call p95 ≤ 3s
4. WHEN error budget is tracked THEN the system SHALL maintain <0.5% of scan cycles unrecovered

### Requirement 8

**User Story:** As a trader, I want the system to operate continuously with self-recovery, so that it can trade 24/7 without manual intervention.

#### Acceptance Criteria

1. WHEN the system runs THEN it SHALL operate continuously 24/7 with automatic recovery from API failures
2. WHEN failures are detected THEN the system SHALL implement watchdog functionality with auto-restart capabilities
3. WHEN configuration changes occur THEN the system SHALL support hot reload without downtime
4. WHEN check intervals are determined THEN the system SHALL adapt between 15m-4h based on market conditions
5. WHEN market regime changes THEN the system SHALL automatically adjust timeframe weighting based on volatility

### Requirement 9

**User Story:** As a trader, I want secure handling of credentials and compliance features, so that I can meet regulatory requirements and protect sensitive data.

#### Acceptance Criteria

1. WHEN secrets are managed THEN the system SHALL store them in Vault/ENV and never log them
2. WHEN audit trails are created THEN they SHALL be tamper-evident with hash-chain verification
3. WHEN access control is needed THEN the system SHALL implement RBAC with signed configurations
4. WHEN compliance is required THEN the system SHALL provide configurable audit trails per jurisdiction
5. WHEN cost optimization occurs THEN the system SHALL use token-optimized prompts and cost-aware routing