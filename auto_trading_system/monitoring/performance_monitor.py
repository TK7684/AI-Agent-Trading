"""
Real-time Performance Monitor
Comprehensive monitoring system for trading performance, system health, and learning metrics.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import psutil

from ..database.performance_repository import PerformanceRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Real-time system performance metrics"""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_available: float = 0.0
    disk_usage: float = 0.0
    disk_free: float = 0.0
    network_io: Dict[str, float] = field(default_factory=dict)
    active_connections: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TradingMetrics:
    """Real-time trading performance metrics"""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    active_positions: int = 0
    daily_pnl: float = 0.0
    current_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    average_trade_duration: float = 0.0
    trades_per_hour: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LearningMetrics:
    """Real-time learning and adaptation metrics"""

    learning_cycles_today: int = 0
    accuracy_improvement: float = 0.0
    profit_improvement: float = 0.0
    convergence_score: float = 0.0
    strategies_optimized: int = 0
    parameters_adjusted: int = 0
    adaptation_frequency: float = 0.0
    confidence_score: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AlertConfig:
    """Configuration for performance alerts"""

    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    drawdown_threshold: float = 10.0
    win_rate_threshold: float = 40.0
    error_rate_threshold: float = 5.0


class PerformanceMonitor:
    """
    Real-time performance monitoring system with alerting and analytics.
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig()
        self.performance_repository = PerformanceRepository()

        # Metrics storage
        self.system_metrics_history: List[SystemMetrics] = []
        self.trading_metrics_history: List[TradingMetrics] = []
        self.learning_metrics_history: List[LearningMetrics] = []

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.collection_interval = 30  # seconds
        self.max_history_size = 1000

        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

        # Performance counters
        self.start_time = time.time()
        self.last_trade_count = 0
        self.last_learning_cycle = time.time()

        logger.info("Performance Monitor initialized")

    async def start_monitoring(self) -> None:
        """Start the performance monitoring loop"""
        if self.is_monitoring:
            logger.warning("Monitoring is already running")
            return

        logger.info("Starting performance monitoring")
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop the performance monitoring loop"""
        logger.info("Stopping performance monitoring")
        self.is_monitoring = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Save final metrics
        await self._save_metrics_snapshot()
        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that collects metrics"""
        while self.is_monitoring:
            try:
                # Collect all metrics
                system_metrics = await self._collect_system_metrics()
                trading_metrics = await self._collect_trading_metrics()
                learning_metrics = await self._collect_learning_metrics()

                # Store metrics
                self._store_metrics(system_metrics, trading_metrics, learning_metrics)

                # Check for alerts
                await self._check_alerts(system_metrics, trading_metrics)

                # Save metrics to database periodically
                if len(self.system_metrics_history) % 5 == 0:  # Every 5 collections
                    await self._save_metrics_snapshot()

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_usage = psutil.cpu_percent(interval=1)

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available / (1024**3)  # GB

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_usage = disk.percent
            disk_free = disk.free / (1024**3)  # GB

            # Network metrics
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            }

            # Connection metrics
            active_connections = len(psutil.net_connections())

            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_available=memory_available,
                disk_usage=disk_usage,
                disk_free=disk_free,
                network_io=network_io,
                active_connections=active_connections,
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics()

    async def _collect_trading_metrics(self) -> TradingMetrics:
        """Collect trading performance metrics"""
        try:
            # Get recent performance from repository
            recent_performance = (
                await self.performance_repository.get_performance_metrics(hours=1)
            )

            if recent_performance:
                latest = recent_performance[0]

                # Calculate additional metrics
                win_rate = latest.win_rate or 0.0
                trades_per_hour = self._calculate_trades_per_hour(latest.total_trades)

                return TradingMetrics(
                    total_trades=latest.total_trades or 0,
                    winning_trades=latest.winning_trades or 0,
                    losing_trades=latest.losing_trades or 0,
                    active_positions=latest.active_positions or 0,
                    daily_pnl=latest.daily_pnl or 0.0,
                    current_drawdown=latest.max_drawdown or 0.0,
                    win_rate=win_rate,
                    profit_factor=self._calculate_profit_factor(latest),
                    sharpe_ratio=latest.sharpe_ratio or 0.0,
                    average_trade_duration=self._calculate_avg_trade_duration(),
                    trades_per_hour=trades_per_hour,
                )

            # Return default metrics if no data
            return TradingMetrics()

        except Exception as e:
            logger.error(f"Error collecting trading metrics: {e}")
            return TradingMetrics()

    async def _collect_learning_metrics(self) -> LearningMetrics:
        """Collect learning and adaptation metrics"""
        try:
            # Get recent learning results
            learning_results = await self.performance_repository.get_learning_results(
                days=1
            )

            if learning_results:
                # Calculate learning metrics
                learning_cycles_today = len(learning_results)

                # Calculate improvements
                improvements = [
                    r.accuracy_improvement
                    for r in learning_results
                    if r.accuracy_improvement
                ]
                accuracy_improvement = (
                    sum(improvements) / len(improvements) if improvements else 0.0
                )

                profit_improvements = [
                    r.profit_improvement
                    for r in learning_results
                    if r.profit_improvement
                ]
                profit_improvement = (
                    sum(profit_improvements) / len(profit_improvements)
                    if profit_improvements
                    else 0.0
                )

                # Calculate convergence
                convergence_scores = [
                    r.convergence_score for r in learning_results if r.convergence_score
                ]
                convergence_score = (
                    sum(convergence_scores) / len(convergence_scores)
                    if convergence_scores
                    else 0.0
                )

                # Calculate adaptation frequency
                current_time = time.time()
                adaptation_frequency = (current_time - self.last_learning_cycle) / max(
                    learning_cycles_today, 1
                )
                self.last_learning_cycle = current_time

                return LearningMetrics(
                    learning_cycles_today=learning_cycles_today,
                    accuracy_improvement=accuracy_improvement,
                    profit_improvement=profit_improvement,
                    convergence_score=convergence_score,
                    strategies_optimized=len(
                        set(r.cycle_type for r in learning_results)
                    ),
                    parameters_adjusted=sum(
                        len(r.parameter_adjustments or {}) for r in learning_results
                    ),
                    adaptation_frequency=adaptation_frequency,
                    confidence_score=max(0.5, convergence_score),
                )

            # Return default metrics if no data
            return LearningMetrics()

        except Exception as e:
            logger.error(f"Error collecting learning metrics: {e}")
            return LearningMetrics()

    def _store_metrics(
        self,
        system_metrics: SystemMetrics,
        trading_metrics: TradingMetrics,
        learning_metrics: LearningMetrics,
    ) -> None:
        """Store metrics in history with size management"""
        self.system_metrics_history.append(system_metrics)
        self.trading_metrics_history.append(trading_metrics)
        self.learning_metrics_history.append(learning_metrics)

        # Manage history size
        if len(self.system_metrics_history) > self.max_history_size:
            self.system_metrics_history = self.system_metrics_history[
                -self.max_history_size :
            ]

        if len(self.trading_metrics_history) > self.max_history_size:
            self.trading_metrics_history = self.trading_metrics_history[
                -self.max_history_size :
            ]

        if len(self.learning_metrics_history) > self.max_history_size:
            self.learning_metrics_history = self.learning_metrics_history[
                -self.max_history_size :
            ]

    async def _check_alerts(
        self,
        system_metrics: SystemMetrics,
        trading_metrics: TradingMetrics,
    ) -> None:
        """Check for performance alerts"""
        alerts = []

        # System alerts
        if system_metrics.cpu_usage > self.config.cpu_threshold:
            alerts.append(
                {
                    "type": "SYSTEM",
                    "level": "WARNING",
                    "metric": "cpu_usage",
                    "value": system_metrics.cpu_usage,
                    "threshold": self.config.cpu_threshold,
                    "message": f"High CPU usage: {system_metrics.cpu_usage:.1f}%",
                }
            )

        if system_metrics.memory_usage > self.config.memory_threshold:
            alerts.append(
                {
                    "type": "SYSTEM",
                    "level": "WARNING",
                    "metric": "memory_usage",
                    "value": system_metrics.memory_usage,
                    "threshold": self.config.memory_threshold,
                    "message": f"High memory usage: {system_metrics.memory_usage:.1f}%",
                }
            )

        if system_metrics.disk_usage > self.config.disk_threshold:
            alerts.append(
                {
                    "type": "SYSTEM",
                    "level": "CRITICAL",
                    "metric": "disk_usage",
                    "value": system_metrics.disk_usage,
                    "threshold": self.config.disk_threshold,
                    "message": f"High disk usage: {system_metrics.disk_usage:.1f}%",
                }
            )

        # Trading alerts
        if trading_metrics.current_drawdown > self.config.drawdown_threshold:
            alerts.append(
                {
                    "type": "TRADING",
                    "level": "WARNING",
                    "metric": "current_drawdown",
                    "value": trading_metrics.current_drawdown,
                    "threshold": self.config.drawdown_threshold,
                    "message": f"High drawdown: {trading_metrics.current_drawdown:.1f}%",
                }
            )

        if (
            trading_metrics.win_rate < self.config.win_rate_threshold
            and trading_metrics.total_trades > 10
        ):
            alerts.append(
                {
                    "type": "TRADING",
                    "level": "WARNING",
                    "metric": "win_rate",
                    "value": trading_metrics.win_rate,
                    "threshold": self.config.win_rate_threshold,
                    "message": f"Low win rate: {trading_metrics.win_rate:.1f}%",
                }
            )

        # Trigger alert callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    await callback(alert["type"], alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

    async def _save_metrics_snapshot(self) -> None:
        """Save current metrics snapshot to database"""
        try:
            if not self.system_metrics_history:
                return

            # Get latest metrics
            latest_system = self.system_metrics_history[-1]
            latest_trading = (
                self.trading_metrics_history[-1]
                if self.trading_metrics_history
                else None
            )
            latest_learning = (
                self.learning_metrics_history[-1]
                if self.learning_metrics_history
                else None
            )

            # Prepare metrics data
            metrics_data = {
                "timestamp": latest_system.timestamp,
                "cpu_usage": latest_system.cpu_usage,
                "memory_usage": latest_system.memory_usage,
                "disk_usage": latest_system.disk_usage,
                "network_latency": 0.0,  # Would be calculated
                "error_rate": 0.0,  # Would be calculated
                "active_connections": latest_system.active_connections,
                "requests_per_minute": 0,  # Would be calculated,
            }

            # Add trading metrics if available
            if latest_trading:
                metrics_data.update(
                    {
                        "daily_pnl": latest_trading.daily_pnl,
                        "total_trades": latest_trading.total_trades,
                        "winning_trades": latest_trading.winning_trades,
                        "losing_trades": latest_trading.losing_trades,
                        "win_rate": latest_trading.win_rate,
                        "active_positions": latest_trading.active_positions,
                        "max_drawdown": latest_trading.current_drawdown,
                        "sharpe_ratio": latest_trading.sharpe_ratio,
                        "sortino_ratio": 0.0,  # Would be calculated
                        "calmar_ratio": 0.0,  # Would be calculated
                    }
                )

            # Save to database
            await self.performance_repository.save_performance_metrics(metrics_data)

        except Exception as e:
            logger.error(f"Error saving metrics snapshot: {e}")

    def add_alert_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Add a callback for performance alerts"""
        self.alert_callbacks.append(callback)

    def remove_alert_callback(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Remove an alert callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.system_metrics_history:
            return {}

        latest_system = self.system_metrics_history[-1]
        latest_trading = (
            self.trading_metrics_history[-1] if self.trading_metrics_history else None
        )
        latest_learning = (
            self.learning_metrics_history[-1] if self.learning_metrics_history else None
        )

        return {
            "system": {
                "cpu_usage": latest_system.cpu_usage,
                "memory_usage": latest_system.memory_usage,
                "memory_available": latest_system.memory_available,
                "disk_usage": latest_system.disk_usage,
                "disk_free": latest_system.disk_free,
                "active_connections": latest_system.active_connections,
                "timestamp": latest_system.timestamp.isoformat(),
            },
            "trading": {
                "total_trades": latest_trading.total_trades if latest_trading else 0,
                "winning_trades": latest_trading.winning_trades
                if latest_trading
                else 0,
                "losing_trades": latest_trading.losing_trades if latest_trading else 0,
                "active_positions": latest_trading.active_positions
                if latest_trading
                else 0,
                "daily_pnl": latest_trading.daily_pnl if latest_trading else 0.0,
                "current_drawdown": latest_trading.current_drawdown
                if latest_trading
                else 0.0,
                "win_rate": latest_trading.win_rate if latest_trading else 0.0,
                "profit_factor": latest_trading.profit_factor
                if latest_trading
                else 0.0,
                "sharpe_ratio": latest_trading.sharpe_ratio if latest_trading else 0.0,
                "trades_per_hour": latest_trading.trades_per_hour
                if latest_trading
                else 0.0,
                "timestamp": latest_trading.timestamp.isoformat()
                if latest_trading
                else None,
            },
            "learning": {
                "learning_cycles_today": latest_learning.learning_cycles_today
                if latest_learning
                else 0,
                "accuracy_improvement": latest_learning.accuracy_improvement
                if latest_learning
                else 0.0,
                "profit_improvement": latest_learning.profit_improvement
                if latest_learning
                else 0.0,
                "convergence_score": latest_learning.convergence_score
                if latest_learning
                else 0.0,
                "strategies_optimized": latest_learning.strategies_optimized
                if latest_learning
                else 0,
                "parameters_adjusted": latest_learning.parameters_adjusted
                if latest_learning
                else 0,
                "adaptation_frequency": latest_learning.adaptation_frequency
                if latest_learning
                else 0.0,
                "confidence_score": latest_learning.confidence_score
                if latest_learning
                else 1.0,
                "timestamp": latest_learning.timestamp.isoformat()
                if latest_learning
                else None,
            },
        }

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        # Filter metrics by time
        recent_system = [
            m
            for m in self.system_metrics_history
            if m.timestamp.timestamp() > cutoff_time
        ]
        recent_trading = [
            m
            for m in self.trading_metrics_history
            if m.timestamp.timestamp() > cutoff_time
        ]
        recent_learning = [
            m
            for m in self.learning_metrics_history
            if m.timestamp.timestamp() > cutoff_time
        ]

        report = {
            "report_period_hours": hours,
            "data_points": {
                "system": len(recent_system),
                "trading": len(recent_trading),
                "learning": len(recent_learning),
            },
            "system_performance": self._calculate_system_performance_summary(
                recent_system
            ),
            "trading_performance": self._calculate_trading_performance_summary(
                recent_trading
            ),
            "learning_performance": self._calculate_learning_performance_summary(
                recent_learning
            ),
            "alerts": self._get_recent_alerts(hours),
        }

        return report

    def _calculate_system_performance_summary(
        self, metrics: List[SystemMetrics]
    ) -> Dict[str, Any]:
        """Calculate system performance summary"""
        if not metrics:
            return {}

        return {
            "avg_cpu_usage": sum(m.cpu_usage for m in metrics) / len(metrics),
            "max_cpu_usage": max(m.cpu_usage for m in metrics),
            "avg_memory_usage": sum(m.memory_usage for m in metrics) / len(metrics),
            "max_memory_usage": max(m.memory_usage for m in metrics),
            "avg_disk_usage": sum(m.disk_usage for m in metrics) / len(metrics),
            "avg_connections": sum(m.active_connections for m in metrics)
            / len(metrics),
            "uptime_hours": (time.time() - self.start_time) / 3600,
        }

    def _calculate_trading_performance_summary(
        self, metrics: List[TradingMetrics]
    ) -> Dict[str, Any]:
        """Calculate trading performance summary"""
        if not metrics:
            return {}

        return {
            "total_trades": max(m.total_trades for m in metrics),
            "win_rate": sum(m.win_rate for m in metrics) / len(metrics),
            "daily_pnl": max(m.daily_pnl for m in metrics),
            "max_drawdown": max(m.current_drawdown for m in metrics),
            "avg_sharpe_ratio": sum(m.sharpe_ratio for m in metrics) / len(metrics),
            "avg_trades_per_hour": sum(m.trades_per_hour for m in metrics)
            / len(metrics),
            "current_positions": max(m.active_positions for m in metrics),
        }

    def _calculate_learning_performance_summary(
        self, metrics: List[LearningMetrics]
    ) -> Dict[str, Any]:
        """Calculate learning performance summary"""
        if not metrics:
            return {}

        return {
            "total_learning_cycles": sum(m.learning_cycles_today for m in metrics),
            "avg_accuracy_improvement": sum(m.accuracy_improvement for m in metrics)
            / len(metrics),
            "avg_profit_improvement": sum(m.profit_improvement for m in metrics)
            / len(metrics),
            "avg_convergence_score": sum(m.convergence_score for m in metrics)
            / len(metrics),
            "total_strategies_optimized": sum(m.strategies_optimized for m in metrics),
            "total_parameters_adjusted": sum(m.parameters_adjusted for m in metrics),
            "avg_confidence_score": sum(m.confidence_score for m in metrics)
            / len(metrics),
        }

    def _get_recent_alerts(self, hours: int) -> List[Dict[str, Any]]:
        """Get recent alerts (would be stored in alert history)"""
        # This would be implemented with an alert history storage
        return []

    def _calculate_trades_per_hour(self, total_trades: int) -> float:
        """Calculate trades per hour rate"""
        if total_trades <= self.last_trade_count:
            return 0.0

        trades_delta = total_trades - self.last_trade_count
        time_delta = time.time() - self.start_time

        if time_delta > 0:
            return (trades_delta / time_delta) * 3600  # Convert to per hour

        return 0.0

    def _calculate_profit_factor(self, latest_metrics) -> float:
        """Calculate profit factor from metrics"""
        # This would be calculated from detailed trade data
        return 1.5  # Placeholder

    def _calculate_avg_trade_duration(self) -> float:
        """Calculate average trade duration"""
        # This would be calculated from detailed trade data
        return 120.0  # Placeholder in minutes
