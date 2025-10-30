"""
Real-time Dashboard and Monitoring

This module provides real-time monitoring, visualization, and alerting
for live trading operations with manual override capabilities.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional

import structlog

from .live_trading_config import PerformanceMetrics
from .live_trading_controller import LiveTradingController

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    """Alert categories."""
    PERFORMANCE = "performance"
    RISK = "risk"
    SYSTEM = "system"
    EXECUTION = "execution"
    MANUAL = "manual"


@dataclass
class Alert:
    """Real-time alert."""
    id: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # "improving", "declining", "stable"
    period: timedelta
    timestamp: datetime


@dataclass
class OverrideCommand:
    """Manual override command."""
    command_type: str  # "emergency_stop", "resume_trading", "adjust_risk", etc.
    parameters: dict[str, Any]
    issued_by: str
    timestamp: datetime
    reason: str


class RealtimeDashboard:
    """
    Real-time dashboard for live trading monitoring and control.

    Provides visualization, alerting, and manual override capabilities.
    """

    def __init__(self, controller: LiveTradingController):
        """
        Initialize the real-time dashboard.

        Args:
            controller: Live trading controller instance
        """
        self.controller = controller
        self.alerts: list[Alert] = []
        self.alert_handlers: dict[AlertSeverity, list[Callable]] = {
            severity: [] for severity in AlertSeverity
        }
        self.performance_history: list[PerformanceMetrics] = []
        self.override_history: list[OverrideCommand] = []

        # Monitoring state
        self.last_update = datetime.now(UTC)
        self.update_interval = timedelta(seconds=30)

        self.logger = logger.bind(component="RealtimeDashboard")

        self.logger.info("Real-time dashboard initialized")

    def update_position_display(self, positions: list[dict[str, Any]]) -> None:
        """
        Update position display with current positions.

        Args:
            positions: List of current positions
        """
        self.logger.debug(
            "Updating position display",
            position_count=len(positions)
        )

        # Calculate aggregated metrics
        total_exposure = sum(p.get("exposure", 0.0) for p in positions)
        total_unrealized_pnl = sum(p.get("unrealized_pnl", 0.0) for p in positions)

        # Update controller metrics
        self.controller.update_position_metrics(
            positions=len(positions),
            exposure=total_exposure,
            daily_pnl=self.controller.daily_pnl,
            unrealized_pnl=total_unrealized_pnl
        )

        # Check for alerts
        if total_exposure > self.controller.config.risk_limits.max_portfolio_exposure:
            self.create_alert(
                severity=AlertSeverity.WARNING,
                category=AlertCategory.RISK,
                title="Portfolio Exposure High",
                message=f"Total exposure {total_exposure:.2%} exceeds limit {self.controller.config.risk_limits.max_portfolio_exposure:.2%}",
                metadata={"exposure": total_exposure, "positions": len(positions)}
            )

    def update_pnl_metrics(self, pnl_data: dict[str, float]) -> None:
        """
        Update P&L metrics display.

        Args:
            pnl_data: Dictionary with P&L metrics
        """
        daily_pnl = pnl_data.get("daily_pnl", 0.0)
        unrealized_pnl = pnl_data.get("unrealized_pnl", 0.0)
        realized_pnl = pnl_data.get("realized_pnl", 0.0)

        self.logger.debug(
            "Updating P&L metrics",
            daily_pnl=daily_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl
        )

        # Check for daily loss limit
        if abs(daily_pnl) >= self.controller.config.risk_limits.daily_loss_limit:
            self.create_alert(
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RISK,
                title="Daily Loss Limit Reached",
                message=f"Daily P&L {daily_pnl:.2%} reached limit {self.controller.config.risk_limits.daily_loss_limit:.2%}",
                metadata=pnl_data
            )

    def display_system_health(self, health: dict[str, Any]) -> None:
        """
        Display system health metrics.

        Args:
            health: System health data
        """
        cpu_usage = health.get("cpu_percent", 0.0)
        memory_usage = health.get("memory_percent", 0.0)
        api_latency = health.get("api_latency_ms", 0.0)

        self.logger.debug(
            "System health update",
            cpu=cpu_usage,
            memory=memory_usage,
            api_latency=api_latency
        )

        # Check for system issues
        if cpu_usage > 80:
            self.create_alert(
                severity=AlertSeverity.WARNING,
                category=AlertCategory.SYSTEM,
                title="High CPU Usage",
                message=f"CPU usage at {cpu_usage:.1f}%",
                metadata=health
            )

        if memory_usage > 85:
            self.create_alert(
                severity=AlertSeverity.WARNING,
                category=AlertCategory.SYSTEM,
                title="High Memory Usage",
                message=f"Memory usage at {memory_usage:.1f}%",
                metadata=health
            )

        if api_latency > 2000:  # 2 seconds
            self.create_alert(
                severity=AlertSeverity.ERROR,
                category=AlertCategory.SYSTEM,
                title="High API Latency",
                message=f"API latency at {api_latency:.0f}ms",
                metadata=health
            )

    def show_performance_trends(
        self,
        current_metrics: PerformanceMetrics,
        period: timedelta = timedelta(hours=24)
    ) -> list[PerformanceTrend]:
        """
        Show performance trends over time.

        Args:
            current_metrics: Current performance metrics
            period: Time period for trend analysis

        Returns:
            List of performance trends
        """
        trends = []

        # Store current metrics
        self.performance_history.append(current_metrics)

        # Keep only recent history
        cutoff_time = datetime.now(UTC) - period
        self.performance_history = [
            m for m in self.performance_history
            if m.end_date >= cutoff_time
        ]

        if len(self.performance_history) < 2:
            return trends

        # Calculate trends
        previous_metrics = self.performance_history[-2]

        # Win rate trend
        win_rate_change = (
            (current_metrics.win_rate - previous_metrics.win_rate) / previous_metrics.win_rate * 100
            if previous_metrics.win_rate > 0 else 0
        )
        trends.append(PerformanceTrend(
            metric_name="win_rate",
            current_value=current_metrics.win_rate,
            previous_value=previous_metrics.win_rate,
            change_percent=win_rate_change,
            trend="improving" if win_rate_change > 5 else "declining" if win_rate_change < -5 else "stable",
            period=period,
            timestamp=datetime.now(UTC)
        ))

        # Sharpe ratio trend
        sharpe_change = (
            (current_metrics.sharpe_ratio - previous_metrics.sharpe_ratio) / abs(previous_metrics.sharpe_ratio) * 100
            if previous_metrics.sharpe_ratio != 0 else 0
        )
        trends.append(PerformanceTrend(
            metric_name="sharpe_ratio",
            current_value=current_metrics.sharpe_ratio,
            previous_value=previous_metrics.sharpe_ratio,
            change_percent=sharpe_change,
            trend="improving" if sharpe_change > 10 else "declining" if sharpe_change < -10 else "stable",
            period=period,
            timestamp=datetime.now(UTC)
        ))

        self.logger.info(
            "Performance trends calculated",
            trend_count=len(trends),
            win_rate_trend=trends[0].trend if trends else None
        )

        return trends


    def create_alert(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        title: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> Alert:
        """
        Create and register a new alert.

        Args:
            severity: Alert severity level
            category: Alert category
            title: Alert title
            message: Alert message
            metadata: Additional metadata

        Returns:
            Created alert
        """
        alert = Alert(
            id=f"alert_{datetime.now(UTC).timestamp()}",
            severity=severity,
            category=category,
            title=title,
            message=message,
            timestamp=datetime.now(UTC),
            metadata=metadata or {}
        )

        self.alerts.append(alert)

        self.logger.log(
            severity.value,
            "Alert created",
            alert_id=alert.id,
            title=title,
            category=category.value
        )

        # Trigger alert handlers
        for handler in self.alert_handlers.get(severity, []):
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(
                    "Alert handler failed",
                    error=str(e),
                    alert_id=alert.id
                )

        return alert

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge
            user: User acknowledging the alert

        Returns:
            True if alert was acknowledged
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now(UTC)

                self.logger.info(
                    "Alert acknowledged",
                    alert_id=alert_id,
                    user=user
                )
                return True

        return False

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        category: Optional[AlertCategory] = None,
        acknowledged: Optional[bool] = None
    ) -> list[Alert]:
        """
        Get active alerts with optional filtering.

        Args:
            severity: Filter by severity
            category: Filter by category
            acknowledged: Filter by acknowledgment status

        Returns:
            List of matching alerts
        """
        alerts = self.alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if category:
            alerts = [a for a in alerts if a.category == category]

        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts

    def register_alert_handler(
        self,
        severity: AlertSeverity,
        handler: Callable[[Alert], None]
    ) -> None:
        """
        Register a handler for alerts of specific severity.

        Args:
            severity: Alert severity to handle
            handler: Handler function
        """
        self.alert_handlers[severity].append(handler)
        self.logger.info(
            "Alert handler registered",
            severity=severity.value
        )

    def handle_manual_override(self, command: OverrideCommand) -> bool:
        """
        Handle manual override command.

        Args:
            command: Override command to execute

        Returns:
            True if command executed successfully
        """
        self.logger.warning(
            "Manual override command received",
            command_type=command.command_type,
            issued_by=command.issued_by,
            reason=command.reason
        )

        success = False

        try:
            if command.command_type == "emergency_stop":
                self.controller.emergency_stop(command.reason)
                success = True

            elif command.command_type == "resume_trading":
                self.controller.circuit_breaker.reset_emergency_state()
                self.controller.circuit_breaker.clear_all_cooldowns()
                self.controller.is_active = True
                success = True

            elif command.command_type == "adjust_risk":
                new_risk = command.parameters.get("risk_per_trade")
                if new_risk:
                    success = self.controller.scale_trading_operations(
                        new_risk,
                        f"Manual adjustment by {command.issued_by}"
                    )

            elif command.command_type == "enable_override":
                self.controller.enable_manual_override()
                success = True

            elif command.command_type == "disable_override":
                self.controller.disable_manual_override()
                success = True

            else:
                self.logger.error(
                    "Unknown override command",
                    command_type=command.command_type
                )
                return False

            if success:
                self.override_history.append(command)

                self.create_alert(
                    severity=AlertSeverity.WARNING,
                    category=AlertCategory.MANUAL,
                    title="Manual Override Executed",
                    message=f"{command.command_type} by {command.issued_by}: {command.reason}",
                    metadata={"command": command.command_type, "user": command.issued_by}
                )

            return success

        except Exception as e:
            self.logger.error(
                "Override command failed",
                command_type=command.command_type,
                error=str(e)
            )
            return False

    def get_dashboard_summary(self) -> dict[str, Any]:
        """
        Get comprehensive dashboard summary.

        Returns:
            Dashboard summary data
        """
        status = self.controller.get_current_status()

        return {
            "status": status.to_dict(),
            "alerts": {
                "total": len(self.alerts),
                "unacknowledged": len([a for a in self.alerts if not a.acknowledged]),
                "critical": len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL]),
                "by_category": {
                    category.value: len([a for a in self.alerts if a.category == category])
                    for category in AlertCategory
                }
            },
            "performance_history_count": len(self.performance_history),
            "override_history_count": len(self.override_history),
            "last_update": self.last_update.isoformat(),
            "controller_mode": status.mode.value,
            "emergency_active": status.emergency_active
        }

    def clear_old_alerts(self, age: timedelta = timedelta(hours=24)) -> int:
        """
        Clear old acknowledged alerts.

        Args:
            age: Maximum age of alerts to keep

        Returns:
            Number of alerts cleared
        """
        cutoff_time = datetime.now(UTC) - age

        initial_count = len(self.alerts)
        self.alerts = [
            a for a in self.alerts
            if not a.acknowledged or a.acknowledged_at > cutoff_time
        ]

        cleared = initial_count - len(self.alerts)

        if cleared > 0:
            self.logger.info(
                "Old alerts cleared",
                count=cleared
            )

        return cleared

    def get_override_history(self, limit: int = 50) -> list[OverrideCommand]:
        """
        Get manual override history.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of override commands
        """
        return self.override_history[-limit:]
