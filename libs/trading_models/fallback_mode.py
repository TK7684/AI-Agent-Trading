"""
Fallback mode handler for running the trading system without database connectivity.

This module enables the system to operate in a limited read-only/demo mode
when the database is unavailable, providing mock data and clear warnings.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import structlog

from .base import BaseModel as TradingBaseModel

logger = structlog.get_logger(__name__)


class FallbackConfig(TradingBaseModel):
    """Configuration for fallback mode."""
    enabled: bool = False
    mock_data_enabled: bool = True
    warning_interval_minutes: int = 30
    check_database_interval_minutes: int = 5
    mock_data_file: Optional[str] = None


class MockDataGenerator:
    """Generates realistic mock data for fallback mode."""

    def __init__(self):
        self.logger = logger.bind(component="MockDataGenerator")
        self._last_prices = {}
        self._base_time = datetime.now(UTC)

    def generate_trade_record(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        """Generate a mock trade record."""
        trade_id = str(uuid.uuid4())
        entry_time = self._base_time - timedelta(hours=2)
        exit_time = self._base_time - timedelta(hours=1)

        entry_price = 45000.0 + (hash(trade_id) % 10000)
        exit_price = entry_price * (1 + (hash(trade_id) % 100 - 50) / 1000)
        quantity = 0.1

        pnl = (exit_price - entry_price) * quantity
        pnl_percentage = (pnl / (entry_price * quantity)) * 100

        return {
            "id": trade_id,
            "symbol": symbol,
            "direction": "LONG" if pnl > 0 else "SHORT",
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "entry_time": entry_time.isoformat(),
            "exit_time": exit_time.isoformat(),
            "pnl": pnl,
            "pnl_percentage": pnl_percentage,
            "fees": 5.0,
            "status": "CLOSED",
            "stop_loss": entry_price * 0.95,
            "take_profit": entry_price * 1.1,
            "pattern_id": f"pattern_{hash(trade_id) % 100}",
            "confidence_score": 0.75 + (hash(trade_id) % 25) / 100,
            "reasoning": "Mock trade for demonstration purposes",
            "trade_metadata": {"mock": True, "fallback_mode": True},
            "created_at": entry_time.isoformat(),
            "updated_at": exit_time.isoformat()
        }

    def generate_position_record(self, trade_id: str, symbol: str = "BTCUSDT") -> dict[str, Any]:
        """Generate a mock position record."""
        current_price = 45000.0 + (hash(trade_id) % 5000)
        average_price = current_price * (1 + (hash(trade_id) % 20 - 10) / 1000)
        quantity = 0.1

        unrealized_pnl = (current_price - average_price) * quantity
        unrealized_pnl_percentage = (unrealized_pnl / (average_price * quantity)) * 100

        return {
            "id": str(uuid.uuid4()),
            "trade_id": trade_id,
            "symbol": symbol,
            "quantity": quantity,
            "average_price": average_price,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_percentage": unrealized_pnl_percentage,
            "margin_used": average_price * quantity * 0.1,  # 10x leverage
            "timestamp": datetime.now(UTC).isoformat(),
            "position_metadata": {"mock": True, "fallback_mode": True}
        }

    def generate_performance_metrics(self) -> list[dict[str, Any]]:
        """Generate mock performance metrics."""
        metrics = []
        metric_names = [
            "total_pnl", "win_rate", "sharpe_ratio", "max_drawdown",
            "total_trades", "avg_trade_duration", "profit_factor"
        ]

        for metric_name in metric_names:
            value = {
                "total_pnl": 1250.75,
                "win_rate": 0.65,
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.12,
                "total_trades": 45,
                "avg_trade_duration": 2.5,
                "profit_factor": 1.4
            }.get(metric_name, 0.0)

            metrics.append({
                "id": str(uuid.uuid4()),
                "metric_name": metric_name,
                "metric_value": value,
                "period_start": (self._base_time - timedelta(days=30)).isoformat(),
                "period_end": self._base_time.isoformat(),
                "symbol": None,
                "pattern_id": None,
                "timeframe": "30d",
                "metric_metadata": {"mock": True, "fallback_mode": True},
                "timestamp": datetime.now(UTC).isoformat()
            })

        return metrics

    def generate_market_data(self, symbol: str = "BTCUSDT") -> dict[str, Any]:
        """Generate mock market data."""
        base_price = 45000.0
        current_price = base_price + (hash(symbol) % 5000)

        return {
            "symbol": symbol,
            "price": current_price,
            "volume": 1000000 + (hash(symbol) % 500000),
            "change_24h": (hash(symbol) % 200 - 100) / 10,  # -10% to +10%
            "high_24h": current_price * 1.05,
            "low_24h": current_price * 0.95,
            "timestamp": datetime.now(UTC).isoformat(),
            "mock": True,
            "fallback_mode": True
        }


class FallbackMode:
    """Manages fallback mode operation when database is unavailable."""

    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.logger = logger.bind(component="FallbackMode")
        self._enabled = False
        self._last_warning = None
        self._last_db_check = None
        self._mock_generator = MockDataGenerator()
        self._warning_count = 0

    def enable(self, reason: str = "Database unavailable") -> None:
        """
        Enable fallback mode.

        Args:
            reason: Reason for enabling fallback mode
        """
        if not self._enabled:
            self._enabled = True
            self.logger.warning("Fallback mode enabled", reason=reason)
            self._log_warning("system_startup", {
                "message": "System started in fallback mode",
                "reason": reason,
                "limitations": [
                    "No data persistence",
                    "Mock data only",
                    "Limited functionality",
                    "Read-only operations"
                ]
            })

    def disable(self) -> None:
        """Disable fallback mode."""
        if self._enabled:
            self._enabled = False
            self.logger.info("Fallback mode disabled - database connection restored")

    def is_enabled(self) -> bool:
        """Check if fallback mode is currently enabled."""
        return self._enabled

    def get_mock_data(self, data_type: str, **kwargs) -> Any:
        """
        Get mock data for the specified type.

        Args:
            data_type: Type of data to generate (trades, positions, metrics, market_data)
            **kwargs: Additional parameters for data generation

        Returns:
            Mock data of the requested type
        """
        if not self._enabled:
            self.logger.warning("Mock data requested but fallback mode not enabled")
            return None

        try:
            if data_type == "trade":
                return self._mock_generator.generate_trade_record(
                    kwargs.get("symbol", "BTCUSDT")
                )

            elif data_type == "trades":
                count = kwargs.get("count", 10)
                symbol = kwargs.get("symbol", "BTCUSDT")
                return [
                    self._mock_generator.generate_trade_record(symbol)
                    for _ in range(count)
                ]

            elif data_type == "position":
                return self._mock_generator.generate_position_record(
                    kwargs.get("trade_id", str(uuid.uuid4())),
                    kwargs.get("symbol", "BTCUSDT")
                )

            elif data_type == "positions":
                count = kwargs.get("count", 5)
                return [
                    self._mock_generator.generate_position_record(
                        str(uuid.uuid4()),
                        kwargs.get("symbol", "BTCUSDT")
                    )
                    for _ in range(count)
                ]

            elif data_type == "metrics":
                return self._mock_generator.generate_performance_metrics()

            elif data_type == "market_data":
                return self._mock_generator.generate_market_data(
                    kwargs.get("symbol", "BTCUSDT")
                )

            else:
                self.logger.warning("Unknown mock data type requested", data_type=data_type)
                return None

        except Exception as e:
            self.logger.error("Error generating mock data", data_type=data_type, error=str(e))
            return None

    def log_warning(self, operation: str, details: dict[str, Any] = None) -> None:
        """
        Log a warning about operation attempted in fallback mode.

        Args:
            operation: Name of the operation attempted
            details: Additional details about the operation
        """
        if not self._enabled:
            return

        # Rate limit warnings
        now = datetime.now(UTC)
        if (self._last_warning and
            (now - self._last_warning).total_seconds() < self.config.warning_interval_minutes * 60):
            return

        self._last_warning = now
        self._warning_count += 1

        warning_data = {
            "operation": operation,
            "fallback_mode": True,
            "warning_count": self._warning_count,
            "details": details or {}
        }

        self.logger.warning(
            f"Operation '{operation}' attempted in fallback mode - limited functionality",
            **warning_data
        )

    def _log_warning(self, operation: str, details: dict[str, Any]) -> None:
        """Internal method to log warnings without rate limiting."""
        self.logger.warning(
            f"Fallback mode: {operation}",
            fallback_mode=True,
            **details
        )

    def check_database_available(self, connection_string: str = None) -> bool:
        """
        Check if database has become available.

        Args:
            connection_string: Optional connection string to test

        Returns:
            True if database is available, False otherwise
        """
        if not self._enabled:
            return True

        # Rate limit database checks
        now = datetime.now(UTC)
        if (self._last_db_check and
            (now - self._last_db_check).total_seconds() < self.config.check_database_interval_minutes * 60):
            return False

        self._last_db_check = now

        if not connection_string:
            return False

        try:
            # Import here to avoid circular imports
            from .db_validator import DatabaseValidator

            validator = DatabaseValidator()
            result = validator.test_connection(connection_string)

            if result.success:
                self.logger.info("Database connection restored - disabling fallback mode")
                self.disable()
                return True
            else:
                self.logger.debug("Database still unavailable", error_type=result.error_type)
                return False

        except Exception as e:
            self.logger.debug("Error checking database availability", error=str(e))
            return False

    def get_status(self) -> dict[str, Any]:
        """
        Get current fallback mode status.

        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self._enabled,
            "warning_count": self._warning_count,
            "last_warning": self._last_warning.isoformat() if self._last_warning else None,
            "last_db_check": self._last_db_check.isoformat() if self._last_db_check else None,
            "config": self.config.model_dump(),
            "limitations": [
                "No data persistence - changes are not saved",
                "Mock data only - not real trading data",
                "Limited functionality - some features disabled",
                "Read-only operations - cannot modify settings"
            ] if self._enabled else []
        }

    def get_user_message(self) -> str:
        """
        Get user-friendly message about fallback mode status.

        Returns:
            Formatted message for display
        """
        if not self._enabled:
            return "✅ Database connected - full functionality available"

        return """⚠️  Running in Fallback Mode

The system is running with limited functionality because the database is unavailable.

Current limitations:
• No data persistence - changes are not saved
• Mock data only - not real trading data
• Some features may be disabled
• Read-only operations only

To restore full functionality:
1. Fix database connection issues
2. Run: .\\scripts\\Setup-Database.ps1
3. Restart the application

The system will automatically reconnect when the database becomes available."""


# Global fallback mode instance
_fallback_instance = None


def get_fallback_mode() -> FallbackMode:
    """Get the global fallback mode instance."""
    global _fallback_instance
    if _fallback_instance is None:
        _fallback_instance = FallbackMode()
    return _fallback_instance


def is_fallback_enabled() -> bool:
    """Check if fallback mode is currently enabled."""
    return get_fallback_mode().is_enabled()


def enable_fallback_mode(reason: str = "Database unavailable") -> None:
    """Enable fallback mode globally."""
    get_fallback_mode().enable(reason)


def disable_fallback_mode() -> None:
    """Disable fallback mode globally."""
    get_fallback_mode().disable()
