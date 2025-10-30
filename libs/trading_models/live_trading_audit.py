"""
Enhanced Audit and Performance Reporting for Live Trading

This module provides comprehensive audit logging with tamper-evident hash chains,
performance reporting, and export functionality for live trading operations.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import structlog

from .live_trading_config import PerformanceMetrics, TradingMode

logger = structlog.get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    MODE_TRANSITION = "mode_transition"
    TRADE_EXECUTED = "trade_executed"
    RISK_ADJUSTMENT = "risk_adjustment"
    EMERGENCY_STOP = "emergency_stop"
    MANUAL_OVERRIDE = "manual_override"
    VALIDATION_COMPLETED = "validation_completed"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIGURATION_CHANGE = "configuration_change"


@dataclass
class AuditEntry:
    """Tamper-evident audit log entry."""
    id: str
    event_type: AuditEventType
    timestamp: datetime
    data: dict[str, Any]
    user: Optional[str] = None
    hash_value: str = ""
    previous_hash: str = ""

    def calculate_hash(self, previous_hash: str = "") -> str:
        """
        Calculate hash for tamper-evident logging.

        Args:
            previous_hash: Hash of previous entry

        Returns:
            SHA-256 hash of entry
        """
        hash_data = {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "user": self.user,
            "previous_hash": previous_hash
        }

        hash_input = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_input.encode()).hexdigest()


@dataclass
class TradeAnalysis:
    """Detailed trade-by-trade analysis."""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    direction: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    duration: Optional[timedelta]
    entry_reasoning: str
    exit_reasoning: Optional[str]
    market_conditions: dict[str, Any]
    risk_metrics: dict[str, float]


@dataclass
class PerformanceReport:
    """Comprehensive performance report."""
    report_id: str
    period_start: datetime
    period_end: datetime
    trading_mode: TradingMode

    # Performance metrics
    metrics: PerformanceMetrics

    # Trade analysis
    trades: list[TradeAnalysis]

    # Comparison data
    backtest_comparison: Optional[dict[str, float]] = None
    paper_trading_comparison: Optional[dict[str, float]] = None

    # Risk metrics
    max_drawdown_date: Optional[datetime] = None
    largest_loss_trade: Optional[str] = None
    largest_win_trade: Optional[str] = None

    # System metrics
    system_uptime_percent: float = 100.0
    api_errors: int = 0
    emergency_stops: int = 0

    # Recommendations
    recommendations: list[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class LiveTradingAudit:
    """
    Enhanced audit logging and performance reporting system.

    Provides tamper-evident logging, comprehensive reporting,
    and multi-format export capabilities.
    """

    def __init__(self, audit_log_path: Optional[Path] = None):
        """
        Initialize the audit system.

        Args:
            audit_log_path: Path to audit log file
        """
        self.audit_log_path = audit_log_path or Path("logs/live_trading_audit.jsonl")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        self.audit_entries: list[AuditEntry] = []
        self.last_hash = ""
        self.trade_analyses: list[TradeAnalysis] = []

        self.logger = logger.bind(component="LiveTradingAudit")

        # Load last hash from existing log
        self._load_last_hash()

        self.logger.info(
            "Audit system initialized",
            log_path=str(self.audit_log_path)
        )

    def _load_last_hash(self) -> None:
        """Load the last hash from existing audit log."""
        if not self.audit_log_path.exists():
            return

        try:
            with open(self.audit_log_path) as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    self.last_hash = last_entry.get("hash_value", "")
                    self.logger.info("Loaded last hash from audit log")
        except Exception as e:
            self.logger.warning(
                "Could not load last hash",
                error=str(e)
            )

    def log_event(
        self,
        event_type: AuditEventType,
        data: dict[str, Any],
        user: Optional[str] = None
    ) -> AuditEntry:
        """
        Log an audit event with tamper-evident hash.

        Args:
            event_type: Type of event
            data: Event data
            user: User associated with event

        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            id=f"audit_{datetime.now(UTC).timestamp()}",
            event_type=event_type,
            timestamp=datetime.now(UTC),
            data=data,
            user=user,
            previous_hash=self.last_hash
        )

        # Calculate hash
        entry.hash_value = entry.calculate_hash(self.last_hash)
        self.last_hash = entry.hash_value

        # Store entry
        self.audit_entries.append(entry)

        # Write to file
        self._write_to_log(entry)

        self.logger.info(
            "Audit event logged",
            event_type=event_type.value,
            entry_id=entry.id
        )

        return entry

    def _write_to_log(self, entry: AuditEntry) -> None:
        """Write audit entry to log file."""
        try:
            with open(self.audit_log_path, 'a') as f:
                entry_dict = {
                    "id": entry.id,
                    "event_type": entry.event_type.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "data": entry.data,
                    "user": entry.user,
                    "hash_value": entry.hash_value,
                    "previous_hash": entry.previous_hash
                }
                f.write(json.dumps(entry_dict, default=str) + '\n')
        except Exception as e:
            self.logger.error(
                "Failed to write audit entry",
                error=str(e),
                entry_id=entry.id
            )

    def verify_audit_integrity(self) -> bool:
        """
        Verify integrity of audit log using hash chain.

        Returns:
            True if audit log is intact
        """
        if not self.audit_log_path.exists():
            return True

        try:
            with open(self.audit_log_path) as f:
                lines = f.readlines()

            previous_hash = ""
            for line in lines:
                entry_data = json.loads(line)

                # Recreate entry
                entry = AuditEntry(
                    id=entry_data["id"],
                    event_type=AuditEventType(entry_data["event_type"]),
                    timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                    data=entry_data["data"],
                    user=entry_data.get("user"),
                    hash_value=entry_data["hash_value"],
                    previous_hash=entry_data["previous_hash"]
                )

                # Verify hash
                expected_hash = entry.calculate_hash(previous_hash)
                if expected_hash != entry.hash_value:
                    self.logger.error(
                        "Audit integrity check failed",
                        entry_id=entry.id,
                        expected=expected_hash,
                        actual=entry.hash_value
                    )
                    return False

                previous_hash = entry.hash_value

            self.logger.info("Audit integrity verified")
            return True

        except Exception as e:
            self.logger.error(
                "Audit integrity verification failed",
                error=str(e)
            )
            return False

    def add_trade_analysis(self, analysis: TradeAnalysis) -> None:
        """
        Add trade analysis for reporting.

        Args:
            analysis: Trade analysis data
        """
        self.trade_analyses.append(analysis)

        # Log trade execution
        self.log_event(
            event_type=AuditEventType.TRADE_EXECUTED,
            data={
                "trade_id": analysis.trade_id,
                "symbol": analysis.symbol,
                "direction": analysis.direction,
                "entry_price": analysis.entry_price,
                "exit_price": analysis.exit_price,
                "pnl": analysis.pnl,
                "entry_reasoning": analysis.entry_reasoning
            }
        )


    def generate_performance_report(
        self,
        period_start: datetime,
        period_end: datetime,
        trading_mode: TradingMode,
        metrics: PerformanceMetrics,
        backtest_metrics: Optional[PerformanceMetrics] = None,
        paper_metrics: Optional[PerformanceMetrics] = None
    ) -> PerformanceReport:
        """
        Generate comprehensive performance report.

        Args:
            period_start: Report period start
            period_end: Report period end
            trading_mode: Trading mode during period
            metrics: Performance metrics
            backtest_metrics: Backtest comparison metrics
            paper_metrics: Paper trading comparison metrics

        Returns:
            Performance report
        """
        # Filter trades for period
        period_trades = [
            t for t in self.trade_analyses
            if period_start <= t.entry_time <= period_end
        ]

        # Calculate comparisons
        backtest_comparison = None
        if backtest_metrics:
            backtest_comparison = {
                "win_rate_diff": metrics.win_rate - backtest_metrics.win_rate,
                "sharpe_diff": metrics.sharpe_ratio - backtest_metrics.sharpe_ratio,
                "drawdown_diff": metrics.max_drawdown - backtest_metrics.max_drawdown
            }

        paper_comparison = None
        if paper_metrics:
            paper_comparison = {
                "win_rate_diff": metrics.win_rate - paper_metrics.win_rate,
                "sharpe_diff": metrics.sharpe_ratio - paper_metrics.sharpe_ratio,
                "drawdown_diff": metrics.max_drawdown - paper_metrics.max_drawdown
            }

        # Find notable trades
        largest_loss_trade = None
        largest_win_trade = None
        if period_trades:
            loss_trades = [t for t in period_trades if t.pnl and t.pnl < 0]
            win_trades = [t for t in period_trades if t.pnl and t.pnl > 0]

            if loss_trades:
                largest_loss_trade = min(loss_trades, key=lambda t: t.pnl).trade_id
            if win_trades:
                largest_win_trade = max(win_trades, key=lambda t: t.pnl).trade_id

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, backtest_comparison, paper_comparison)

        report = PerformanceReport(
            report_id=f"report_{datetime.now(UTC).timestamp()}",
            period_start=period_start,
            period_end=period_end,
            trading_mode=trading_mode,
            metrics=metrics,
            trades=period_trades,
            backtest_comparison=backtest_comparison,
            paper_trading_comparison=paper_comparison,
            largest_loss_trade=largest_loss_trade,
            largest_win_trade=largest_win_trade,
            recommendations=recommendations
        )

        # Log report generation
        self.log_event(
            event_type=AuditEventType.VALIDATION_COMPLETED,
            data={
                "report_id": report.report_id,
                "period_days": (period_end - period_start).days,
                "total_trades": len(period_trades),
                "win_rate": metrics.win_rate,
                "sharpe_ratio": metrics.sharpe_ratio
            }
        )

        self.logger.info(
            "Performance report generated",
            report_id=report.report_id,
            trades=len(period_trades)
        )

        return report

    def _generate_recommendations(
        self,
        metrics: PerformanceMetrics,
        backtest_comparison: Optional[dict[str, float]],
        paper_comparison: Optional[dict[str, float]]
    ) -> list[str]:
        """Generate performance recommendations."""
        recommendations = []

        # Win rate recommendations
        if metrics.win_rate < 0.45:
            recommendations.append(
                "Win rate below target (45%). Consider reviewing entry criteria and signal quality."
            )

        # Sharpe ratio recommendations
        if metrics.sharpe_ratio < 0.5:
            recommendations.append(
                "Sharpe ratio below target (0.5). Review risk-adjusted returns and consider reducing position sizes."
            )

        # Drawdown recommendations
        if metrics.max_drawdown > 0.15:
            recommendations.append(
                "Maximum drawdown exceeds 15%. Implement tighter stop losses and reduce correlation between positions."
            )

        # Comparison recommendations
        if backtest_comparison:
            if backtest_comparison["win_rate_diff"] < -0.05:
                recommendations.append(
                    "Live win rate significantly lower than backtest. Review execution quality and slippage."
                )

        if paper_comparison:
            if paper_comparison["sharpe_diff"] < -0.2:
                recommendations.append(
                    "Live Sharpe ratio degraded from paper trading. Monitor execution costs and market impact."
                )

        # Profit factor recommendations
        if metrics.profit_factor < 1.5:
            recommendations.append(
                "Profit factor below 1.5. Focus on cutting losses quickly and letting winners run."
            )

        return recommendations

    def export_report_json(self, report: PerformanceReport, output_path: Path) -> None:
        """
        Export report to JSON format.

        Args:
            report: Performance report
            output_path: Output file path
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            report_dict = {
                "report_id": report.report_id,
                "period": {
                    "start": report.period_start.isoformat(),
                    "end": report.period_end.isoformat()
                },
                "trading_mode": report.trading_mode.value,
                "metrics": {
                    "win_rate": report.metrics.win_rate,
                    "total_trades": report.metrics.total_trades,
                    "sharpe_ratio": report.metrics.sharpe_ratio,
                    "max_drawdown": report.metrics.max_drawdown,
                    "profit_factor": report.metrics.profit_factor,
                    "total_pnl": report.metrics.total_pnl
                },
                "trades": [
                    {
                        "trade_id": t.trade_id,
                        "symbol": t.symbol,
                        "direction": t.direction,
                        "pnl": t.pnl,
                        "pnl_percent": t.pnl_percent,
                        "entry_time": t.entry_time.isoformat(),
                        "exit_time": t.exit_time.isoformat() if t.exit_time else None
                    }
                    for t in report.trades
                ],
                "comparisons": {
                    "backtest": report.backtest_comparison,
                    "paper_trading": report.paper_trading_comparison
                },
                "recommendations": report.recommendations,
                "timestamp": report.timestamp.isoformat()
            }

            with open(output_path, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)

            self.logger.info(
                "Report exported to JSON",
                path=str(output_path)
            )

        except Exception as e:
            self.logger.error(
                "Failed to export JSON report",
                error=str(e)
            )

    def export_report_csv(self, report: PerformanceReport, output_path: Path) -> None:
        """
        Export report to CSV format.

        Args:
            report: Performance report
            output_path: Output file path
        """
        try:
            import csv

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow([
                    "Trade ID", "Symbol", "Direction", "Entry Time", "Exit Time",
                    "Entry Price", "Exit Price", "Quantity", "P&L", "P&L %",
                    "Duration (hours)", "Entry Reasoning"
                ])

                # Write trades
                for trade in report.trades:
                    duration_hours = trade.duration.total_seconds() / 3600 if trade.duration else None
                    writer.writerow([
                        trade.trade_id,
                        trade.symbol,
                        trade.direction,
                        trade.entry_time.isoformat(),
                        trade.exit_time.isoformat() if trade.exit_time else "",
                        trade.entry_price,
                        trade.exit_price or "",
                        trade.quantity,
                        trade.pnl or "",
                        f"{trade.pnl_percent:.2%}" if trade.pnl_percent else "",
                        f"{duration_hours:.1f}" if duration_hours else "",
                        trade.entry_reasoning
                    ])

            self.logger.info(
                "Report exported to CSV",
                path=str(output_path)
            )

        except Exception as e:
            self.logger.error(
                "Failed to export CSV report",
                error=str(e)
            )

    def get_audit_events(
        self,
        event_type: Optional[AuditEventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user: Optional[str] = None
    ) -> list[AuditEntry]:
        """
        Get audit events with optional filtering.

        Args:
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            user: Filter by user

        Returns:
            List of matching audit entries
        """
        entries = self.audit_entries

        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        if user:
            entries = [e for e in entries if e.user == user]

        return entries
