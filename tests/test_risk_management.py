"""Tests for risk management system."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from libs.trading_models.enums import Direction
from libs.trading_models.risk_management import (
    CorrelationMonitor,
    DrawdownProtection,
    PortfolioMetrics,
    Position,
    PositionSizer,
    RiskLimits,
    RiskManager,
    SafeMode,
    StopLossManager,
    StopType,
)


class TestPositionSizer:
    """Test position sizing calculator."""

    def test_basic_position_sizing(self):
        """Test basic position size calculation."""
        sizer = PositionSizer(base_risk_pct=0.01)

        portfolio_value = Decimal("100000")
        entry_price = Decimal("50")
        stop_loss = Decimal("48")
        confidence = 0.8
        leverage = 1.0

        position_size, risk_pct = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, confidence, leverage
        )

        # Expected: 1% risk * 1.65 confidence multiplier = 1.65% risk
        # Risk amount = $1650, Stop distance = $2, Position size = 825 shares
        assert risk_pct == pytest.approx(0.0165, rel=1e-3)
        assert position_size == pytest.approx(Decimal("825"), rel=1e-3)

    def test_confidence_scaling(self):
        """Test confidence-based position scaling."""
        sizer = PositionSizer(base_risk_pct=0.01)

        portfolio_value = Decimal("100000")
        entry_price = Decimal("100")
        stop_loss = Decimal("95")
        leverage = 1.0

        # Low confidence (0.2) should scale down
        pos_low, risk_low = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, 0.2, leverage
        )

        # High confidence (1.0) should scale up
        pos_high, risk_high = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, 1.0, leverage
        )

        assert risk_low < 0.01  # Below base risk
        assert risk_high > 0.01  # Above base risk
        assert pos_high > pos_low

    def test_leverage_adjustment(self):
        """Test leverage adjustment in position sizing."""
        sizer = PositionSizer(base_risk_pct=0.01)

        portfolio_value = Decimal("100000")
        entry_price = Decimal("100")
        stop_loss = Decimal("95")
        confidence = 0.5

        # Test different leverage levels
        pos_1x, _ = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, confidence, 1.0
        )

        pos_3x, _ = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, confidence, 3.0
        )

        # Position size should be the same regardless of leverage
        # Leverage affects margin requirements, not position size
        assert pos_3x == pos_1x

    def test_risk_bounds(self):
        """Test risk percentage bounds."""
        sizer = PositionSizer(base_risk_pct=0.01)

        portfolio_value = Decimal("100000")
        entry_price = Decimal("100")
        stop_loss = Decimal("95")
        leverage = 1.0

        # Extreme low confidence
        _, risk_low = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, 0.0, leverage
        )

        # Extreme high confidence
        _, risk_high = sizer.calculate_position_size(
            portfolio_value, entry_price, stop_loss, 1.0, leverage
        )

        # Should be bounded between 0.25% and 2%
        assert risk_low >= 0.0025
        assert risk_high <= 0.02

    def test_zero_stop_distance_error(self):
        """Test error handling for zero stop distance."""
        sizer = PositionSizer()

        with pytest.raises(ValueError, match="Stop loss cannot equal entry price"):
            sizer.calculate_position_size(
                Decimal("100000"), Decimal("100"), Decimal("100"), 0.5, 1.0
            )


class TestCorrelationMonitor:
    """Test correlation monitoring."""

    def test_correlation_update(self):
        """Test correlation matrix updates."""
        monitor = CorrelationMonitor()

        monitor.update_correlation("EURUSD", "GBPUSD", 0.8)

        assert monitor.get_correlation("EURUSD", "GBPUSD") == 0.8
        assert monitor.get_correlation("GBPUSD", "EURUSD") == 0.8

    def test_self_correlation(self):
        """Test self-correlation returns 1.0."""
        monitor = CorrelationMonitor()

        assert monitor.get_correlation("EURUSD", "EURUSD") == 1.0

    def test_unknown_correlation(self):
        """Test unknown correlation returns 0.0."""
        monitor = CorrelationMonitor()

        assert monitor.get_correlation("EURUSD", "UNKNOWN") == 0.0

    def test_correlation_limit_check(self):
        """Test correlation limit checking."""
        monitor = CorrelationMonitor(correlation_threshold=0.7, max_correlated_exposure=0.15)

        # Set up correlations
        monitor.update_correlation("EURUSD", "GBPUSD", 0.8)
        monitor.update_correlation("EURUSD", "AUDUSD", 0.6)  # Below threshold

        # Create existing positions
        existing_positions = [
            Position(
                position_id="1",
                symbol="GBPUSD",
                direction=Direction.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.30"),
                current_price=Decimal("1.31"),
                stop_loss=Decimal("1.28"),
                unrealized_pnl=Decimal("10"),
                initial_risk=Decimal("20"),
                current_risk=Decimal("20"),
                opened_at=datetime.utcnow()
            )
        ]

        portfolio_value = Decimal("100000")

        # Test new position that would violate correlation limits
        new_position_value = Decimal("20000")  # 20% of portfolio

        allowed, violations = monitor.check_correlation_limits(
            "EURUSD", new_position_value, existing_positions, portfolio_value
        )

        # Should be rejected due to high correlation and exposure
        assert not allowed
        assert len(violations) > 0
        assert "exceeding limit" in violations[0]

    def test_correlation_limit_allowed(self):
        """Test correlation limit check when allowed."""
        monitor = CorrelationMonitor(correlation_threshold=0.7, max_correlated_exposure=0.25)

        # Set up low correlation
        monitor.update_correlation("EURUSD", "USDJPY", 0.3)

        existing_positions = [
            Position(
                position_id="1",
                symbol="USDJPY",
                direction=Direction.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("110"),
                current_price=Decimal("111"),
                stop_loss=Decimal("108"),
                unrealized_pnl=Decimal("1000"),
                initial_risk=Decimal("2000"),
                current_risk=Decimal("2000"),
                opened_at=datetime.utcnow()
            )
        ]

        portfolio_value = Decimal("100000")
        new_position_value = Decimal("10000")

        allowed, violations = monitor.check_correlation_limits(
            "EURUSD", new_position_value, existing_positions, portfolio_value
        )

        assert allowed
        assert len(violations) == 0


class TestDrawdownProtection:
    """Test drawdown protection system."""

    def test_normal_drawdown(self):
        """Test normal operation with acceptable drawdown."""
        protection = DrawdownProtection(daily_limit=0.08, monthly_limit=0.20)

        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal("-2000"),
            daily_pnl=Decimal("-3000"),
            monthly_pnl=Decimal("-5000"),
            daily_drawdown=0.03,  # 3% - acceptable
            monthly_drawdown=0.05,  # 5% - acceptable
            max_drawdown=0.10,
            win_rate=0.65,
            sharpe_ratio=1.2,
            total_trades=100,
            open_positions=3
        )

        safe_mode, triggers = protection.check_drawdown_limits(metrics)

        assert safe_mode == SafeMode.NORMAL
        assert len(triggers) == 0

    def test_daily_drawdown_trigger(self):
        """Test daily drawdown limit trigger."""
        protection = DrawdownProtection(daily_limit=0.08, monthly_limit=0.20)

        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal("-8000"),
            daily_pnl=Decimal("-9000"),
            monthly_pnl=Decimal("-12000"),
            daily_drawdown=0.09,  # 9% - exceeds limit
            monthly_drawdown=0.12,
            max_drawdown=0.15,
            win_rate=0.45,
            sharpe_ratio=0.8,
            total_trades=100,
            open_positions=5
        )

        safe_mode, triggers = protection.check_drawdown_limits(metrics)

        assert safe_mode == SafeMode.SAFE_MODE
        assert len(triggers) > 0
        assert "Daily drawdown" in triggers[0]

    def test_monthly_drawdown_trigger(self):
        """Test monthly drawdown limit trigger."""
        protection = DrawdownProtection(daily_limit=0.08, monthly_limit=0.20)

        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal("-15000"),
            daily_pnl=Decimal("-2000"),
            monthly_pnl=Decimal("-25000"),
            daily_drawdown=0.02,
            monthly_drawdown=0.25,  # 25% - exceeds limit
            max_drawdown=0.30,
            win_rate=0.40,
            sharpe_ratio=0.5,
            total_trades=150,
            open_positions=2
        )

        safe_mode, triggers = protection.check_drawdown_limits(metrics)

        assert safe_mode == SafeMode.SAFE_MODE
        assert len(triggers) > 0
        assert "Monthly drawdown" in triggers[0]

    def test_emergency_mode_trigger(self):
        """Test emergency mode for extreme drawdowns."""
        protection = DrawdownProtection(daily_limit=0.08, monthly_limit=0.20)

        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("30000"),
            used_margin=Decimal("40000"),
            unrealized_pnl=Decimal("-15000"),
            daily_pnl=Decimal("-15000"),
            monthly_pnl=Decimal("-30000"),
            daily_drawdown=0.15,  # 15% - extreme (>1.5x limit)
            monthly_drawdown=0.30,
            max_drawdown=0.35,
            win_rate=0.30,
            sharpe_ratio=0.2,
            total_trades=200,
            open_positions=8
        )

        safe_mode, triggers = protection.check_drawdown_limits(metrics)

        assert safe_mode == SafeMode.EMERGENCY
        assert len(triggers) > 0
        # Check that extreme drawdown is mentioned in any trigger
        assert any("Extreme daily drawdown" in trigger for trigger in triggers)

    def test_position_size_adjustment(self):
        """Test position size adjustments based on safe mode."""
        protection = DrawdownProtection()

        # Normal mode
        protection.current_safe_mode = SafeMode.NORMAL
        assert protection.get_position_size_adjustment() == 1.0

        # Caution mode
        protection.current_safe_mode = SafeMode.CAUTION
        assert protection.get_position_size_adjustment() == 0.75

        # Safe mode
        protection.current_safe_mode = SafeMode.SAFE_MODE
        assert protection.get_position_size_adjustment() == 0.5

        # Emergency mode
        protection.current_safe_mode = SafeMode.EMERGENCY
        assert protection.get_position_size_adjustment() == 0.0

    def test_safe_mode_cooldown(self):
        """Test safe mode cooldown period."""
        protection = DrawdownProtection(safe_mode_cooldown=timedelta(hours=24))

        # Initially can exit (no safe mode)
        assert protection.can_exit_safe_mode()

        # Trigger safe mode
        protection.current_safe_mode = SafeMode.SAFE_MODE
        protection.safe_mode_triggered_at = datetime.now(UTC)

        # Cannot exit immediately
        assert not protection.can_exit_safe_mode()

        # Can exit after cooldown
        protection.safe_mode_triggered_at = datetime.now(UTC) - timedelta(hours=25)
        assert protection.can_exit_safe_mode()


class TestStopLossManager:
    """Test stop loss management."""

    def test_atr_stop_calculation(self):
        """Test ATR-based stop loss calculation."""
        manager = StopLossManager(atr_multiplier=2.0)

        entry_price = Decimal("100")
        atr_value = 2.5

        # Long position
        long_stop = manager.calculate_atr_stop(entry_price, Direction.LONG, atr_value)
        assert long_stop == Decimal("95")  # 100 - (2.5 * 2.0)

        # Short position
        short_stop = manager.calculate_atr_stop(entry_price, Direction.SHORT, atr_value)
        assert short_stop == Decimal("105")  # 100 + (2.5 * 2.0)

    def test_custom_atr_multiplier(self):
        """Test custom ATR multiplier."""
        manager = StopLossManager()

        entry_price = Decimal("50")
        atr_value = 1.0
        custom_multiplier = 3.0

        stop = manager.calculate_atr_stop(entry_price, Direction.LONG, atr_value, custom_multiplier)
        assert stop == Decimal("47")  # 50 - (1.0 * 3.0)

    def test_trailing_stop_calculation(self):
        """Test trailing stop calculation."""
        manager = StopLossManager(atr_multiplier=2.0, trailing_activation_pct=0.02)

        # Create position with profit
        position = Position(
            position_id="test",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1050"),
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.TRAILING,
            unrealized_pnl=Decimal("50"),  # 5% profit
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        current_price = Decimal("1.1080")
        atr_value = 0.0025

        new_stop = manager.calculate_trailing_stop(position, current_price, atr_value)

        # Should trail up for long position
        expected_stop = current_price - Decimal(str(atr_value * manager.atr_multiplier))
        assert new_stop == max(expected_stop, position.stop_loss)

    def test_trailing_stop_not_activated(self):
        """Test trailing stop not activated for small profits."""
        manager = StopLossManager(trailing_activation_pct=0.02)

        # Position with small profit (below activation threshold)
        position = Position(
            position_id="test",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1010"),
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.TRAILING,
            unrealized_pnl=Decimal("10"),  # 1% profit (below 2% threshold)
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        new_stop = manager.calculate_trailing_stop(position, Decimal("1.1010"), 0.0025)

        # Should keep original stop
        assert new_stop == position.stop_loss

    def test_breakeven_stop_calculation(self):
        """Test breakeven stop calculation."""
        manager = StopLossManager(breakeven_trigger_pct=0.015)

        # Position with sufficient profit for breakeven
        position = Position(
            position_id="test",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1020"),
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.BREAKEVEN,
            unrealized_pnl=Decimal("20"),  # 2% profit (above 1.5% threshold)
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        breakeven_stop = manager.calculate_breakeven_stop(position)

        assert breakeven_stop == position.entry_price

    def test_breakeven_stop_not_triggered(self):
        """Test breakeven stop not triggered for small profits."""
        manager = StopLossManager(breakeven_trigger_pct=0.015)

        # Position with insufficient profit
        position = Position(
            position_id="test",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1005"),
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.BREAKEVEN,
            unrealized_pnl=Decimal("5"),  # 0.5% profit (below 1.5% threshold)
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        breakeven_stop = manager.calculate_breakeven_stop(position)

        assert breakeven_stop is None


class TestRiskManager:
    """Test comprehensive risk manager."""

    def test_trade_approval_normal_conditions(self):
        """Test trade approval under normal conditions."""
        risk_manager = RiskManager()

        # Use very conservative parameters that should definitely be approved
        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0500"),  # Much larger stop distance (500 pips)
            confidence=0.3,  # Very low confidence for minimal position
            portfolio_value=Decimal("1000000"),  # Large portfolio
            available_margin=Decimal("500000"),  # Lots of margin
            leverage=1.0  # No leverage
        )


        assert assessment.approved
        assert assessment.safe_mode_status == SafeMode.NORMAL

    def test_trade_rejection_high_risk(self):
        """Test trade rejection for high risk."""
        risk_manager = RiskManager()

        # Create new risk limits with tight constraints
        risk_manager.risk_limits = RiskLimits(max_risk_per_trade=0.005)  # 0.5%

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0900"),  # Large stop distance
            confidence=1.0,  # High confidence = high risk
            portfolio_value=Decimal("100000"),
            available_margin=Decimal("50000"),
            leverage=3.0
        )

        assert not assessment.approved
        assert "Risk" in assessment.risk_factors[0]

    def test_trade_rejection_emergency_mode(self):
        """Test trade rejection in emergency mode."""
        risk_manager = RiskManager()

        # Set emergency mode
        risk_manager.drawdown_protection.current_safe_mode = SafeMode.EMERGENCY

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=Decimal("100000"),
            available_margin=Decimal("50000"),
            leverage=3.0
        )

        assert not assessment.approved
        assert assessment.risk_score == 100.0
        assert "Emergency safe mode" in assessment.risk_factors[0]

    def test_trade_rejection_high_leverage(self):
        """Test trade rejection for excessive leverage."""
        risk_manager = RiskManager()

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=Decimal("100000"),
            available_margin=Decimal("50000"),
            leverage=15.0  # Exceeds 10x limit
        )

        assert not assessment.approved
        assert "Leverage" in assessment.risk_factors[0]

    def test_trade_rejection_insufficient_margin(self):
        """Test trade rejection for insufficient margin."""
        risk_manager = RiskManager()

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=Decimal("100000"),
            available_margin=Decimal("1000"),  # Very low margin
            leverage=10.0
        )

        assert not assessment.approved
        assert "Margin utilization" in assessment.risk_factors[0]

    def test_position_management(self):
        """Test position addition and removal."""
        risk_manager = RiskManager()

        position = Position(
            position_id="test1",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1050"),
            stop_loss=Decimal("1.0950"),
            unrealized_pnl=Decimal("50"),
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        # Add position
        risk_manager.add_position(position)
        assert len(risk_manager.current_positions) == 1

        # Remove position
        risk_manager.remove_position("test1")
        assert len(risk_manager.current_positions) == 0

    def test_portfolio_metrics_update(self):
        """Test portfolio metrics update and drawdown checking."""
        risk_manager = RiskManager()

        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal("-5000"),
            daily_pnl=Decimal("-8000"),
            monthly_pnl=Decimal("-15000"),
            daily_drawdown=0.08,  # At limit
            monthly_drawdown=0.15,
            max_drawdown=0.20,
            win_rate=0.55,
            sharpe_ratio=1.0,
            total_trades=100,
            open_positions=3
        )

        risk_manager.update_portfolio_metrics(metrics)

        assert risk_manager.portfolio_metrics == metrics
        assert risk_manager.drawdown_protection.current_safe_mode == SafeMode.SAFE_MODE

    def test_stop_loss_updates(self):
        """Test stop loss updates for positions."""
        risk_manager = RiskManager()

        position = Position(
            position_id="test1",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1050"),
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.ATR_BASED,
            unrealized_pnl=Decimal("50"),
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        risk_manager.add_position(position)

        # Update stops
        risk_manager.update_position_stops("EURUSD", Decimal("1.1080"), 0.0025)

        # Stop should be updated
        updated_position = risk_manager.current_positions[0]
        assert updated_position.stop_loss != Decimal("1.0950")

    def test_risk_summary(self):
        """Test risk summary generation."""
        risk_manager = RiskManager()

        # Set up portfolio metrics
        metrics = PortfolioMetrics(
            total_equity=Decimal("100000"),
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal("2000"),
            daily_pnl=Decimal("1000"),
            monthly_pnl=Decimal("5000"),
            daily_drawdown=0.02,
            monthly_drawdown=0.05,
            max_drawdown=0.10,
            win_rate=0.65,
            sharpe_ratio=1.2,
            total_trades=100,
            open_positions=2
        )

        risk_manager.update_portfolio_metrics(metrics)

        summary = risk_manager.get_risk_summary()

        assert "safe_mode" in summary
        assert "daily_drawdown" in summary
        assert "monthly_drawdown" in summary
        assert "portfolio_risk" in summary
        assert "open_positions" in summary
        assert summary["open_positions"] == 0  # No positions added yet


class TestPropertyBasedRiskManagement:
    """Property-based tests for risk management invariants."""

    def test_position_size_never_negative(self):
        """Test that position sizes are never negative."""
        sizer = PositionSizer()

        test_cases = [
            (Decimal("100000"), Decimal("100"), Decimal("95"), 0.5, 1.0),
            (Decimal("50000"), Decimal("50"), Decimal("48"), 0.8, 2.0),
            (Decimal("200000"), Decimal("200"), Decimal("190"), 0.3, 3.0),
        ]

        for portfolio, entry, stop, confidence, leverage in test_cases:
            position_size, risk_pct = sizer.calculate_position_size(
                portfolio, entry, stop, confidence, leverage
            )

            assert position_size > 0
            assert risk_pct > 0

    def test_risk_percentage_bounds_invariant(self):
        """Test that risk percentage always stays within bounds."""
        sizer = PositionSizer()

        # Test with various confidence levels
        for confidence in [0.0, 0.25, 0.5, 0.75, 1.0]:
            _, risk_pct = sizer.calculate_position_size(
                Decimal("100000"), Decimal("100"), Decimal("95"), confidence, 1.0
            )

            assert 0.0025 <= risk_pct <= 0.02  # 0.25% to 2%

    def test_leverage_constraint_invariant(self):
        """Test that leverage constraints are always enforced."""
        risk_manager = RiskManager()

        # Test various leverage levels
        for leverage in [1.0, 3.0, 5.0, 10.0, 15.0, 20.0]:
            assessment = risk_manager.assess_trade_risk(
                symbol="EURUSD",
                direction=Direction.LONG,
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0950"),
                confidence=0.5,
                portfolio_value=Decimal("100000"),
                available_margin=Decimal("50000"),
                leverage=leverage
            )

            if leverage > 10.0:
                assert not assessment.approved
                assert any("Leverage" in factor for factor in assessment.risk_factors)
            else:
                # May still be rejected for other reasons, but not leverage
                if not assessment.approved:
                    assert not any("Leverage" in factor for factor in assessment.risk_factors)

    def test_safe_mode_position_reduction_invariant(self):
        """Test that safe mode always reduces position sizes."""
        protection = DrawdownProtection()

        normal_adjustment = protection.get_position_size_adjustment()

        protection.current_safe_mode = SafeMode.CAUTION
        caution_adjustment = protection.get_position_size_adjustment()

        protection.current_safe_mode = SafeMode.SAFE_MODE
        safe_adjustment = protection.get_position_size_adjustment()

        protection.current_safe_mode = SafeMode.EMERGENCY
        emergency_adjustment = protection.get_position_size_adjustment()

        # Each mode should reduce position size more than the previous
        assert normal_adjustment >= caution_adjustment
        assert caution_adjustment >= safe_adjustment
        assert safe_adjustment >= emergency_adjustment
        assert emergency_adjustment == 0.0

    def test_correlation_exposure_invariant(self):
        """Test that correlation exposure limits are never exceeded."""
        monitor = CorrelationMonitor(max_correlated_exposure=0.15)

        # Set up high correlation
        monitor.update_correlation("EURUSD", "GBPUSD", 0.9)

        # Create position that uses most of the correlation budget
        existing_positions = [
            Position(
                position_id="1",
                symbol="GBPUSD",
                direction=Direction.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.30"),
                current_price=Decimal("1.31"),
                stop_loss=Decimal("1.28"),
                unrealized_pnl=Decimal("10"),
                initial_risk=Decimal("20"),
                current_risk=Decimal("20"),
                opened_at=datetime.utcnow()
            )
        ]

        portfolio_value = Decimal("100000")

        # Test various new position sizes
        for new_position_pct in [0.05, 0.10, 0.15, 0.20, 0.25]:
            new_position_value = portfolio_value * Decimal(str(new_position_pct))

            allowed, _ = monitor.check_correlation_limits(
                "EURUSD", new_position_value, existing_positions, portfolio_value
            )

            # Calculate total correlated exposure
            existing_value = existing_positions[0].calculate_position_value()
            total_exposure = float((existing_value + new_position_value) / portfolio_value)

            if total_exposure > monitor.max_correlated_exposure:
                assert not allowed
            # Note: May still be rejected due to other factors even if under limit


class TestChaosAndPropertyBased:
    """Chaos testing and additional property-based tests for risk management."""

    def test_atr_stop_properties(self):
        """Property-based test for ATR stop calculations."""
        manager = StopLossManager()

        # Test various ATR values and multipliers
        test_cases = [
            (Decimal("100"), 2.0, 2.0),
            (Decimal("50"), 1.5, 1.5),
            (Decimal("200"), 3.0, 2.5),
            (Decimal("75"), 0.5, 3.0),
        ]

        for entry_price, atr_value, multiplier in test_cases:
            # Long position stop should always be below entry
            long_stop = manager.calculate_atr_stop(entry_price, Direction.LONG, atr_value, multiplier)
            assert long_stop < entry_price, f"Long stop {long_stop} should be below entry {entry_price}"

            # Short position stop should always be above entry
            short_stop = manager.calculate_atr_stop(entry_price, Direction.SHORT, atr_value, multiplier)
            assert short_stop > entry_price, f"Short stop {short_stop} should be above entry {entry_price}"

            # Stop distance should equal ATR * multiplier
            expected_distance = Decimal(str(atr_value * multiplier))
            long_distance = entry_price - long_stop
            short_distance = short_stop - entry_price

            assert abs(long_distance - expected_distance) < Decimal("0.0001")
            assert abs(short_distance - expected_distance) < Decimal("0.0001")

    def test_trailing_stop_properties(self):
        """Property-based test for trailing stop behavior."""
        manager = StopLossManager(atr_multiplier=2.0, trailing_activation_pct=0.02)

        # Create profitable long position
        position = Position(
            position_id="trail_test",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1030"),  # 3% profit
            stop_loss=Decimal("1.0950"),
            stop_type=StopType.TRAILING,
            unrealized_pnl=Decimal("30"),
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.utcnow()
        )

        # Test trailing stop only moves in favorable direction
        original_stop = position.stop_loss

        # Price moves up - stop should trail up
        new_stop_up = manager.calculate_trailing_stop(position, Decimal("1.1050"), 0.0025)
        assert new_stop_up >= original_stop, "Trailing stop should only move up for long positions"

        # Price moves down - stop should not move down
        position.stop_loss = new_stop_up  # Update to new stop
        new_stop_down = manager.calculate_trailing_stop(position, Decimal("1.1020"), 0.0025)
        assert new_stop_down >= new_stop_up, "Trailing stop should not move down for long positions"

    def test_breakeven_stop_properties(self):
        """Property-based test for breakeven stop behavior."""
        manager = StopLossManager(breakeven_trigger_pct=0.015)

        # Test with various profit levels
        profit_levels = [0.005, 0.01, 0.015, 0.02, 0.03]  # 0.5% to 3%

        for profit_pct in profit_levels:
            entry_price = Decimal("1.1000")
            current_price = entry_price * (1 + Decimal(str(profit_pct)))
            quantity = Decimal("1000")

            position = Position(
                position_id="be_test",
                symbol="EURUSD",
                direction=Direction.LONG,
                quantity=quantity,
                entry_price=entry_price,
                current_price=current_price,
                stop_loss=Decimal("1.0950"),
                stop_type=StopType.BREAKEVEN,
                unrealized_pnl=Decimal("0"),  # Will be calculated
                initial_risk=Decimal("50"),
                current_risk=Decimal("50"),
                opened_at=datetime.utcnow()
            )

            # Calculate P&L properly
            position.calculate_unrealized_pnl()

            breakeven_stop = manager.calculate_breakeven_stop(position)

            if profit_pct >= manager.breakeven_trigger_pct:
                assert breakeven_stop == position.entry_price, f"Should trigger breakeven at {profit_pct:.1%} profit"
            else:
                assert breakeven_stop is None, f"Should not trigger breakeven at {profit_pct:.1%} profit"

    def test_correlation_blocking_synthetic_suite(self):
        """Synthetic test suite for correlation exposure blocking."""
        monitor = CorrelationMonitor(correlation_threshold=0.7, max_correlated_exposure=0.15)

        # Set up synthetic correlation matrix
        symbols = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD"]
        correlations = {
            ("EURUSD", "GBPUSD"): 0.85,
            ("EURUSD", "AUDUSD"): 0.75,
            ("GBPUSD", "AUDUSD"): 0.80,
            ("AUDUSD", "NZDUSD"): 0.90,
            ("USDCAD", "EURUSD"): -0.65,  # Negative correlation
        }

        # Update correlation matrix
        for (sym1, sym2), corr in correlations.items():
            monitor.update_correlation(sym1, sym2, corr)

        portfolio_value = Decimal("1000000")  # $1M portfolio

        # Create existing positions
        existing_positions = [
            Position(
                position_id="pos1",
                symbol="GBPUSD",
                direction=Direction.LONG,
                quantity=Decimal("50000"),
                entry_price=Decimal("1.3000"),
                current_price=Decimal("1.3000"),
                stop_loss=Decimal("1.2950"),
                unrealized_pnl=Decimal("0"),
                initial_risk=Decimal("2500"),
                current_risk=Decimal("2500"),
                opened_at=datetime.utcnow()
            ),
            Position(
                position_id="pos2",
                symbol="AUDUSD",
                direction=Direction.LONG,
                quantity=Decimal("60000"),
                entry_price=Decimal("0.7500"),
                current_price=Decimal("0.7500"),
                stop_loss=Decimal("0.7450"),
                unrealized_pnl=Decimal("0"),
                initial_risk=Decimal("3000"),
                current_risk=Decimal("3000"),
                opened_at=datetime.utcnow()
            )
        ]

        # Calculate existing exposure
        existing_exposure = sum(pos.calculate_position_value() for pos in existing_positions)
        existing_pct = float(existing_exposure / portfolio_value)

        # Test new EURUSD position (highly correlated with both existing)
        new_position_value = Decimal("100000")  # $100k position

        allowed, violations = monitor.check_correlation_limits(
            "EURUSD", new_position_value, existing_positions, portfolio_value
        )

        # Should be blocked due to high correlation with both positions
        assert not allowed, "Should block EURUSD due to correlation with GBPUSD and AUDUSD"
        assert len(violations) > 0
        assert "exceeding limit" in violations[0]

        # Test USDCAD position (negative correlation - should be allowed)
        allowed_usdcad, violations_usdcad = monitor.check_correlation_limits(
            "USDCAD", new_position_value, existing_positions, portfolio_value
        )

        # Should be allowed due to negative correlation
        assert allowed_usdcad, "Should allow USDCAD due to negative correlation"

    def test_safe_mode_triggers_simulated_drawdown(self):
        """Test SAFE_MODE triggers with simulated drawdown scenarios."""
        protection = DrawdownProtection(daily_limit=0.08, monthly_limit=0.20)

        # Simulate gradual drawdown progression
        drawdown_scenarios = [
            (0.02, 0.05, SafeMode.NORMAL),      # 2% daily, 5% monthly - normal
            (0.05, 0.10, SafeMode.NORMAL),      # 5% daily, 10% monthly - normal
            (0.08, 0.15, SafeMode.SAFE_MODE),   # 8% daily, 15% monthly - safe mode
            (0.10, 0.20, SafeMode.SAFE_MODE),   # 10% daily, 20% monthly - safe mode
            (0.12, 0.25, SafeMode.EMERGENCY),   # 12% daily, 25% monthly - emergency
        ]

        for daily_dd, monthly_dd, expected_mode in drawdown_scenarios:
            metrics = PortfolioMetrics(
                total_equity=Decimal("100000"),
                available_margin=Decimal("50000"),
                used_margin=Decimal("20000"),
                unrealized_pnl=Decimal(str(-100000 * daily_dd)),
                daily_pnl=Decimal(str(-100000 * daily_dd)),
                monthly_pnl=Decimal(str(-100000 * monthly_dd)),
                daily_drawdown=daily_dd,
                monthly_drawdown=monthly_dd,
                max_drawdown=max(daily_dd, monthly_dd),
                win_rate=0.45,
                sharpe_ratio=0.8,
                total_trades=100,
                open_positions=3
            )

            safe_mode, triggers = protection.check_drawdown_limits(metrics)

            assert safe_mode == expected_mode, f"Expected {expected_mode} for {daily_dd:.0%}/{monthly_dd:.0%} drawdown"

            # Verify position size adjustment matches safe mode
            adjustment = protection.get_position_size_adjustment()
            if expected_mode == SafeMode.NORMAL:
                assert adjustment == 1.0
            elif expected_mode == SafeMode.SAFE_MODE:
                assert adjustment == 0.5
            elif expected_mode == SafeMode.EMERGENCY:
                assert adjustment == 0.0

    def test_risk_decision_latency_benchmark(self):
        """Test that risk decisions complete within 2ms target."""
        import time

        risk_manager = RiskManager()
        portfolio_value = Decimal("100000")
        available_margin = Decimal("50000")

        # Add some positions to make it more realistic
        for i in range(5):
            position = Position(
                position_id=f"bench_pos_{i}",
                symbol=f"PAIR{i}",
                direction=Direction.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.0000"),
                current_price=Decimal("1.0010"),
                stop_loss=Decimal("0.9950"),
                unrealized_pnl=Decimal("10"),
                initial_risk=Decimal("50"),
                current_risk=Decimal("50"),
                opened_at=datetime.utcnow()
            )
            risk_manager.add_position(position)

        # Warm up
        for _ in range(10):
            risk_manager.assess_trade_risk(
                symbol="TESTPAIR",
                direction=Direction.LONG,
                entry_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0950"),
                confidence=0.8,
                portfolio_value=portfolio_value,
                available_margin=available_margin,
                leverage=3.0
            )

        # Benchmark
        num_tests = 100
        start_time = time.perf_counter()

        for i in range(num_tests):
            # Vary parameters to avoid caching
            entry_price = Decimal("1.1000") + Decimal(str(i * 0.0001))
            confidence = 0.5 + (i % 50) * 0.01

            assessment = risk_manager.assess_trade_risk(
                symbol="TESTPAIR",
                direction=Direction.LONG,
                entry_price=entry_price,
                stop_loss=Decimal("1.0950"),
                confidence=confidence,
                portfolio_value=portfolio_value,
                available_margin=available_margin,
                leverage=3.0
            )

        end_time = time.perf_counter()
        avg_time_ms = ((end_time - start_time) / num_tests) * 1000

        # Assert latency target
        assert avg_time_ms <= 2.0, f"Risk decision latency {avg_time_ms:.3f}ms exceeds 2ms target"

    def test_no_position_exceeds_limits_chaos(self):
        """Chaos test ensuring no position ever exceeds risk limits."""
        import random

        risk_manager = RiskManager()
        portfolio_value = Decimal("100000")
        available_margin = Decimal("50000")

        # Set strict limits for chaos testing
        risk_manager.risk_limits.max_risk_per_trade = 0.01  # 1%
        risk_manager.risk_limits.max_portfolio_risk = 0.15  # 15%
        risk_manager.risk_limits.max_leverage = 5.0

        # Simulate chaotic market conditions
        random.seed(42)  # Reproducible chaos

        approved_trades = []
        rejected_trades = []

        # Generate 1000 random trade scenarios
        for i in range(1000):
            # Random parameters
            symbol = f"CHAOS{i % 20}"  # 20 different symbols
            direction = random.choice([Direction.LONG, Direction.SHORT])
            entry_price = Decimal(str(random.uniform(0.5, 200.0)))
            stop_distance_pct = random.uniform(0.01, 0.10)  # 1-10% stop distance
            stop_loss = entry_price * (1 - Decimal(str(stop_distance_pct))) if direction == Direction.LONG else entry_price * (1 + Decimal(str(stop_distance_pct)))
            confidence = random.uniform(0.1, 1.0)
            leverage = random.uniform(1.0, 15.0)  # Some will exceed limits

            assessment = risk_manager.assess_trade_risk(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                confidence=confidence,
                portfolio_value=portfolio_value,
                available_margin=available_margin,
                leverage=leverage
            )

            if assessment.approved:
                approved_trades.append(assessment)

                # Verify approved trade respects all limits
                assert assessment.position_risk_pct <= risk_manager.risk_limits.max_risk_per_trade * 100
                assert assessment.portfolio_risk_pct <= risk_manager.risk_limits.max_portfolio_risk * 100
                assert assessment.leverage_used <= risk_manager.risk_limits.max_leverage
                assert assessment.margin_utilization <= 90.0  # Margin limit

            else:
                rejected_trades.append(assessment)

        # Verify we had both approvals and rejections (system is working)
        assert len(approved_trades) > 0, "Should have some approved trades"
        assert len(rejected_trades) > 0, "Should have some rejected trades"

        # Verify all approved trades are within limits
        for trade in approved_trades:
            assert trade.position_risk_pct <= 1.0, f"Position risk {trade.position_risk_pct:.2f}% exceeds 1% limit"
            assert trade.portfolio_risk_pct <= 15.0, f"Portfolio risk {trade.portfolio_risk_pct:.2f}% exceeds 15% limit"
            assert trade.leverage_used <= 5.0, f"Leverage {trade.leverage_used}x exceeds 5x limit"

        print(f"Chaos test completed: {len(approved_trades)} approved, {len(rejected_trades)} rejected")

    def test_portfolio_consistency_invariant(self):
        """Test that portfolio calculations remain consistent under all operations."""
        risk_manager = RiskManager()
        portfolio_value = Decimal("100000")

        # Add positions and verify portfolio consistency
        positions = []
        total_risk = Decimal("0")

        for i in range(10):
            position = Position(
                position_id=f"consist_pos_{i}",
                symbol=f"PAIR{i}",
                direction=Direction.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.0000"),
                current_price=Decimal("1.0010"),
                stop_loss=Decimal("0.9950"),
                unrealized_pnl=Decimal("10"),
                initial_risk=Decimal("50"),
                current_risk=Decimal("50"),
                opened_at=datetime.utcnow()
            )

            risk_manager.add_position(position)
            positions.append(position)
            total_risk += position.current_risk

            # Verify portfolio risk calculation is consistent
            calculated_risk = risk_manager._calculate_current_portfolio_risk(portfolio_value)
            expected_risk = float(total_risk / portfolio_value)

            assert abs(calculated_risk - expected_risk) < 0.0001, f"Portfolio risk calculation inconsistent: {calculated_risk} vs {expected_risk}"

        # Remove positions and verify consistency
        for position in positions[:5]:  # Remove half
            risk_manager.remove_position(position.position_id)
            total_risk -= position.current_risk

            calculated_risk = risk_manager._calculate_current_portfolio_risk(portfolio_value)
            expected_risk = float(total_risk / portfolio_value)

            assert abs(calculated_risk - expected_risk) < 0.0001, f"Portfolio risk calculation inconsistent after removal: {calculated_risk} vs {expected_risk}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
