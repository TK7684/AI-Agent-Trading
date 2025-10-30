"""
Live Trading Configuration and Data Models

This module defines the core data structures and configuration models
for the live trading execution system, including trading modes, validation
results, emergency triggers, and performance metrics.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional


class TradingMode(str, Enum):
    """Trading mode enumeration."""
    PAPER = "paper"
    LIVE_MINIMAL = "live_minimal"
    LIVE_SCALED = "live_scaled"
    EMERGENCY_STOP = "emergency_stop"


class EmergencyAction(str, Enum):
    """Emergency action types."""
    HALT_NEW_TRADES = "halt_new_trades"
    CLOSE_ALL_POSITIONS = "close_all_positions"
    CLOSE_CORRELATED = "close_correlated"
    PAUSE_TRADING = "pause_trading"
    IMMEDIATE_STOP = "immediate_stop"
    REDUCE_POSITION_SIZES = "reduce_position_sizes"


@dataclass
class EmergencyTrigger:
    """Configuration for emergency circuit breaker triggers."""
    condition: str  # "drawdown_exceeded", "api_failure", "manual_stop", etc.
    threshold: float
    action: EmergencyAction
    cooldown_hours: int
    enabled: bool = True
    description: str = ""

    def __post_init__(self):
        if self.threshold < 0:
            raise ValueError("Threshold must be non-negative")
        if self.cooldown_hours < 0:
            raise ValueError("Cooldown hours must be non-negative")


@dataclass
class PerformanceThresholds:
    """Performance thresholds for validation and scaling."""
    min_win_rate: float = 0.45  # 45%
    min_sharpe_ratio: float = 0.5
    max_drawdown: float = 0.15  # 15%
    min_profit_factor: float = 1.2
    min_trades: int = 10
    min_days_profitable: int = 7

    def __post_init__(self):
        if not (0 <= self.min_win_rate <= 1):
            raise ValueError("Win rate must be between 0 and 1")
        if self.max_drawdown < 0:
            raise ValueError("Max drawdown must be non-negative")
        if self.min_profit_factor <= 0:
            raise ValueError("Profit factor must be positive")


@dataclass
class RiskLimits:
    """Risk management limits for different trading phases."""
    max_risk_per_trade: float
    max_portfolio_exposure: float
    daily_loss_limit: float
    max_correlation: float = 0.7
    max_leverage: float = 3.0
    position_timeout_hours: int = 24

    def __post_init__(self):
        if not (0 < self.max_risk_per_trade <= 0.1):  # Max 10% per trade
            raise ValueError("Risk per trade must be between 0 and 0.1 (10%)")
        if not (0 < self.max_portfolio_exposure <= 1.0):
            raise ValueError("Portfolio exposure must be between 0 and 1.0 (100%)")
        if self.daily_loss_limit <= 0:
            raise ValueError("Daily loss limit must be positive")


@dataclass
class LiveTradingConfig:
    """Main configuration for live trading operations."""
    mode: TradingMode
    risk_limits: RiskLimits
    allowed_symbols: list[str]
    performance_thresholds: PerformanceThresholds
    emergency_triggers: list[EmergencyTrigger]

    # Optional settings
    scaling_enabled: bool = True
    auto_scaling: bool = False
    notification_enabled: bool = True
    audit_enabled: bool = True

    # API and exchange settings
    exchange: str = "binance"
    testnet: bool = True
    api_timeout_seconds: int = 10
    max_api_retries: int = 3

    # Monitoring settings
    monitoring_interval_seconds: int = 30
    performance_update_interval_minutes: int = 15

    def __post_init__(self):
        if not self.allowed_symbols:
            raise ValueError("At least one symbol must be allowed")
        if self.api_timeout_seconds <= 0:
            raise ValueError("API timeout must be positive")
        if self.monitoring_interval_seconds <= 0:
            raise ValueError("Monitoring interval must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "mode": self.mode.value,
            "risk_limits": {
                "max_risk_per_trade": self.risk_limits.max_risk_per_trade,
                "max_portfolio_exposure": self.risk_limits.max_portfolio_exposure,
                "daily_loss_limit": self.risk_limits.daily_loss_limit,
                "max_correlation": self.risk_limits.max_correlation,
                "max_leverage": self.risk_limits.max_leverage,
                "position_timeout_hours": self.risk_limits.position_timeout_hours
            },
            "allowed_symbols": self.allowed_symbols,
            "performance_thresholds": {
                "min_win_rate": self.performance_thresholds.min_win_rate,
                "min_sharpe_ratio": self.performance_thresholds.min_sharpe_ratio,
                "max_drawdown": self.performance_thresholds.max_drawdown,
                "min_profit_factor": self.performance_thresholds.min_profit_factor,
                "min_trades": self.performance_thresholds.min_trades,
                "min_days_profitable": self.performance_thresholds.min_days_profitable
            },
            "emergency_triggers": [
                {
                    "condition": trigger.condition,
                    "threshold": trigger.threshold,
                    "action": trigger.action.value,
                    "cooldown_hours": trigger.cooldown_hours,
                    "enabled": trigger.enabled,
                    "description": trigger.description
                }
                for trigger in self.emergency_triggers
            ],
            "scaling_enabled": self.scaling_enabled,
            "auto_scaling": self.auto_scaling,
            "notification_enabled": self.notification_enabled,
            "audit_enabled": self.audit_enabled,
            "exchange": self.exchange,
            "testnet": self.testnet,
            "api_timeout_seconds": self.api_timeout_seconds,
            "max_api_retries": self.max_api_retries,
            "monitoring_interval_seconds": self.monitoring_interval_seconds,
            "performance_update_interval_minutes": self.performance_update_interval_minutes
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LiveTradingConfig':
        """Create configuration from dictionary."""
        risk_limits = RiskLimits(**data["risk_limits"])
        performance_thresholds = PerformanceThresholds(**data["performance_thresholds"])

        emergency_triggers = [
            EmergencyTrigger(
                condition=trigger["condition"],
                threshold=trigger["threshold"],
                action=EmergencyAction(trigger["action"]),
                cooldown_hours=trigger["cooldown_hours"],
                enabled=trigger.get("enabled", True),
                description=trigger.get("description", "")
            )
            for trigger in data["emergency_triggers"]
        ]

        return cls(
            mode=TradingMode(data["mode"]),
            risk_limits=risk_limits,
            allowed_symbols=data["allowed_symbols"],
            performance_thresholds=performance_thresholds,
            emergency_triggers=emergency_triggers,
            scaling_enabled=data.get("scaling_enabled", True),
            auto_scaling=data.get("auto_scaling", False),
            notification_enabled=data.get("notification_enabled", True),
            audit_enabled=data.get("audit_enabled", True),
            exchange=data.get("exchange", "binance"),
            testnet=data.get("testnet", True),
            api_timeout_seconds=data.get("api_timeout_seconds", 10),
            max_api_retries=data.get("max_api_retries", 3),
            monitoring_interval_seconds=data.get("monitoring_interval_seconds", 30),
            performance_update_interval_minutes=data.get("performance_update_interval_minutes", 15)
        )


@dataclass
class ValidationIssue:
    """Represents a validation issue found during paper trading."""
    severity: str  # "error", "warning", "info"
    category: str  # "performance", "system", "risk", "data"
    message: str
    timestamp: datetime
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for trading validation."""
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: timedelta
    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        if self.total_trades != self.winning_trades + self.losing_trades:
            raise ValueError("Total trades must equal winning + losing trades")
        if self.total_trades > 0 and not (0 <= self.win_rate <= 1):
            raise ValueError("Win rate must be between 0 and 1")


@dataclass
class ValidationResult:
    """Result of paper trading validation."""
    passed: bool
    performance: PerformanceMetrics
    validation_period: timedelta
    issues: list[ValidationIssue]
    timestamp: datetime

    # Detailed validation results
    win_rate_passed: bool
    sharpe_ratio_passed: bool
    drawdown_passed: bool
    profit_factor_passed: bool
    min_trades_passed: bool

    def get_summary(self) -> dict[str, Any]:
        """Get validation summary."""
        return {
            "passed": self.passed,
            "validation_period_days": self.validation_period.days,
            "performance": {
                "win_rate": self.performance.win_rate,
                "sharpe_ratio": self.performance.sharpe_ratio,
                "max_drawdown": self.performance.max_drawdown,
                "profit_factor": self.performance.profit_factor,
                "total_trades": self.performance.total_trades,
                "total_pnl": self.performance.total_pnl
            },
            "validation_checks": {
                "win_rate_passed": self.win_rate_passed,
                "sharpe_ratio_passed": self.sharpe_ratio_passed,
                "drawdown_passed": self.drawdown_passed,
                "profit_factor_passed": self.profit_factor_passed,
                "min_trades_passed": self.min_trades_passed
            },
            "issues_count": len(self.issues),
            "error_count": len([i for i in self.issues if i.severity == "error"]),
            "warning_count": len([i for i in self.issues if i.severity == "warning"])
        }


@dataclass
class ScalingValidation:
    """Validation result for risk scaling decisions."""
    can_scale: bool
    current_performance: PerformanceMetrics
    required_thresholds: PerformanceThresholds
    days_since_last_scale: int
    risk_concentration: float
    market_volatility: float
    blocking_reasons: list[str] = field(default_factory=list)

    def get_next_risk_level(self, current_risk: float, scaling_factor: float = 1.5) -> float:
        """Calculate next risk level if scaling is allowed."""
        if not self.can_scale:
            return current_risk
        return min(current_risk * scaling_factor, 0.01)  # Cap at 1%


@dataclass
class EmergencyResponse:
    """Response from emergency circuit breaker activation."""
    trigger_reason: str
    trigger_condition: str
    actions_taken: list[str]
    positions_closed: list[str]
    cooldown_until: datetime
    recovery_steps: list[str]
    timestamp: datetime

    def is_in_cooldown(self) -> bool:
        """Check if still in cooldown period."""
        return datetime.now(UTC) < self.cooldown_until


@dataclass
class TradingStatus:
    """Current status of live trading system."""
    mode: TradingMode
    is_active: bool
    current_positions: int
    total_exposure: float
    daily_pnl: float
    unrealized_pnl: float
    last_trade_time: Optional[datetime]
    emergency_active: bool
    cooldown_until: Optional[datetime]
    system_health: str  # "healthy", "warning", "error"
    last_update: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert status to dictionary."""
        return {
            "mode": self.mode.value,
            "is_active": self.is_active,
            "current_positions": self.current_positions,
            "total_exposure": self.total_exposure,
            "daily_pnl": self.daily_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "emergency_active": self.emergency_active,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "system_health": self.system_health,
            "last_update": self.last_update.isoformat()
        }


# Predefined configurations for different trading phases
DEFAULT_EMERGENCY_TRIGGERS = [
    EmergencyTrigger(
        condition="daily_loss_exceeded",
        threshold=0.01,  # 1%
        action=EmergencyAction.HALT_NEW_TRADES,
        cooldown_hours=4,
        description="Daily loss limit exceeded"
    ),
    EmergencyTrigger(
        condition="drawdown_exceeded",
        threshold=0.03,  # 3%
        action=EmergencyAction.CLOSE_ALL_POSITIONS,
        cooldown_hours=24,
        description="Maximum drawdown exceeded"
    ),
    EmergencyTrigger(
        condition="api_latency_high",
        threshold=2.0,  # 2 seconds
        action=EmergencyAction.PAUSE_TRADING,
        cooldown_hours=1,
        description="API latency too high"
    ),
    EmergencyTrigger(
        condition="correlation_breach",
        threshold=0.7,  # 70%
        action=EmergencyAction.CLOSE_CORRELATED,
        cooldown_hours=2,
        description="Position correlation too high"
    ),
    EmergencyTrigger(
        condition="manual_override",
        threshold=0.0,
        action=EmergencyAction.IMMEDIATE_STOP,
        cooldown_hours=0,
        description="Manual emergency stop"
    )
]


def create_paper_trading_config() -> LiveTradingConfig:
    """Create configuration for paper trading phase."""
    return LiveTradingConfig(
        mode=TradingMode.PAPER,
        risk_limits=RiskLimits(
            max_risk_per_trade=0.005,  # 0.5% for paper trading
            max_portfolio_exposure=0.20,  # 20% for testing
            daily_loss_limit=0.05  # 5% daily loss limit
        ),
        allowed_symbols=["BTCUSDT", "ETHUSDT"],
        performance_thresholds=PerformanceThresholds(),
        emergency_triggers=DEFAULT_EMERGENCY_TRIGGERS.copy(),
        testnet=True
    )


def create_live_minimal_config() -> LiveTradingConfig:
    """Create configuration for minimal live trading phase."""
    return LiveTradingConfig(
        mode=TradingMode.LIVE_MINIMAL,
        risk_limits=RiskLimits(
            max_risk_per_trade=0.001,  # 0.1%
            max_portfolio_exposure=0.02,  # 2%
            daily_loss_limit=0.01  # 1%
        ),
        allowed_symbols=["BTCUSDT"],
        performance_thresholds=PerformanceThresholds(),
        emergency_triggers=DEFAULT_EMERGENCY_TRIGGERS.copy(),
        testnet=False,
        auto_scaling=False
    )


def create_live_scaled_config() -> LiveTradingConfig:
    """Create configuration for scaled live trading phase."""
    return LiveTradingConfig(
        mode=TradingMode.LIVE_SCALED,
        risk_limits=RiskLimits(
            max_risk_per_trade=0.005,  # 0.5%
            max_portfolio_exposure=0.10,  # 10%
            daily_loss_limit=0.02  # 2%
        ),
        allowed_symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        performance_thresholds=PerformanceThresholds(),
        emergency_triggers=DEFAULT_EMERGENCY_TRIGGERS.copy(),
        testnet=False,
        auto_scaling=True
    )
