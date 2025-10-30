"""
Unit tests for Emergency Circuit Breaker system.
"""

from datetime import UTC, datetime, timedelta

import pytest

from libs.trading_models.emergency_circuit_breaker import (
    EmergencyCircuitBreaker,
    SystemState,
    TriggeredCondition,
)
from libs.trading_models.live_trading_config import (
    DEFAULT_EMERGENCY_TRIGGERS,
    EmergencyAction,
    EmergencyTrigger,
)


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker instance for testing."""
    return EmergencyCircuitBreaker(DEFAULT_EMERGENCY_TRIGGERS.copy())


@pytest.fixture
def normal_state():
    """Create a normal system state."""
    return SystemState(
        current_drawdown=0.01,  # 1%
        daily_loss=0.005,  # 0.5%
        api_latency_ms=500,  # 0.5 seconds
        position_correlation=0.3,  # 30%
        total_exposure=0.05,  # 5%
        open_positions=2,
        last_trade_time=datetime.now(UTC),
        system_health="healthy"
    )


@pytest.fixture
def critical_state():
    """Create a critical system state."""
    return SystemState(
        current_drawdown=0.05,  # 5%
        daily_loss=0.02,  # 2%
        api_latency_ms=3000,  # 3 seconds
        position_correlation=0.8,  # 80%
        total_exposure=0.15,  # 15%
        open_positions=5,
        last_trade_time=datetime.now(UTC),
        system_health="critical"
    )


class TestEmergencyCircuitBreaker:
    """Test suite for EmergencyCircuitBreaker class."""

    def test_initialization(self, circuit_breaker):
        """Test circuit breaker initialization."""
        assert len(circuit_breaker.triggers) == 5
        assert not circuit_breaker.emergency_active
        assert len(circuit_breaker.active_cooldowns) == 0
        assert len(circuit_breaker.trigger_history) == 0

    def test_register_trigger(self, circuit_breaker):
        """Test registering a new trigger."""
        new_trigger = EmergencyTrigger(
            condition="test_condition",
            threshold=0.5,
            action=EmergencyAction.HALT_NEW_TRADES,
            cooldown_hours=2
        )

        circuit_breaker.register_trigger(new_trigger)
        assert "test_condition" in circuit_breaker.triggers
        assert circuit_breaker.triggers["test_condition"].threshold == 0.5

    def test_register_disabled_trigger(self, circuit_breaker):
        """Test that disabled triggers are not registered."""
        disabled_trigger = EmergencyTrigger(
            condition="disabled_test",
            threshold=0.5,
            action=EmergencyAction.HALT_NEW_TRADES,
            cooldown_hours=2,
            enabled=False
        )

        initial_count = len(circuit_breaker.triggers)
        circuit_breaker.register_trigger(disabled_trigger)
        assert len(circuit_breaker.triggers) == initial_count

    def test_unregister_trigger(self, circuit_breaker):
        """Test unregistering a trigger."""
        assert circuit_breaker.unregister_trigger("daily_loss_exceeded")
        assert "daily_loss_exceeded" not in circuit_breaker.triggers
        assert not circuit_breaker.unregister_trigger("nonexistent")

    def test_check_triggers_normal_state(self, circuit_breaker, normal_state):
        """Test trigger checking with normal state."""
        triggered = circuit_breaker.check_triggers(normal_state)
        assert len(triggered) == 0

    def test_check_triggers_daily_loss_exceeded(self, circuit_breaker):
        """Test daily loss trigger."""
        state = SystemState(
            current_drawdown=0.005,
            daily_loss=0.015,  # 1.5% - exceeds 1% threshold
            api_latency_ms=500,
            position_correlation=0.3,
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="warning"
        )

        triggered = circuit_breaker.check_triggers(state)
        assert len(triggered) == 1
        assert triggered[0].trigger.condition == "daily_loss_exceeded"
        assert triggered[0].current_value >= 0.01

    def test_check_triggers_drawdown_exceeded(self, circuit_breaker):
        """Test drawdown trigger."""
        state = SystemState(
            current_drawdown=0.04,  # 4% - exceeds 3% threshold
            daily_loss=0.005,
            api_latency_ms=500,
            position_correlation=0.3,
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="warning"
        )

        triggered = circuit_breaker.check_triggers(state)
        assert len(triggered) == 1
        assert triggered[0].trigger.condition == "drawdown_exceeded"

    def test_check_triggers_api_latency_high(self, circuit_breaker):
        """Test API latency trigger."""
        state = SystemState(
            current_drawdown=0.01,
            daily_loss=0.005,
            api_latency_ms=2500,  # 2.5 seconds - exceeds 2.0 threshold
            position_correlation=0.3,
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="degraded"
        )

        triggered = circuit_breaker.check_triggers(state)
        assert len(triggered) == 1
        assert triggered[0].trigger.condition == "api_latency_high"

    def test_check_triggers_correlation_breach(self, circuit_breaker):
        """Test correlation trigger."""
        state = SystemState(
            current_drawdown=0.01,
            daily_loss=0.005,
            api_latency_ms=500,
            position_correlation=0.75,  # 75% - exceeds 70% threshold
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="warning"
        )

        triggered = circuit_breaker.check_triggers(state)
        assert len(triggered) == 1
        assert triggered[0].trigger.condition == "correlation_breach"

    def test_check_triggers_multiple_conditions(self, circuit_breaker, critical_state):
        """Test multiple triggers at once."""
        triggered = circuit_breaker.check_triggers(critical_state)
        assert len(triggered) >= 2  # Multiple conditions should trigger

    def test_cooldown_prevents_retrigger(self, circuit_breaker):
        """Test that cooldown prevents immediate retriggering."""
        state = SystemState(
            current_drawdown=0.01,
            daily_loss=0.015,  # Exceeds threshold
            api_latency_ms=500,
            position_correlation=0.3,
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="warning"
        )

        # First check should trigger
        triggered1 = circuit_breaker.check_triggers(state)
        assert len(triggered1) == 1

        # Set cooldown
        circuit_breaker.enter_cooldown("daily_loss_exceeded", timedelta(hours=1))

        # Second check should not trigger due to cooldown
        triggered2 = circuit_breaker.check_triggers(state)
        assert len(triggered2) == 0

    def test_execute_emergency_stop(self, circuit_breaker):
        """Test emergency stop execution."""
        response = circuit_breaker.execute_emergency_stop("Test emergency")

        assert circuit_breaker.emergency_active
        assert response.trigger_reason == "Test emergency"
        assert len(response.actions_taken) > 0
        assert len(response.recovery_steps) > 0
        assert response.cooldown_until > datetime.now(UTC)

    def test_execute_emergency_stop_with_triggers(self, circuit_breaker, critical_state):
        """Test emergency stop with triggered conditions."""
        triggered = circuit_breaker.check_triggers(critical_state)

        # Store current time before executing stop
        time_before = datetime.now(UTC)

        response = circuit_breaker.execute_emergency_stop(
            "Multiple triggers activated",
            triggered
        )

        assert circuit_breaker.emergency_active
        assert len(response.actions_taken) >= len(triggered)
        assert response.cooldown_until >= time_before

    def test_enter_cooldown(self, circuit_breaker):
        """Test manual cooldown entry."""
        duration = timedelta(hours=2)
        circuit_breaker.enter_cooldown("test_condition", duration)

        assert "test_condition" in circuit_breaker.active_cooldowns
        cooldown_until = circuit_breaker.active_cooldowns["test_condition"]
        assert cooldown_until > datetime.now(UTC)

    def test_clear_cooldown(self, circuit_breaker):
        """Test cooldown clearing."""
        circuit_breaker.enter_cooldown("test_condition", timedelta(hours=1))
        assert circuit_breaker.clear_cooldown("test_condition")
        assert "test_condition" not in circuit_breaker.active_cooldowns
        assert not circuit_breaker.clear_cooldown("nonexistent")

    def test_clear_all_cooldowns(self, circuit_breaker):
        """Test clearing all cooldowns."""
        circuit_breaker.enter_cooldown("condition1", timedelta(hours=1))
        circuit_breaker.enter_cooldown("condition2", timedelta(hours=2))

        circuit_breaker.clear_all_cooldowns()
        assert len(circuit_breaker.active_cooldowns) == 0

    def test_reset_emergency_state(self, circuit_breaker):
        """Test emergency state reset."""
        circuit_breaker.execute_emergency_stop("Test")
        assert circuit_breaker.emergency_active

        circuit_breaker.reset_emergency_state()
        assert not circuit_breaker.emergency_active

    def test_get_status(self, circuit_breaker):
        """Test status retrieval."""
        status = circuit_breaker.get_status()

        assert "emergency_active" in status
        assert "active_triggers" in status
        assert "active_cooldowns" in status
        assert "trigger_history_count" in status
        assert status["active_triggers"] == 5

    def test_get_trigger_history(self, circuit_breaker, critical_state):
        """Test trigger history retrieval."""
        # Generate some history
        circuit_breaker.check_triggers(critical_state)

        history = circuit_breaker.get_trigger_history()
        assert len(history) > 0
        assert all(isinstance(t, TriggeredCondition) for t in history)

    def test_get_trigger_history_with_severity_filter(self, circuit_breaker):
        """Test trigger history with severity filter."""
        # Create a critical state to generate critical triggers
        state = SystemState(
            current_drawdown=0.06,  # 6% - well above 3% threshold
            daily_loss=0.02,
            api_latency_ms=500,
            position_correlation=0.3,
            total_exposure=0.05,
            open_positions=2,
            last_trade_time=datetime.now(UTC),
            system_health="critical"
        )

        circuit_breaker.check_triggers(state)

        critical_history = circuit_breaker.get_trigger_history(severity="critical")
        assert all(t.severity == "critical" for t in critical_history)

    def test_trigger_history_limit(self, circuit_breaker):
        """Test trigger history limit."""
        # Generate multiple triggers
        for i in range(10):
            state = SystemState(
                current_drawdown=0.04,
                daily_loss=0.015,
                api_latency_ms=500,
                position_correlation=0.3,
                total_exposure=0.05,
                open_positions=2,
                last_trade_time=datetime.now(UTC),
                system_health="warning"
            )
            circuit_breaker.check_triggers(state)
            circuit_breaker.clear_all_cooldowns()  # Allow retriggering

        history = circuit_breaker.get_trigger_history(limit=5)
        assert len(history) <= 5


class TestTriggeredCondition:
    """Test suite for TriggeredCondition class."""

    def test_triggered_condition_creation(self):
        """Test creating a triggered condition."""
        trigger = EmergencyTrigger(
            condition="test",
            threshold=0.5,
            action=EmergencyAction.HALT_NEW_TRADES,
            cooldown_hours=1
        )

        condition = TriggeredCondition(
            trigger=trigger,
            current_value=0.6,
            threshold=0.5,
            timestamp=datetime.now(UTC),
            severity="warning"
        )

        assert condition.current_value == 0.6
        assert condition.threshold == 0.5
        assert condition.severity == "warning"

    def test_invalid_severity(self):
        """Test that invalid severity raises error."""
        trigger = EmergencyTrigger(
            condition="test",
            threshold=0.5,
            action=EmergencyAction.HALT_NEW_TRADES,
            cooldown_hours=1
        )

        with pytest.raises(ValueError, match="Severity must be"):
            TriggeredCondition(
                trigger=trigger,
                current_value=0.6,
                threshold=0.5,
                timestamp=datetime.now(UTC),
                severity="invalid"
            )


class TestSystemState:
    """Test suite for SystemState class."""

    def test_system_state_creation(self):
        """Test creating a system state."""
        state = SystemState(
            current_drawdown=0.02,
            daily_loss=0.01,
            api_latency_ms=1000,
            position_correlation=0.5,
            total_exposure=0.1,
            open_positions=3,
            last_trade_time=datetime.now(UTC),
            system_health="healthy"
        )

        assert state.current_drawdown == 0.02
        assert state.daily_loss == 0.01
        assert state.system_health == "healthy"
        assert state.timestamp is not None
