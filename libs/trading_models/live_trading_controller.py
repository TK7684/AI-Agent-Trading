"""
Live Trading Controller

This module implements the main coordination component for live trading operations,
managing mode transitions, risk scaling, emergency controls, and integration with
the existing trading system.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

import structlog

from .emergency_circuit_breaker import EmergencyCircuitBreaker, SystemState
from .live_trading_config import (
    LiveTradingConfig,
    PerformanceMetrics,
    RiskLimits,
    TradingMode,
    TradingStatus,
    ValidationResult,
)

logger = structlog.get_logger(__name__)


class TransitionResult(Enum):
    """Result of mode transition attempt."""
    SUCCESS = "success"
    FAILED_VALIDATION = "failed_validation"
    EMERGENCY_ACTIVE = "emergency_active"
    COOLDOWN_ACTIVE = "cooldown_active"
    INSUFFICIENT_PERFORMANCE = "insufficient_performance"
    MANUAL_APPROVAL_REQUIRED = "manual_approval_required"


@dataclass
class ModeTransition:
    """Record of a mode transition."""
    from_mode: TradingMode
    to_mode: TradingMode
    timestamp: datetime
    result: TransitionResult
    reason: str
    validation_data: Optional[dict[str, Any]] = None


class LiveTradingController:
    """
    Main controller for live trading operations.

    Coordinates paper trading validation, live trading execution,
    risk scaling, and emergency controls.
    """

    def __init__(
        self,
        config: LiveTradingConfig,
        circuit_breaker: Optional[EmergencyCircuitBreaker] = None
    ):
        """
        Initialize the live trading controller.

        Args:
            config: Live trading configuration
            circuit_breaker: Emergency circuit breaker (creates default if None)
        """
        self.config = config
        self.current_mode = config.mode
        self.is_active = False

        # Initialize circuit breaker
        if circuit_breaker:
            self.circuit_breaker = circuit_breaker
        else:
            self.circuit_breaker = EmergencyCircuitBreaker(config.emergency_triggers)

        # State tracking
        self.transition_history: list[ModeTransition] = []
        self.last_validation: Optional[ValidationResult] = None
        self.paper_trading_start: Optional[datetime] = None
        self.live_trading_start: Optional[datetime] = None
        self.manual_override_active = False

        # Performance tracking
        self.current_positions = 0
        self.total_exposure = 0.0
        self.daily_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.last_trade_time: Optional[datetime] = None

        self.logger = logger.bind(component="LiveTradingController")

        self.logger.info(
            "Live trading controller initialized",
            mode=self.current_mode.value,
            testnet=config.testnet,
            allowed_symbols=config.allowed_symbols
        )

    def start_paper_trading(self, duration_days: int = 7) -> bool:
        """
        Start paper trading validation phase.

        Args:
            duration_days: Duration of paper trading validation

        Returns:
            True if paper trading started successfully
        """
        if self.circuit_breaker.emergency_active:
            self.logger.error("Cannot start paper trading - emergency active")
            return False

        if self.current_mode != TradingMode.PAPER:
            self.logger.warning(
                "Switching to paper trading mode",
                current_mode=self.current_mode.value
            )
            self.current_mode = TradingMode.PAPER

        self.paper_trading_start = datetime.now(UTC)
        self.is_active = True

        self.logger.info(
            "Paper trading started",
            duration_days=duration_days,
            start_time=self.paper_trading_start.isoformat()
        )

        return True


    def validate_paper_trading_results(
        self,
        performance: PerformanceMetrics
    ) -> ValidationResult:
        """
        Validate paper trading results against thresholds.

        Args:
            performance: Performance metrics from paper trading

        Returns:
            Validation result with pass/fail status
        """
        thresholds = self.config.performance_thresholds
        issues = []

        # Check win rate
        win_rate_passed = performance.win_rate >= thresholds.min_win_rate
        if not win_rate_passed:
            issues.append({
                "severity": "error",
                "category": "performance",
                "message": f"Win rate {performance.win_rate:.2%} below threshold {thresholds.min_win_rate:.2%}",
                "timestamp": datetime.now(UTC)
            })

        # Check Sharpe ratio
        sharpe_passed = performance.sharpe_ratio >= thresholds.min_sharpe_ratio
        if not sharpe_passed:
            issues.append({
                "severity": "error",
                "category": "performance",
                "message": f"Sharpe ratio {performance.sharpe_ratio:.2f} below threshold {thresholds.min_sharpe_ratio:.2f}",
                "timestamp": datetime.now(UTC)
            })

        # Check drawdown
        drawdown_passed = performance.max_drawdown <= thresholds.max_drawdown
        if not drawdown_passed:
            issues.append({
                "severity": "error",
                "category": "risk",
                "message": f"Max drawdown {performance.max_drawdown:.2%} exceeds threshold {thresholds.max_drawdown:.2%}",
                "timestamp": datetime.now(UTC)
            })

        # Check profit factor
        profit_factor_passed = performance.profit_factor >= thresholds.min_profit_factor
        if not profit_factor_passed:
            issues.append({
                "severity": "error",
                "category": "performance",
                "message": f"Profit factor {performance.profit_factor:.2f} below threshold {thresholds.min_profit_factor:.2f}",
                "timestamp": datetime.now(UTC)
            })

        # Check minimum trades
        min_trades_passed = performance.total_trades >= thresholds.min_trades
        if not min_trades_passed:
            issues.append({
                "severity": "error",
                "category": "data",
                "message": f"Only {performance.total_trades} trades, need {thresholds.min_trades}",
                "timestamp": datetime.now(UTC)
            })

        # Overall validation
        passed = all([
            win_rate_passed,
            sharpe_passed,
            drawdown_passed,
            profit_factor_passed,
            min_trades_passed
        ])

        validation_period = performance.end_date - performance.start_date

        # Create validation result (simplified - would use actual ValidationResult model)
        self.last_validation = {
            "passed": passed,
            "performance": performance,
            "validation_period": validation_period,
            "issues": issues,
            "timestamp": datetime.now(UTC),
            "win_rate_passed": win_rate_passed,
            "sharpe_ratio_passed": sharpe_passed,
            "drawdown_passed": drawdown_passed,
            "profit_factor_passed": profit_factor_passed,
            "min_trades_passed": min_trades_passed
        }

        self.logger.info(
            "Paper trading validation complete",
            passed=passed,
            win_rate=performance.win_rate,
            sharpe_ratio=performance.sharpe_ratio,
            max_drawdown=performance.max_drawdown,
            issues_count=len(issues)
        )

        return self.last_validation

    def transition_to_live_trading(self, manual_approval: bool = False) -> TransitionResult:
        """
        Transition from paper trading to live trading.

        Args:
            manual_approval: Whether manual approval was given

        Returns:
            Result of transition attempt
        """
        # Check prerequisites
        if self.circuit_breaker.emergency_active:
            self.logger.error("Cannot transition - emergency active")
            return TransitionResult.EMERGENCY_ACTIVE

        if self.current_mode == TradingMode.LIVE_MINIMAL:
            self.logger.warning("Already in live trading mode")
            return TransitionResult.SUCCESS

        # Check validation
        if not self.last_validation or not self.last_validation["passed"]:
            self.logger.error(
                "Cannot transition - paper trading validation failed",
                validation_passed=self.last_validation["passed"] if self.last_validation else None
            )
            return TransitionResult.FAILED_VALIDATION

        # Require manual approval for live trading
        if not manual_approval and not self.manual_override_active:
            self.logger.warning("Manual approval required for live trading transition")
            return TransitionResult.MANUAL_APPROVAL_REQUIRED

        # Perform transition
        old_mode = self.current_mode
        self.current_mode = TradingMode.LIVE_MINIMAL
        self.live_trading_start = datetime.now(UTC)

        # Update risk limits for live trading
        self.config.risk_limits = RiskLimits(
            max_risk_per_trade=0.001,  # 0.1%
            max_portfolio_exposure=0.02,  # 2%
            daily_loss_limit=0.01  # 1%
        )

        # Record transition
        transition = ModeTransition(
            from_mode=old_mode,
            to_mode=self.current_mode,
            timestamp=datetime.now(UTC),
            result=TransitionResult.SUCCESS,
            reason="Paper trading validation passed",
            validation_data=self.last_validation
        )
        self.transition_history.append(transition)

        self.logger.info(
            "Transitioned to live trading",
            from_mode=old_mode.value,
            to_mode=self.current_mode.value,
            risk_per_trade=self.config.risk_limits.max_risk_per_trade
        )

        return TransitionResult.SUCCESS

    def scale_trading_operations(
        self,
        new_risk_level: float,
        reason: str = "Performance validated"
    ) -> bool:
        """
        Scale trading operations to higher risk level.

        Args:
            new_risk_level: New risk per trade (0.0-0.01)
            reason: Reason for scaling

        Returns:
            True if scaling successful
        """
        if self.circuit_breaker.emergency_active:
            self.logger.error("Cannot scale - emergency active")
            return False

        if self.current_mode not in [TradingMode.LIVE_MINIMAL, TradingMode.LIVE_SCALED]:
            self.logger.error(
                "Cannot scale - not in live trading mode",
                current_mode=self.current_mode.value
            )
            return False

        # Validate new risk level
        if not (0 < new_risk_level <= 0.01):  # Max 1%
            self.logger.error(
                "Invalid risk level",
                new_risk_level=new_risk_level
            )
            return False

        old_risk = self.config.risk_limits.max_risk_per_trade

        # Update risk limits
        self.config.risk_limits.max_risk_per_trade = new_risk_level

        # Update mode if scaling significantly
        if new_risk_level > 0.0025:  # > 0.25%
            old_mode = self.current_mode
            self.current_mode = TradingMode.LIVE_SCALED

            transition = ModeTransition(
                from_mode=old_mode,
                to_mode=self.current_mode,
                timestamp=datetime.now(UTC),
                result=TransitionResult.SUCCESS,
                reason=reason
            )
            self.transition_history.append(transition)

        self.logger.info(
            "Trading operations scaled",
            old_risk=old_risk,
            new_risk=new_risk_level,
            reason=reason,
            mode=self.current_mode.value
        )

        return True

    def emergency_stop(self, reason: str) -> None:
        """
        Execute emergency stop of all trading operations.

        Args:
            reason: Reason for emergency stop
        """
        self.logger.error(
            "EMERGENCY STOP TRIGGERED",
            reason=reason,
            current_mode=self.current_mode.value
        )

        # Trigger circuit breaker
        response = self.circuit_breaker.execute_emergency_stop(reason)

        # Update state
        old_mode = self.current_mode
        self.current_mode = TradingMode.EMERGENCY_STOP
        self.is_active = False

        # Record transition
        transition = ModeTransition(
            from_mode=old_mode,
            to_mode=self.current_mode,
            timestamp=datetime.now(UTC),
            result=TransitionResult.SUCCESS,
            reason=reason
        )
        self.transition_history.append(transition)

        self.logger.error(
            "Emergency stop executed",
            actions_taken=len(response.actions_taken),
            cooldown_until=response.cooldown_until.isoformat()
        )

    def enable_manual_override(self) -> None:
        """Enable manual override mode for authorized operations."""
        self.manual_override_active = True
        self.logger.warning("Manual override enabled")

    def disable_manual_override(self) -> None:
        """Disable manual override mode."""
        self.manual_override_active = False
        self.logger.info("Manual override disabled")

    def update_system_state(
        self,
        current_drawdown: float,
        daily_loss: float,
        api_latency_ms: float,
        position_correlation: float
    ) -> None:
        """
        Update system state and check for emergency triggers.

        Args:
            current_drawdown: Current portfolio drawdown
            daily_loss: Daily loss percentage
            api_latency_ms: API latency in milliseconds
            position_correlation: Position correlation coefficient
        """
        state = SystemState(
            current_drawdown=current_drawdown,
            daily_loss=daily_loss,
            api_latency_ms=api_latency_ms,
            position_correlation=position_correlation,
            total_exposure=self.total_exposure,
            open_positions=self.current_positions,
            last_trade_time=self.last_trade_time,
            system_health="healthy" if not self.circuit_breaker.emergency_active else "critical"
        )

        # Check for triggered conditions
        triggered = self.circuit_breaker.check_triggers(state)

        if triggered:
            self.logger.warning(
                "Emergency triggers activated",
                trigger_count=len(triggered),
                conditions=[t.trigger.condition for t in triggered]
            )

            # Execute emergency response
            self.emergency_stop(f"{len(triggered)} emergency conditions triggered")

    def get_current_status(self) -> TradingStatus:
        """
        Get current trading status.

        Returns:
            Current trading status
        """
        return TradingStatus(
            mode=self.current_mode,
            is_active=self.is_active,
            current_positions=self.current_positions,
            total_exposure=self.total_exposure,
            daily_pnl=self.daily_pnl,
            unrealized_pnl=self.unrealized_pnl,
            last_trade_time=self.last_trade_time,
            emergency_active=self.circuit_breaker.emergency_active,
            cooldown_until=(
                self.circuit_breaker.last_emergency_response.cooldown_until
                if self.circuit_breaker.last_emergency_response
                else None
            ),
            system_health="healthy" if not self.circuit_breaker.emergency_active else "critical",
            last_update=datetime.now(UTC)
        )

    def get_transition_history(self, limit: int = 10) -> list[ModeTransition]:
        """
        Get mode transition history.

        Args:
            limit: Maximum number of transitions to return

        Returns:
            List of mode transitions
        """
        return self.transition_history[-limit:]

    def can_place_trade(self) -> tuple[bool, Optional[str]]:
        """
        Check if system can place a new trade.

        Returns:
            Tuple of (can_trade, reason_if_not)
        """
        if not self.is_active:
            return False, "Trading not active"

        if self.circuit_breaker.emergency_active:
            return False, "Emergency stop active"

        if self.current_mode == TradingMode.EMERGENCY_STOP:
            return False, "System in emergency stop mode"

        if self.current_mode == TradingMode.PAPER:
            return True, None  # Paper trading always allowed

        # Check risk limits
        if self.total_exposure >= self.config.risk_limits.max_portfolio_exposure:
            return False, f"Portfolio exposure limit reached ({self.total_exposure:.2%})"

        if abs(self.daily_pnl) >= self.config.risk_limits.daily_loss_limit:
            return False, f"Daily loss limit reached ({abs(self.daily_pnl):.2%})"

        return True, None

    def update_position_metrics(
        self,
        positions: int,
        exposure: float,
        daily_pnl: float,
        unrealized_pnl: float
    ) -> None:
        """
        Update position and P&L metrics.

        Args:
            positions: Number of open positions
            exposure: Total portfolio exposure
            daily_pnl: Daily P&L
            unrealized_pnl: Unrealized P&L
        """
        self.current_positions = positions
        self.total_exposure = exposure
        self.daily_pnl = daily_pnl
        self.unrealized_pnl = unrealized_pnl
        self.last_trade_time = datetime.now(UTC)
