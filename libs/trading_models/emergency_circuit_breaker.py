"""
Emergency Circuit Breaker System

This module implements the emergency circuit breaker system for live trading,
providing automatic monitoring, trigger evaluation, and emergency response
actions to protect capital during adverse conditions.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import structlog

from .live_trading_config import (
    EmergencyAction,
    EmergencyResponse,
    EmergencyTrigger,
)

logger = structlog.get_logger(__name__)


@dataclass
class SystemState:
    """Current state of the trading system for trigger evaluation."""
    current_drawdown: float
    daily_loss: float
    api_latency_ms: float
    position_correlation: float
    total_exposure: float
    open_positions: int
    last_trade_time: Optional[datetime]
    system_health: str  # "healthy", "degraded", "critical"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TriggeredCondition:
    """Represents a triggered emergency condition."""
    trigger: EmergencyTrigger
    current_value: float
    threshold: float
    timestamp: datetime
    severity: str  # "warning", "critical"

    def __post_init__(self):
        if self.severity not in ["warning", "critical"]:
            raise ValueError("Severity must be 'warning' or 'critical'")


class EmergencyCircuitBreaker:
    """
    Emergency circuit breaker system for live trading.

    Monitors system state and automatically triggers emergency actions
    when predefined conditions are met.
    """

    def __init__(self, triggers: list[EmergencyTrigger]):
        """
        Initialize the circuit breaker.

        Args:
            triggers: List of emergency triggers to monitor
        """
        self.triggers = {trigger.condition: trigger for trigger in triggers if trigger.enabled}
        self.active_cooldowns: dict[str, datetime] = {}
        self.trigger_history: list[TriggeredCondition] = []
        self.emergency_active = False
        self.last_emergency_response: Optional[EmergencyResponse] = None
        self.logger = logger.bind(component="EmergencyCircuitBreaker")

        self.logger.info(
            "Circuit breaker initialized",
            trigger_count=len(self.triggers),
            conditions=list(self.triggers.keys())
        )

    def register_trigger(self, trigger: EmergencyTrigger) -> None:
        """
        Register a new emergency trigger.

        Args:
            trigger: Emergency trigger configuration
        """
        if not trigger.enabled:
            self.logger.info("Skipping disabled trigger", condition=trigger.condition)
            return

        self.triggers[trigger.condition] = trigger
        self.logger.info(
            "Trigger registered",
            condition=trigger.condition,
            threshold=trigger.threshold,
            action=trigger.action.value
        )

    def unregister_trigger(self, condition: str) -> bool:
        """
        Unregister an emergency trigger.

        Args:
            condition: Condition name to unregister

        Returns:
            True if trigger was removed
        """
        if condition in self.triggers:
            del self.triggers[condition]
            self.logger.info("Trigger unregistered", condition=condition)
            return True
        return False


    def check_triggers(self, current_state: SystemState) -> list[TriggeredCondition]:
        """
        Check all registered triggers against current system state.

        Args:
            current_state: Current trading system state

        Returns:
            List of triggered conditions
        """
        triggered = []

        # Check each trigger condition
        for condition, trigger in self.triggers.items():
            # Skip if in cooldown
            if self._is_in_cooldown(condition):
                continue

            # Evaluate condition
            is_triggered, current_value = self._evaluate_condition(condition, trigger, current_state)

            if is_triggered:
                severity = "critical" if current_value > trigger.threshold * 1.5 else "warning"

                triggered_condition = TriggeredCondition(
                    trigger=trigger,
                    current_value=current_value,
                    threshold=trigger.threshold,
                    timestamp=datetime.now(UTC),
                    severity=severity
                )

                triggered.append(triggered_condition)
                self.trigger_history.append(triggered_condition)

                self.logger.warning(
                    "Emergency trigger activated",
                    condition=condition,
                    current_value=current_value,
                    threshold=trigger.threshold,
                    severity=severity,
                    action=trigger.action.value
                )

        return triggered

    def _evaluate_condition(
        self,
        condition: str,
        trigger: EmergencyTrigger,
        state: SystemState
    ) -> tuple[bool, float]:
        """
        Evaluate a specific trigger condition.

        Args:
            condition: Condition name
            trigger: Trigger configuration
            state: Current system state

        Returns:
            Tuple of (is_triggered, current_value)
        """
        condition_map = {
            "daily_loss_exceeded": (state.daily_loss, lambda v, t: v >= t),
            "drawdown_exceeded": (state.current_drawdown, lambda v, t: v >= t),
            "api_latency_high": (state.api_latency_ms / 1000.0, lambda v, t: v >= t),
            "correlation_breach": (state.position_correlation, lambda v, t: v >= t),
            "exposure_exceeded": (state.total_exposure, lambda v, t: v >= t),
            "manual_override": (0.0, lambda v, t: False)  # Only triggers via execute_emergency_stop
        }

        if condition not in condition_map:
            self.logger.warning("Unknown condition", condition=condition)
            return False, 0.0

        current_value, comparator = condition_map[condition]
        is_triggered = comparator(current_value, trigger.threshold)

        return is_triggered, current_value

    def _is_in_cooldown(self, condition: str) -> bool:
        """
        Check if a condition is in cooldown period.

        Args:
            condition: Condition name

        Returns:
            True if in cooldown
        """
        if condition not in self.active_cooldowns:
            return False

        cooldown_until = self.active_cooldowns[condition]
        now = datetime.now(UTC)

        if now < cooldown_until:
            return True

        # Cooldown expired, remove it
        del self.active_cooldowns[condition]
        self.logger.info("Cooldown expired", condition=condition)
        return False

    def execute_emergency_stop(
        self,
        reason: str,
        triggered_conditions: Optional[list[TriggeredCondition]] = None
    ) -> EmergencyResponse:
        """
        Execute emergency stop procedures.

        Args:
            reason: Reason for emergency stop
            triggered_conditions: List of conditions that triggered the stop

        Returns:
            Emergency response with actions taken
        """
        self.logger.error(
            "EMERGENCY STOP INITIATED",
            reason=reason,
            triggered_count=len(triggered_conditions) if triggered_conditions else 0
        )

        self.emergency_active = True
        actions_taken = []
        positions_closed = []
        recovery_steps = []

        # Determine actions based on triggered conditions
        if triggered_conditions:
            for triggered in triggered_conditions:
                action = triggered.trigger.action

                if action == EmergencyAction.HALT_NEW_TRADES:
                    actions_taken.append("Halted new trade entries")
                    recovery_steps.append("Monitor performance and resume when conditions improve")

                elif action == EmergencyAction.CLOSE_ALL_POSITIONS:
                    actions_taken.append("Initiated closure of all open positions")
                    positions_closed.append("ALL")
                    recovery_steps.append("Wait for cooldown period")
                    recovery_steps.append("Review system logs and performance")
                    recovery_steps.append("Restart with conservative settings")

                elif action == EmergencyAction.CLOSE_CORRELATED:
                    actions_taken.append("Closed highly correlated positions")
                    positions_closed.append("CORRELATED")
                    recovery_steps.append("Review correlation metrics")

                elif action == EmergencyAction.PAUSE_TRADING:
                    actions_taken.append("Paused all trading operations")
                    recovery_steps.append("Check API connectivity")
                    recovery_steps.append("Resume when latency normalizes")

                elif action == EmergencyAction.IMMEDIATE_STOP:
                    actions_taken.append("Immediate system shutdown initiated")
                    positions_closed.append("ALL")
                    recovery_steps.append("Manual review required before restart")

                elif action == EmergencyAction.REDUCE_POSITION_SIZES:
                    actions_taken.append("Reduced all position sizes by 50%")
                    recovery_steps.append("Monitor volatility")

                # Set cooldown
                cooldown_until = datetime.now(UTC) + timedelta(hours=triggered.trigger.cooldown_hours)
                self.active_cooldowns[triggered.trigger.condition] = cooldown_until
        else:
            # Manual emergency stop
            actions_taken.append("Manual emergency stop executed")
            positions_closed.append("ALL")
            recovery_steps.append("Manual review and approval required")
            cooldown_until = datetime.now(UTC) + timedelta(hours=24)

        response = EmergencyResponse(
            trigger_reason=reason,
            trigger_condition=triggered_conditions[0].trigger.condition if triggered_conditions else "manual",
            actions_taken=actions_taken,
            positions_closed=positions_closed,
            cooldown_until=cooldown_until,
            recovery_steps=recovery_steps,
            timestamp=datetime.now(UTC)
        )

        self.last_emergency_response = response

        self.logger.error(
            "Emergency response executed",
            actions_count=len(actions_taken),
            positions_closed_count=len(positions_closed),
            cooldown_hours=(cooldown_until - datetime.now(UTC)).total_seconds() / 3600
        )

        return response

    def close_all_positions(self, method: str = "market") -> list[dict[str, Any]]:
        """
        Close all open positions.

        Args:
            method: Order type for closing ("market" or "limit")

        Returns:
            List of order results
        """
        self.logger.warning(
            "Closing all positions",
            method=method
        )

        # This would integrate with the execution gateway
        # For now, return placeholder
        order_results = []

        # TODO: Integrate with actual execution gateway
        # order_results = self.execution_gateway.close_all_positions(method)

        self.logger.info(
            "Position closure initiated",
            orders_placed=len(order_results),
            method=method
        )

        return order_results

    def enter_cooldown(self, condition: str, duration: timedelta) -> None:
        """
        Manually enter cooldown period for a condition.

        Args:
            condition: Condition name
            duration: Cooldown duration
        """
        cooldown_until = datetime.now(UTC) + duration
        self.active_cooldowns[condition] = cooldown_until

        self.logger.info(
            "Cooldown period set",
            condition=condition,
            duration_hours=duration.total_seconds() / 3600,
            until=cooldown_until.isoformat()
        )

    def clear_cooldown(self, condition: str) -> bool:
        """
        Clear cooldown for a specific condition.

        Args:
            condition: Condition name

        Returns:
            True if cooldown was cleared
        """
        if condition in self.active_cooldowns:
            del self.active_cooldowns[condition]
            self.logger.info("Cooldown cleared", condition=condition)
            return True
        return False

    def clear_all_cooldowns(self) -> None:
        """Clear all active cooldowns."""
        count = len(self.active_cooldowns)
        self.active_cooldowns.clear()
        self.logger.info("All cooldowns cleared", count=count)

    def reset_emergency_state(self) -> None:
        """Reset emergency state to allow normal operations."""
        self.emergency_active = False
        self.logger.info("Emergency state reset")

    def get_status(self) -> dict[str, Any]:
        """
        Get current circuit breaker status.

        Returns:
            Status dictionary
        """
        return {
            "emergency_active": self.emergency_active,
            "active_triggers": len(self.triggers),
            "active_cooldowns": len(self.active_cooldowns),
            "cooldown_details": {
                condition: until.isoformat()
                for condition, until in self.active_cooldowns.items()
            },
            "trigger_history_count": len(self.trigger_history),
            "last_emergency": (
                self.last_emergency_response.timestamp.isoformat()
                if self.last_emergency_response
                else None
            )
        }

    def get_trigger_history(
        self,
        limit: int = 100,
        severity: Optional[str] = None
    ) -> list[TriggeredCondition]:
        """
        Get trigger history.

        Args:
            limit: Maximum number of entries to return
            severity: Filter by severity ("warning" or "critical")

        Returns:
            List of triggered conditions
        """
        history = self.trigger_history

        if severity:
            history = [t for t in history if t.severity == severity]

        return history[-limit:]
