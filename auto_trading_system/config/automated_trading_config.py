"""
Automated Trading Configuration
Configuration settings for the comprehensive automated trading system with
database integration, adaptive learning, and real-time monitoring.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TradingConfig:
    """Trading-specific configuration settings"""

    # General trading settings
    symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    account_balance: float = 10000.0
    max_concurrent_positions: int = 10
    max_position_size: float = 1.0

    # Risk management
    max_risk_per_trade: float = 0.02  # 2% of account per trade
    max_drawdown_pct: float = 10.0  # Maximum drawdown percentage
    min_confidence: float = 0.6  # Minimum confidence to execute trade
    stop_loss_distance_pct: float = 0.02  # 2% stop loss
    take_profit_distance_pct: float = 0.04  # 4% take profit

    # Performance targets
    min_win_rate: float = 65.0  # Target win rate percentage
    min_profit_factor: float = 1.5  # Target profit factor
    target_daily_return: float = 0.01  # 1% daily return target

    # Trading schedule
    trading_hours_enabled: bool = True
    trading_start_hour: int = 0  # UTC hour
    trading_end_hour: int = 23  # UTC hour
    avoid_weekends: bool = True

    # Position management
    position_timeout_hours: int = 24  # Maximum hours to hold position
    profit_protection_enabled: bool = True
    trailing_stop_enabled: bool = True

    # Correlation risk
    max_correlation_exposure: float = 0.3  # Max exposure to correlated assets
    correlation_threshold: float = 0.8  # Correlation coefficient threshold


@dataclass
class DatabaseConfig:
    """Database configuration settings"""

    # Connection settings
    host: str = "localhost"
    port: int = 5432
    database: str = "trading_db"
    username: str = "trading_user"
    password: str = "trading_pass"

    # Connection pool settings
    max_connections: int = 20
    min_connections: int = 5
    connection_timeout: int = 30

    # Performance settings
    query_timeout: int = 60
    batch_size: int = 1000
    enable_connection_pooling: bool = True

    # Backup and retention
    backup_enabled: bool = True
    backup_interval_hours: int = 6
    data_retention_days: int = 90
    archive_old_data: bool = True

    # Redis settings for caching
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl_seconds: int = 3600


@dataclass
class LearningConfig:
    """Machine learning and adaptive learning settings"""

    # Learning cycle settings
    cycle_interval_trades: int = 50  # Learning cycle every N trades
    cycle_interval_hours: int = 4  # Maximum hours between cycles
    min_sample_size: int = 20  # Minimum trades for learning

    # Adaptation settings
    adaptation_threshold: float = 0.05  # 5% performance drop triggers adaptation
    max_adaptation_frequency: int = 3600  # Max once per hour (seconds)
    parameter_adjustment_rate: float = 0.1  # Rate of parameter changes

    # Strategy optimization
    optimization_enabled: bool = True
    optimization_interval_hours: int = 24
    strategy_selection_method: str = "adaptive"  # adaptive, static, ml_based

    # Pattern recognition
    pattern_recognition_enabled: bool = True
    pattern_confidence_threshold: float = 0.7
    max_pattern_age_days: int = 30

    # Multi-armed bandit settings
    epsilon_greedy_epsilon: float = 0.1  # Exploration rate
    ucb_confidence_level: float = 2.0  # UCB1 confidence parameter
    bandit_algorithm: str = "ucb1"  # epsilon_greedy, ucb1, thompson_sampling

    # Model settings
    ml_model_retrain_interval: int = 168  # Hours between retraining (1 week)
    feature_importance_threshold: float = 0.05
    cross_validation_folds: int = 5


@dataclass
class MonitoringConfig:
    """Performance monitoring and alerting settings"""

    # Metrics collection
    collection_interval_seconds: int = 30
    history_size: int = 1000
    save_to_database_interval: int = 5  # Every N collections

    # System alert thresholds
    cpu_threshold: float = 80.0  # Percentage
    memory_threshold: float = 85.0  # Percentage
    disk_threshold: float = 90.0  # Percentage
    network_latency_threshold: float = 1000.0  # Milliseconds

    # Trading alert thresholds
    drawdown_alert_threshold: float = 8.0  # Percentage
    win_rate_alert_threshold: float = 45.0  # Percentage
    consecutive_losses_alert: int = 5
    error_rate_threshold: float = 5.0  # Percentage

    # Alert settings
    alert_enabled: bool = True
    email_alerts_enabled: bool = False
    webhook_alerts_enabled: bool = False
    alert_cooldown_minutes: int = 30  # Min time between same alerts

    # Performance reporting
    daily_report_enabled: bool = True
    weekly_report_enabled: bool = True
    report_recipients: List[str] = field(default_factory=list)

    # Dashboard settings
    dashboard_enabled: bool = True
    dashboard_port: int = 8080
    dashboard_refresh_interval: int = 5  # Seconds


@dataclass
class LLMConfig:
    """Language model integration settings"""

    # Provider settings
    primary_provider: str = "openai"  # openai, google
    fallback_providers: List[str] = field(default_factory=lambda: ["google"])

    # Model settings
    default_model: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 1000

    # API Keys (from environment)
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Model configurations
    openai_model: str = "gpt-4"
    gemini_model: str = "gemini-1.5-pro"

    # Caching settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_size_limit: int = 1000

    # Performance settings
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 1

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 40000

    # Routing settings
    enable_adaptive_routing: bool = True
    routing_strategy: str = (
        "performance_based"  # performance_based, cost_based, latency_based
    )


@dataclass
class SecurityConfig:
    """Security and encryption settings"""

    # API security
    api_key_encryption_enabled: bool = True
    request_signing_enabled: bool = True
    rate_limiting_enabled: bool = True

    # Data encryption
    database_encryption_enabled: bool = False
    log_encryption_enabled: bool = True
    sensitive_data_masking: bool = True

    # Access control
    ip_whitelist_enabled: bool = False
    allowed_ips: List[str] = field(default_factory=list)
    session_timeout_minutes: int = 30

    # Audit logging
    audit_logging_enabled: bool = True
    log_retention_days: int = 90
    failed_login_threshold: int = 5

    # Trading security
    emergency_stop_enabled: bool = True
    max_daily_loss_pct: float = 5.0  # Emergency stop at 5% daily loss
    manual_approval_required: bool = False


@dataclass
class AutomatedTradingSystemConfig:
    """Main configuration class for the automated trading system"""

    # Component configurations
    trading: TradingConfig = field(default_factory=TradingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # System-wide settings
    environment: str = "production"  # development, staging, production
    debug_mode: bool = False
    log_level: str = "INFO"

    # Performance settings
    max_concurrent_tasks: int = 100
    task_queue_size: int = 1000
    enable_async_operations: bool = True

    # Feature flags
    enable_paper_trading: bool = False
    enable_simulation_mode: bool = False
    enable_backtesting: bool = True
    enable_live_trading: bool = True

    # System limits
    max_memory_usage_mb: int = 2048
    max_cpu_usage_pct: float = 90.0
    max_disk_usage_pct: float = 95.0

    def get_database_url(self) -> str:
        """Get the complete database connection URL"""
        return (
            f"postgresql+asyncpg://{self.database.username}:{self.database.password}"
            f"@{self.database.host}:{self.database.port}/{self.database.database}"
        )

    def get_redis_url(self) -> str:
        """Get the Redis connection URL"""
        return f"redis://{self.database.redis_host}:{self.database.redis_port}/{self.database.redis_db}"

    def is_trading_time(self) -> bool:
        """Check if current time is within allowed trading hours"""
        if not self.trading.trading_hours_enabled:
            return True

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        current_hour = now.hour

        if self.trading.trading_start_hour <= self.trading.trading_end_hour:
            # Same day range (e.g., 9 AM to 5 PM)
            return (
                self.trading.trading_start_hour
                <= current_hour
                <= self.trading.trading_end_hour
            )
        else:
            # Cross midnight range (e.g., 9 PM to 6 AM)
            return (
                current_hour >= self.trading.trading_start_hour
                or current_hour <= self.trading.trading_end_hour
            )

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Trading config validation
        if self.trading.max_risk_per_trade > 0.1:
            errors.append("max_risk_per_trade should not exceed 10% (0.1)")

        if self.trading.max_drawdown_pct > 50:
            errors.append("max_drawdown_pct seems too high (>50%)")

        if self.trading.account_balance <= 0:
            errors.append("account_balance must be positive")

        # Database config validation
        if self.database.max_connections < self.trading.max_concurrent_positions:
            errors.append(
                "Database max_connections should be >= max_concurrent_positions"
            )

        # Learning config validation
        if self.learning.min_sample_size < 10:
            errors.append("min_sample_size should be at least 10 for reliable learning")

        # Monitoring config validation
        if self.monitoring.cpu_threshold > 95:
            errors.append("CPU threshold should be <= 95%")

        if self.monitoring.memory_threshold > 95:
            errors.append("Memory threshold should be <= 95%")

        return errors


# Default configuration instance
DEFAULT_CONFIG = AutomatedTradingSystemConfig()


def get_config() -> AutomatedTradingSystemConfig:
    """Get the default configuration"""
    return DEFAULT_CONFIG


def load_config_from_file(config_path: str) -> AutomatedTradingSystemConfig:
    """Load configuration from a JSON or TOML file"""
    import json
    import os
    from pathlib import Path

    file_path = Path(config_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Determine file format from extension
    if file_path.suffix.lower() == ".json":
        with open(file_path, "r") as f:
            config_data = json.load(f)
    elif file_path.suffix.lower() in [".toml", ".tml"]:
        try:
            import tomllib

            with open(file_path, "rb") as f:
                config_data = tomllib.load(f)
        except ImportError:
            import toml

            with open(file_path, "r") as f:
                config_data = toml.load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")

    # Create config from loaded data
    return AutomatedTradingSystemConfig(
        trading=TradingConfig(**config_data.get("trading", {})),
        database=DatabaseConfig(**config_data.get("database", {})),
        learning=LearningConfig(**config_data.get("learning", {})),
        monitoring=MonitoringConfig(**config_data.get("monitoring", {})),
        llm=LLMConfig(**config_data.get("llm", {})),
        security=SecurityConfig(**config_data.get("security", {})),
        environment=config_data.get("environment", "production"),
        debug_mode=config_data.get("debug_mode", False),
        log_level=config_data.get("log_level", "INFO"),
    )


def save_config_to_file(config: AutomatedTradingSystemConfig, config_path: str) -> None:
    """Save configuration to a JSON file"""
    import json
    from pathlib import Path

    file_path = Path(config_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert config to dictionary
    config_dict = {
        "trading": {
            "symbols": config.trading.symbols,
            "timeframes": config.trading.timeframes,
            "account_balance": config.trading.account_balance,
            "max_concurrent_positions": config.trading.max_concurrent_positions,
            "max_position_size": config.trading.max_position_size,
            "max_risk_per_trade": config.trading.max_risk_per_trade,
            "max_drawdown_pct": config.trading.max_drawdown_pct,
            "min_confidence": config.trading.min_confidence,
            "stop_loss_distance_pct": config.trading.stop_loss_distance_pct,
            "take_profit_distance_pct": config.trading.take_profit_distance_pct,
            "min_win_rate": config.trading.min_win_rate,
            "min_profit_factor": config.trading.min_profit_factor,
            "target_daily_return": config.trading.target_daily_return,
            "trading_hours_enabled": config.trading.trading_hours_enabled,
            "trading_start_hour": config.trading.trading_start_hour,
            "trading_end_hour": config.trading.trading_end_hour,
            "avoid_weekends": config.trading.avoid_weekends,
            "position_timeout_hours": config.trading.position_timeout_hours,
            "profit_protection_enabled": config.trading.profit_protection_enabled,
            "trailing_stop_enabled": config.trading.trailing_stop_enabled,
            "max_correlation_exposure": config.trading.max_correlation_exposure,
            "correlation_threshold": config.trading.correlation_threshold,
        },
        "database": {
            "host": config.database.host,
            "port": config.database.port,
            "database": config.database.database,
            "username": config.database.username,
            "password": config.database.password,
            "max_connections": config.database.max_connections,
            "min_connections": config.database.min_connections,
            "connection_timeout": config.database.connection_timeout,
            "query_timeout": config.database.query_timeout,
            "batch_size": config.database.batch_size,
            "enable_connection_pooling": config.database.enable_connection_pooling,
            "backup_enabled": config.database.backup_enabled,
            "backup_interval_hours": config.database.backup_interval_hours,
            "data_retention_days": config.database.data_retention_days,
            "archive_old_data": config.database.archive_old_data,
            "redis_host": config.database.redis_host,
            "redis_port": config.database.redis_port,
            "redis_db": config.database.redis_db,
            "redis_ttl_seconds": config.database.redis_ttl_seconds,
        },
        "learning": {
            "cycle_interval_trades": config.learning.cycle_interval_trades,
            "cycle_interval_hours": config.learning.cycle_interval_hours,
            "min_sample_size": config.learning.min_sample_size,
            "adaptation_threshold": config.learning.adaptation_threshold,
            "max_adaptation_frequency": config.learning.max_adaptation_frequency,
            "parameter_adjustment_rate": config.learning.parameter_adjustment_rate,
            "optimization_enabled": config.learning.optimization_enabled,
            "optimization_interval_hours": config.learning.optimization_interval_hours,
            "strategy_selection_method": config.learning.strategy_selection_method,
            "pattern_recognition_enabled": config.learning.pattern_recognition_enabled,
            "pattern_confidence_threshold": config.learning.pattern_confidence_threshold,
            "max_pattern_age_days": config.learning.max_pattern_age_days,
            "epsilon_greedy_epsilon": config.learning.epsilon_greedy_epsilon,
            "ucb_confidence_level": config.learning.ucb_confidence_level,
            "bandit_algorithm": config.learning.bandit_algorithm,
            "ml_model_retrain_interval": config.learning.ml_model_retrain_interval,
            "feature_importance_threshold": config.learning.feature_importance_threshold,
            "cross_validation_folds": config.learning.cross_validation_folds,
        },
        "monitoring": {
            "collection_interval_seconds": config.monitoring.collection_interval_seconds,
            "history_size": config.monitoring.history_size,
            "save_to_database_interval": config.monitoring.save_to_database_interval,
            "cpu_threshold": config.monitoring.cpu_threshold,
            "memory_threshold": config.monitoring.memory_threshold,
            "disk_threshold": config.monitoring.disk_threshold,
            "network_latency_threshold": config.monitoring.network_latency_threshold,
            "drawdown_alert_threshold": config.monitoring.drawdown_alert_threshold,
            "win_rate_alert_threshold": config.monitoring.win_rate_alert_threshold,
            "consecutive_losses_alert": config.monitoring.consecutive_losses_alert,
            "error_rate_threshold": config.monitoring.error_rate_threshold,
            "alert_enabled": config.monitoring.alert_enabled,
            "email_alerts_enabled": config.monitoring.email_alerts_enabled,
            "webhook_alerts_enabled": config.monitoring.webhook_alerts_enabled,
            "alert_cooldown_minutes": config.monitoring.alert_cooldown_minutes,
            "daily_report_enabled": config.monitoring.daily_report_enabled,
            "weekly_report_enabled": config.monitoring.weekly_report_enabled,
            "report_recipients": config.monitoring.report_recipients,
            "dashboard_enabled": config.monitoring.dashboard_enabled,
            "dashboard_port": config.monitoring.dashboard_port,
            "dashboard_refresh_interval": config.monitoring.dashboard_refresh_interval,
        },
        "llm": {
            "primary_provider": config.llm.primary_provider,
            "fallback_providers": config.llm.fallback_providers,
            "default_model": config.llm.default_model,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "openai_api_key": "***REDACTED***",
            "gemini_api_key": "***REDACTED***",
            "openai_model": config.llm.openai_model,
            "gemini_model": config.llm.gemini_model,
            "enable_caching": config.llm.enable_caching,
            "cache_ttl_seconds": config.llm.cache_ttl_seconds,
            "cache_size_limit": config.llm.cache_size_limit,
            "request_timeout_seconds": config.llm.request_timeout_seconds,
            "max_retries": config.llm.max_retries,
            "retry_delay_seconds": config.llm.retry_delay_seconds,
            "requests_per_minute": config.llm.requests_per_minute,
            "tokens_per_minute": config.llm.tokens_per_minute,
            "enable_adaptive_routing": config.llm.enable_adaptive_routing,
            "routing_strategy": config.llm.routing_strategy,
        },
        "security": {
            "api_key_encryption_enabled": config.security.api_key_encryption_enabled,
            "request_signing_enabled": config.security.request_signing_enabled,
            "rate_limiting_enabled": config.security.rate_limiting_enabled,
            "database_encryption_enabled": config.security.database_encryption_enabled,
            "log_encryption_enabled": config.security.log_encryption_enabled,
            "sensitive_data_masking": config.security.sensitive_data_masking,
            "ip_whitelist_enabled": config.security.ip_whitelist_enabled,
            "allowed_ips": config.security.allowed_ips,
            "session_timeout_minutes": config.security.session_timeout_minutes,
            "audit_logging_enabled": config.security.audit_logging_enabled,
            "log_retention_days": config.security.log_retention_days,
            "failed_login_threshold": config.security.failed_login_threshold,
            "emergency_stop_enabled": config.security.emergency_stop_enabled,
            "max_daily_loss_pct": config.security.max_daily_loss_pct,
            "manual_approval_required": config.security.manual_approval_required,
        },
        "environment": config.environment,
        "debug_mode": config.debug_mode,
        "log_level": config.log_level,
        "max_concurrent_tasks": config.max_concurrent_tasks,
        "task_queue_size": config.task_queue_size,
        "enable_async_operations": config.enable_async_operations,
        "enable_paper_trading": config.enable_paper_trading,
        "enable_simulation_mode": config.enable_simulation_mode,
        "enable_backtesting": config.enable_backtesting,
        "enable_live_trading": config.enable_live_trading,
        "max_memory_usage_mb": config.max_memory_usage_mb,
        "max_cpu_usage_pct": config.max_cpu_usage_pct,
        "max_disk_usage_pct": config.max_disk_usage_pct,
    }

    # Write to file
    with open(file_path, "w") as f:
        json.dump(config_dict, f, indent=2, default=str)
