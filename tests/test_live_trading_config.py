"""
Unit tests for live trading configuration and data models.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from libs.trading_models.live_trading_config import (
    DEFAULT_EMERGENCY_TRIGGERS,
    EmergencyAction,
    EmergencyResponse,
    EmergencyTrigger,
    LiveTradingConfig,
    PerformanceMetrics,
    PerformanceThresholds,
    RiskLimits,
    ScalingValidation,
    TradingMode,
    TradingStatus,
    ValidationResult,
    create_live_minimal_config,
    create_live_scaled_config,
    create_paper_trading_config,
)


class TestEmergencyTrigger:
    """Test EmergencyTrigger data model."""

    def test_valid_trigger_creation(self):
        """Test creating a valid emergency trigger."""
        trigger = EmergencyTrigger(
            condition="drawdown_exceeded",
            threshold=0.05,
            action=EmergencyAction.HALT_NEW_TRADES,
            cooldown_hours=4
        )

        assert trigger.condition == "drawdown_exceeded"
        assert trigger.threshold == 0.05
        assert trigger.action == EmergencyAction.HALT_NEW_TRADES
        assert trigger.cooldown_hours == 4
        assert trigger.enabled is True

    def test_negative_threshold_raises_error(self):
        """Test that negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="Threshold must be non-negative"):
            EmergencyTrigger(
                condition="test",
                threshold=-0.1,
                action=EmergencyAction.HALT_NEW_TRADES,
                cooldown_hours=1
            )

    def test_negative_cooldown_raises_error(self):
        """Test that negative cooldown raises ValueError."""
        with pytest.raises(ValueError, match="Cooldown hours must be non-negative"):
            EmergencyTrigger(
                condition="test",
                threshold=0.1,
                action=EmergencyAction.HALT_NEW_TRADES,
                cooldown_hours=-1
            )


class TestPerformanceThresholds:
    """Test PerformanceThresholds data model."""

    def test_valid_thresholds_creation(self):
        """Test creating valid performance thresholds."""
        thresholds = PerformanceThresholds(
            min_win_rate=0.5,
            min_sharpe_ratio=1.0,
            max_drawdown=0.1,
            min_profit_factor=1.5
        )

        assert thresholds.min_win_rate == 0.5
        assert thresholds.min_sharpe_ratio == 1.0
        assert thresholds.max_drawdown == 0.1
        assert thresholds.min_profit_factor == 1.5

    def test_invalid_win_rate_raises_error(self):
        """Test that invalid win rate raises ValueError."""
        with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
            PerformanceThresholds(min_win_rate=1.5)

        with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
            PerformanceThresholds(min_win_rate=-0.1)

    def test_negative_drawdown_raises_error(self):
        """Test that negative drawdown raises ValueError."""
        with pytest.raises(ValueError, match="Max drawdown must be non-negative"):
            PerformanceThresholds(max_drawdown=-0.1)

    def test_invalid_profit_factor_raises_error(self):
        """Test that invalid profit factor raises ValueError."""
        with pytest.raises(ValueError, match="Profit factor must be positive"):
            PerformanceThresholds(min_profit_factor=0)


class TestRiskLimits:
    """Test RiskLimits data model."""

    def test_valid_risk_limits_creation(self):
        """Test creating valid risk limits."""
        limits = RiskLimits(
            max_risk_per_trade=0.01,
            max_portfolio_exposure=0.2,
            daily_loss_limit=0.05
        )

        assert limits.max_risk_per_trade == 0.01
        assert limits.max_portfolio_exposure == 0.2
        assert limits.daily_loss_limit == 0.05

    def test_invalid_risk_per_trade_raises_error(self):
        """Test that invalid risk per trade raises ValueError."""
        with pytest.raises(ValueError, match="Risk per trade must be between 0 and 0.1"):
            RiskLimits(
                max_risk_per_trade=0.15,  # Too high
                max_portfolio_exposure=0.2,
                daily_loss_limit=0.05
            )

        with pytest.raises(ValueError, match="Risk per trade must be between 0 and 0.1"):
            RiskLimits(
                max_risk_per_trade=0,  # Zero not allowed
                max_portfolio_exposure=0.2,
                daily_loss_limit=0.05
            )

    def test_invalid_portfolio_exposure_raises_error(self):
        """Test that invalid portfolio exposure raises ValueError."""
        with pytest.raises(ValueError, match="Portfolio exposure must be between 0 and 1.0"):
            RiskLimits(
                max_risk_per_trade=0.01,
                max_portfolio_exposure=1.5,  # Too high
                daily_loss_limit=0.05
            )


class TestLiveTradingConfig:
    """Test LiveTradingConfig data model."""

    def test_valid_config_creation(self):
        """Test creating a valid live trading configuration."""
        config = create_paper_trading_config()

        assert config.mode == TradingMode.PAPER
        assert config.testnet is True
        assert len(config.allowed_symbols) > 0
        assert len(config.emergency_triggers) > 0

    def test_empty_symbols_raises_error(self):
        """Test that empty allowed symbols raises ValueError."""
        with pytest.raises(ValueError, match="At least one symbol must be allowed"):
            LiveTradingConfig(
                mode=TradingMode.PAPER,
                risk_limits=RiskLimits(0.01, 0.2, 0.05),
                allowed_symbols=[],  # Empty list
                performance_thresholds=PerformanceThresholds(),
                emergency_triggers=[]
            )

    def test_config_serialization(self):
        """Test configuration serialization to/from dictionary."""
        config = create_live_minimal_config()

        # Convert to dictionary
        config_dict = config.to_dict()

        # Verify key fields
        assert config_dict["mode"] == "live_minimal"
        assert config_dict["testnet"] is False
        assert "BTCUSDT" in config_dict["allowed_symbols"]

        # Convert back from dictionary
        restored_config = LiveTradingConfig.from_dict(config_dict)

        # Verify restoration
        assert restored_config.mode == config.mode
        assert restored_config.testnet == config.testnet
        assert restored_config.allowed_symbols == config.allowed_symbols


class TestPerformanceMetrics:
    """Test PerformanceMetrics data model."""

    def test_valid_metrics_creation(self):
        """Test creating valid performance metrics."""
        metrics = PerformanceMetrics(
            win_rate=0.6,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            total_pnl=1000.0,
            gross_profit=2000.0,
            gross_loss=-1000.0,
            profit_factor=2.0,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            avg_win=33.33,
            avg_loss=-25.0,
            largest_win=100.0,
            largest_loss=-50.0,
            avg_trade_duration=timedelta(hours=4),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )

        assert metrics.win_rate == 0.6
        assert metrics.total_trades == 100
        assert metrics.profit_factor == 2.0

    def test_inconsistent_trade_counts_raises_error(self):
        """Test that inconsistent trade counts raise ValueError."""
        with pytest.raises(ValueError, match="Total trades must equal winning \\+ losing trades"):
            PerformanceMetrics(
                win_rate=0.6,
                total_trades=100,
                winning_trades=60,
                losing_trades=30,  # Should be 40
                total_pnl=1000.0,
                gross_profit=2000.0,
                gross_loss=-1000.0,
                profit_factor=2.0,
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                avg_win=33.33,
                avg_loss=-25.0,
                largest_win=100.0,
                largest_loss=-50.0,
                avg_trade_duration=timedelta(hours=4),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )


class TestValidationResult:
    """Test ValidationResult data model."""

    def test_validation_summary(self):
        """Test validation result summary generation."""
        metrics = PerformanceMetrics(
            win_rate=0.6,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            total_pnl=500.0,
            gross_profit=1000.0,
            gross_loss=-500.0,
            profit_factor=2.0,
            sharpe_ratio=1.2,
            max_drawdown=0.08,
            avg_win=33.33,
            avg_loss=-25.0,
            largest_win=100.0,
            largest_loss=-50.0,
            avg_trade_duration=timedelta(hours=4),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7)
        )

        result = ValidationResult(
            passed=True,
            performance=metrics,
            validation_period=timedelta(days=7),
            issues=[],
            timestamp=datetime.utcnow(),
            win_rate_passed=True,
            sharpe_ratio_passed=True,
            drawdown_passed=True,
            profit_factor_passed=True,
            min_trades_passed=True
        )

        summary = result.get_summary()

        assert summary["passed"] is True
        assert summary["validation_period_days"] == 7
        assert summary["performance"]["win_rate"] == 0.6
        assert summary["validation_checks"]["win_rate_passed"] is True
        assert summary["issues_count"] == 0


class TestScalingValidation:
    """Test ScalingValidation data model."""

    def test_next_risk_level_calculation(self):
        """Test next risk level calculation."""
        metrics = PerformanceMetrics(
            win_rate=0.6, total_trades=50, winning_trades=30, losing_trades=20,
            total_pnl=500.0, gross_profit=1000.0, gross_loss=-500.0,
            profit_factor=2.0, sharpe_ratio=1.2, max_drawdown=0.08,
            avg_win=33.33, avg_loss=-25.0, largest_win=100.0, largest_loss=-50.0,
            avg_trade_duration=timedelta(hours=4),
            start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 7)
        )

        validation = ScalingValidation(
            can_scale=True,
            current_performance=metrics,
            required_thresholds=PerformanceThresholds(),
            days_since_last_scale=10,
            risk_concentration=0.3,
            market_volatility=0.2
        )

        current_risk = 0.001  # 0.1%
        next_risk = validation.get_next_risk_level(current_risk)

        assert next_risk == 0.0015  # 0.15% (1.5x scaling)

        # Test when scaling not allowed
        validation.can_scale = False
        next_risk = validation.get_next_risk_level(current_risk)
        assert next_risk == current_risk


class TestEmergencyResponse:
    """Test EmergencyResponse data model."""

    def test_cooldown_check(self):
        """Test cooldown period checking."""
        future_time = datetime.utcnow() + timedelta(hours=2)

        response = EmergencyResponse(
            trigger_reason="Test emergency",
            trigger_condition="manual_override",
            actions_taken=["halt_trading"],
            positions_closed=[],
            cooldown_until=future_time,
            recovery_steps=["manual_review"],
            timestamp=datetime.utcnow()
        )

        assert response.is_in_cooldown() is True

        # Test past cooldown
        past_time = datetime.utcnow() - timedelta(hours=1)
        response.cooldown_until = past_time

        assert response.is_in_cooldown() is False


class TestTradingStatus:
    """Test TradingStatus data model."""

    def test_status_serialization(self):
        """Test trading status serialization."""
        status = TradingStatus(
            mode=TradingMode.LIVE_MINIMAL,
            is_active=True,
            current_positions=2,
            total_exposure=0.05,
            daily_pnl=100.0,
            unrealized_pnl=50.0,
            last_trade_time=datetime(2024, 1, 1, 12, 0, 0),
            emergency_active=False,
            cooldown_until=None,
            system_health="healthy",
            last_update=datetime(2024, 1, 1, 12, 30, 0)
        )

        status_dict = status.to_dict()

        assert status_dict["mode"] == "live_minimal"
        assert status_dict["is_active"] is True
        assert status_dict["current_positions"] == 2
        assert status_dict["last_trade_time"] == "2024-01-01T12:00:00"


class TestPredefinedConfigs:
    """Test predefined configuration functions."""

    def test_paper_trading_config(self):
        """Test paper trading configuration."""
        config = create_paper_trading_config()

        assert config.mode == TradingMode.PAPER
        assert config.testnet is True
        assert config.risk_limits.max_risk_per_trade == 0.005
        assert "BTCUSDT" in config.allowed_symbols

    def test_live_minimal_config(self):
        """Test live minimal configuration."""
        config = create_live_minimal_config()

        assert config.mode == TradingMode.LIVE_MINIMAL
        assert config.testnet is False
        assert config.risk_limits.max_risk_per_trade == 0.001
        assert config.auto_scaling is False

    def test_live_scaled_config(self):
        """Test live scaled configuration."""
        config = create_live_scaled_config()

        assert config.mode == TradingMode.LIVE_SCALED
        assert config.testnet is False
        assert config.risk_limits.max_risk_per_trade == 0.005
        assert config.auto_scaling is True
        assert len(config.allowed_symbols) >= 3

    def test_default_emergency_triggers(self):
        """Test default emergency triggers."""
        assert len(DEFAULT_EMERGENCY_TRIGGERS) == 5

        # Check for specific triggers
        trigger_conditions = [t.condition for t in DEFAULT_EMERGENCY_TRIGGERS]
        assert "daily_loss_exceeded" in trigger_conditions
        assert "drawdown_exceeded" in trigger_conditions
        assert "manual_override" in trigger_conditions


if __name__ == "__main__":
    pytest.main([__file__])
