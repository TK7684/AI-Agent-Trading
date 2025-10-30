"""
Integration tests for Live Trading Controller.
"""

from datetime import UTC, datetime, timedelta

import pytest

from libs.trading_models.live_trading_config import (
    PerformanceMetrics,
    TradingMode,
    create_paper_trading_config,
)
from libs.trading_models.live_trading_controller import (
    LiveTradingController,
    ModeTransition,
    TransitionResult,
)


@pytest.fixture
def paper_config():
    """Create paper trading configuration."""
    return create_paper_trading_config()


@pytest.fixture
def controller(paper_config):
    """Create live trading controller."""
    return LiveTradingController(paper_config)


@pytest.fixture
def good_performance():
    """Create good performance metrics that pass validation."""
    return PerformanceMetrics(
        win_rate=0.55,  # 55%
        total_trades=20,
        winning_trades=11,
        losing_trades=9,
        total_pnl=5000.0,
        gross_profit=8000.0,
        gross_loss=3000.0,
        profit_factor=2.67,
        sharpe_ratio=1.2,
        max_drawdown=0.10,  # 10%
        avg_win=727.27,
        avg_loss=333.33,
        largest_win=1500.0,
        largest_loss=800.0,
        avg_trade_duration=timedelta(hours=12),
        start_date=datetime.now(UTC) - timedelta(days=7),
        end_date=datetime.now(UTC)
    )


@pytest.fixture
def poor_performance():
    """Create poor performance metrics that fail validation."""
    return PerformanceMetrics(
        win_rate=0.35,  # 35% - below threshold
        total_trades=15,
        winning_trades=5,
        losing_trades=10,
        total_pnl=-2000.0,
        gross_profit=3000.0,
        gross_loss=5000.0,
        profit_factor=0.6,  # Below threshold
        sharpe_ratio=0.2,  # Below threshold
        max_drawdown=0.20,  # 20% - above threshold
        avg_win=600.0,
        avg_loss=500.0,
        largest_win=1000.0,
        largest_loss=1200.0,
        avg_trade_duration=timedelta(hours=8),
        start_date=datetime.now(UTC) - timedelta(days=7),
        end_date=datetime.now(UTC)
    )


class TestLiveTradingController:
    """Test suite for LiveTradingController class."""

    def test_initialization(self, controller, paper_config):
        """Test controller initialization."""
        assert controller.current_mode == TradingMode.PAPER
        assert not controller.is_active
        assert controller.circuit_breaker is not None
        assert len(controller.transition_history) == 0

    def test_start_paper_trading(self, controller):
        """Test starting paper trading."""
        assert controller.start_paper_trading(duration_days=7)
        assert controller.is_active
        assert controller.paper_trading_start is not None
        assert controller.current_mode == TradingMode.PAPER

    def test_start_paper_trading_with_emergency(self, controller):
        """Test that paper trading cannot start during emergency."""
        controller.circuit_breaker.emergency_active = True
        assert not controller.start_paper_trading()
        assert not controller.is_active

    def test_validate_paper_trading_good_performance(self, controller, good_performance):
        """Test validation with good performance."""
        result = controller.validate_paper_trading_results(good_performance)

        assert result["passed"]
        assert result["win_rate_passed"]
        assert result["sharpe_ratio_passed"]
        assert result["drawdown_passed"]
        assert result["profit_factor_passed"]
        assert result["min_trades_passed"]
        assert len(result["issues"]) == 0

    def test_validate_paper_trading_poor_performance(self, controller, poor_performance):
        """Test validation with poor performance."""
        result = controller.validate_paper_trading_results(poor_performance)

        assert not result["passed"]
        assert not result["win_rate_passed"]
        assert not result["sharpe_ratio_passed"]
        assert not result["drawdown_passed"]
        assert not result["profit_factor_passed"]
        assert len(result["issues"]) > 0

    def test_transition_to_live_without_validation(self, controller):
        """Test that transition fails without validation."""
        result = controller.transition_to_live_trading(manual_approval=True)
        assert result == TransitionResult.FAILED_VALIDATION

    def test_transition_to_live_without_approval(self, controller, good_performance):
        """Test that transition requires manual approval."""
        controller.validate_paper_trading_results(good_performance)
        result = controller.transition_to_live_trading(manual_approval=False)
        assert result == TransitionResult.MANUAL_APPROVAL_REQUIRED

    def test_transition_to_live_success(self, controller, good_performance):
        """Test successful transition to live trading."""
        controller.validate_paper_trading_results(good_performance)
        result = controller.transition_to_live_trading(manual_approval=True)

        assert result == TransitionResult.SUCCESS
        assert controller.current_mode == TradingMode.LIVE_MINIMAL
        assert controller.live_trading_start is not None
        assert len(controller.transition_history) == 1
        assert controller.config.risk_limits.max_risk_per_trade == 0.001

    def test_transition_with_emergency_active(self, controller, good_performance):
        """Test that transition fails during emergency."""
        controller.validate_paper_trading_results(good_performance)
        controller.circuit_breaker.emergency_active = True

        result = controller.transition_to_live_trading(manual_approval=True)
        assert result == TransitionResult.EMERGENCY_ACTIVE

    def test_scale_trading_operations(self, controller, good_performance):
        """Test scaling trading operations."""
        # First transition to live
        controller.validate_paper_trading_results(good_performance)
        controller.transition_to_live_trading(manual_approval=True)

        # Scale up
        assert controller.scale_trading_operations(0.0025, "Performance validated")
        assert controller.config.risk_limits.max_risk_per_trade == 0.0025

    def test_scale_to_scaled_mode(self, controller, good_performance):
        """Test scaling transitions to LIVE_SCALED mode."""
        controller.validate_paper_trading_results(good_performance)
        controller.transition_to_live_trading(manual_approval=True)

        # Scale to higher level
        assert controller.scale_trading_operations(0.005, "Significant scaling")
        assert controller.current_mode == TradingMode.LIVE_SCALED

    def test_scale_invalid_risk_level(self, controller, good_performance):
        """Test that invalid risk levels are rejected."""
        controller.validate_paper_trading_results(good_performance)
        controller.transition_to_live_trading(manual_approval=True)

        assert not controller.scale_trading_operations(0.02, "Too high")  # 2% is too high
        assert not controller.scale_trading_operations(-0.001, "Negative")

    def test_scale_in_paper_mode(self, controller):
        """Test that scaling fails in paper mode."""
        assert not controller.scale_trading_operations(0.005)

    def test_emergency_stop(self, controller):
        """Test emergency stop execution."""
        controller.start_paper_trading()
        controller.emergency_stop("Test emergency")

        assert controller.current_mode == TradingMode.EMERGENCY_STOP
        assert not controller.is_active
        assert controller.circuit_breaker.emergency_active
        assert len(controller.transition_history) == 1

    def test_manual_override(self, controller):
        """Test manual override functionality."""
        assert not controller.manual_override_active

        controller.enable_manual_override()
        assert controller.manual_override_active

        controller.disable_manual_override()
        assert not controller.manual_override_active

    def test_update_system_state_normal(self, controller):
        """Test system state update with normal values."""
        controller.start_paper_trading()

        controller.update_system_state(
            current_drawdown=0.01,
            daily_loss=0.005,
            api_latency_ms=500,
            position_correlation=0.3
        )

        # Should not trigger emergency
        assert controller.current_mode != TradingMode.EMERGENCY_STOP

    def test_update_system_state_triggers_emergency(self, controller):
        """Test system state update triggers emergency."""
        controller.start_paper_trading()

        controller.update_system_state(
            current_drawdown=0.05,  # 5% - exceeds threshold
            daily_loss=0.02,  # 2% - exceeds threshold
            api_latency_ms=3000,  # 3s - exceeds threshold
            position_correlation=0.8  # 80% - exceeds threshold
        )

        # Should trigger emergency
        assert controller.current_mode == TradingMode.EMERGENCY_STOP
        assert controller.circuit_breaker.emergency_active

    def test_get_current_status(self, controller):
        """Test getting current status."""
        controller.start_paper_trading()
        status = controller.get_current_status()

        assert status.mode == TradingMode.PAPER
        assert status.is_active
        assert status.current_positions == 0
        assert status.system_health == "healthy"

    def test_get_transition_history(self, controller, good_performance):
        """Test getting transition history."""
        # Make some transitions
        controller.validate_paper_trading_results(good_performance)
        controller.transition_to_live_trading(manual_approval=True)
        controller.scale_trading_operations(0.005)

        history = controller.get_transition_history()
        assert len(history) >= 2
        assert all(isinstance(t, ModeTransition) for t in history)

    def test_can_place_trade_inactive(self, controller):
        """Test trade placement check when inactive."""
        can_trade, reason = controller.can_place_trade()
        assert not can_trade
        assert "not active" in reason.lower()

    def test_can_place_trade_emergency(self, controller):
        """Test trade placement check during emergency."""
        controller.start_paper_trading()
        controller.circuit_breaker.emergency_active = True

        can_trade, reason = controller.can_place_trade()
        assert not can_trade
        assert "emergency" in reason.lower()

    def test_can_place_trade_exposure_limit(self, controller):
        """Test trade placement check with exposure limit."""
        controller.start_paper_trading()
        controller.total_exposure = 0.25  # 25% - exceeds limit

        can_trade, reason = controller.can_place_trade()
        assert not can_trade
        assert "exposure" in reason.lower()

    def test_can_place_trade_daily_loss_limit(self, controller):
        """Test trade placement check with daily loss limit."""
        controller.start_paper_trading()
        controller.daily_pnl = -0.06  # -6% - exceeds 5% limit

        can_trade, reason = controller.can_place_trade()
        assert not can_trade
        assert "loss limit" in reason.lower()

    def test_can_place_trade_success(self, controller):
        """Test successful trade placement check."""
        controller.start_paper_trading()

        can_trade, reason = controller.can_place_trade()
        assert can_trade
        assert reason is None

    def test_update_position_metrics(self, controller):
        """Test updating position metrics."""
        controller.update_position_metrics(
            positions=3,
            exposure=0.15,
            daily_pnl=0.02,
            unrealized_pnl=0.01
        )

        assert controller.current_positions == 3
        assert controller.total_exposure == 0.15
        assert controller.daily_pnl == 0.02
        assert controller.unrealized_pnl == 0.01
        assert controller.last_trade_time is not None


class TestModeTransition:
    """Test suite for ModeTransition class."""

    def test_mode_transition_creation(self):
        """Test creating a mode transition."""
        transition = ModeTransition(
            from_mode=TradingMode.PAPER,
            to_mode=TradingMode.LIVE_MINIMAL,
            timestamp=datetime.now(UTC),
            result=TransitionResult.SUCCESS,
            reason="Validation passed"
        )

        assert transition.from_mode == TradingMode.PAPER
        assert transition.to_mode == TradingMode.LIVE_MINIMAL
        assert transition.result == TransitionResult.SUCCESS
