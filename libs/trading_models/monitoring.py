"""
Comprehensive monitoring and telemetry system for the autonomous trading system.
Provides real-time metrics collection, OpenTelemetry integration, and Prometheus exports.
"""

import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

# OpenTelemetry imports
from opentelemetry import metrics, trace

# from opentelemetry.exporter.prometheus import PrometheusMetricReader  # Optional dependency
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# from opentelemetry.exporter.jaeger.thrift import JaegerExporter  # Optional dependency
# from opentelemetry.instrumentation.requests import RequestsInstrumentor  # Optional dependency
# from opentelemetry.instrumentation.logging import LoggingInstrumentor  # Optional dependency
# Prometheus client
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)


@dataclass
class TradingMetrics:
    """Core trading performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_fees: float = 0.0
    total_funding: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    peak_equity: float = 0.0

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    @property
    def profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(pnl for pnl in self._trade_pnls if pnl > 0)
        gross_loss = abs(sum(pnl for pnl in self._trade_pnls if pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')

    def __post_init__(self):
        self._trade_pnls: list[float] = []
        self._returns: deque = deque(maxlen=252)  # 1 year of daily returns


@dataclass
class PatternMetrics:
    """Pattern-specific performance metrics"""
    pattern_id: str
    total_signals: int = 0
    winning_signals: int = 0
    total_pnl: float = 0.0
    avg_holding_time: float = 0.0
    confidence_scores: list[float] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        """Calculate pattern hit rate percentage"""
        if self.total_signals == 0:
            return 0.0
        return (self.winning_signals / self.total_signals) * 100

    @property
    def expectancy(self) -> float:
        """Calculate pattern expectancy"""
        if self.total_signals == 0:
            return 0.0
        return self.total_pnl / self.total_signals


@dataclass
class SystemMetrics:
    """System performance and health metrics"""
    uptime_seconds: float = 0.0
    scan_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    llm_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    api_call_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    @property
    def scan_latency_p95(self) -> float:
        """Calculate 95th percentile scan latency"""
        if not self.scan_latencies:
            return 0.0
        return statistics.quantiles(list(self.scan_latencies), n=20)[18]  # 95th percentile

    @property
    def llm_latency_p95(self) -> float:
        """Calculate 95th percentile LLM latency"""
        if not self.llm_latencies:
            return 0.0
        return statistics.quantiles(list(self.llm_latencies), n=20)[18]  # 95th percentile


class MetricsCollector:
    """Central metrics collection and aggregation system"""

    def __init__(self):
        self.trading_metrics = TradingMetrics()
        self.pattern_metrics: dict[str, PatternMetrics] = {}
        self.system_metrics = SystemMetrics()
        self._lock = threading.RLock()
        self._start_time = time.time()

        # Initialize Prometheus metrics
        self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metric collectors"""
        from prometheus_client import CollectorRegistry

        # Use a custom registry to avoid conflicts in tests
        self.registry = CollectorRegistry()

        # Trading metrics
        self.trades_total = Counter('trading_trades_total', 'Total number of trades', ['outcome'], registry=self.registry)
        self.pnl_total = Gauge('trading_pnl_total', 'Total P&L including fees', registry=self.registry)
        self.win_rate = Gauge('trading_win_rate_percent', 'Win rate percentage', registry=self.registry)
        self.drawdown_current = Gauge('trading_drawdown_current_percent', 'Current drawdown percentage', registry=self.registry)
        self.drawdown_max = Gauge('trading_drawdown_max_percent', 'Maximum drawdown percentage', registry=self.registry)

        # Pattern metrics
        self.pattern_hit_rate = Gauge('trading_pattern_hit_rate_percent', 'Pattern hit rate', ['pattern_id'], registry=self.registry)
        self.pattern_expectancy = Gauge('trading_pattern_expectancy', 'Pattern expectancy', ['pattern_id'], registry=self.registry)
        self.pattern_signals = Counter('trading_pattern_signals_total', 'Pattern signals', ['pattern_id', 'outcome'], registry=self.registry)

        # System metrics
        self.scan_latency = Histogram('system_scan_latency_seconds', 'Market scan latency', buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0], registry=self.registry)
        self.llm_latency = Histogram('system_llm_latency_seconds', 'LLM call latency', buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0], registry=self.registry)
        self.error_count = Counter('system_errors_total', 'System errors', ['error_type'], registry=self.registry)
        self.uptime_seconds = Gauge('system_uptime_seconds', 'System uptime in seconds', registry=self.registry)
        self.memory_usage = Gauge('system_memory_usage_mb', 'Memory usage in MB', registry=self.registry)
        self.cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage', registry=self.registry)

        # Cost metrics
        self.llm_cost_total = Counter('trading_llm_cost_usd_total', 'Total LLM costs', ['model'], registry=self.registry)
        self.cost_per_trade = Gauge('trading_cost_per_trade_usd', 'Average cost per trade', registry=self.registry)

    def record_trade(self, pnl: float, fees: float, funding: float, outcome: str, pattern_id: Optional[str] = None):
        """Record a completed trade"""
        with self._lock:
            # Update trading metrics
            self.trading_metrics.total_trades += 1
            self.trading_metrics.total_pnl += pnl
            self.trading_metrics.total_fees += fees
            self.trading_metrics.total_funding += funding
            self.trading_metrics.net_pnl = self.trading_metrics.total_pnl - self.trading_metrics.total_fees - self.trading_metrics.total_funding

            if outcome == 'win':
                self.trading_metrics.winning_trades += 1
            else:
                self.trading_metrics.losing_trades += 1

            # Update drawdown
            current_equity = self.trading_metrics.net_pnl
            if current_equity > self.trading_metrics.peak_equity:
                self.trading_metrics.peak_equity = current_equity
                self.trading_metrics.current_drawdown = 0.0
            else:
                self.trading_metrics.current_drawdown = ((self.trading_metrics.peak_equity - current_equity) /
                                                       max(self.trading_metrics.peak_equity, 1.0)) * 100
                self.trading_metrics.max_drawdown = max(self.trading_metrics.max_drawdown,
                                                      self.trading_metrics.current_drawdown)

            # Update pattern metrics
            if pattern_id:
                if pattern_id not in self.pattern_metrics:
                    self.pattern_metrics[pattern_id] = PatternMetrics(pattern_id=pattern_id)

                pattern = self.pattern_metrics[pattern_id]
                pattern.total_signals += 1
                pattern.total_pnl += pnl
                if outcome == 'win':
                    pattern.winning_signals += 1

                # Update Prometheus pattern metrics
                self.pattern_signals.labels(pattern_id=pattern_id, outcome=outcome).inc()
                self.pattern_hit_rate.labels(pattern_id=pattern_id).set(pattern.hit_rate)
                self.pattern_expectancy.labels(pattern_id=pattern_id).set(pattern.expectancy)

            # Update Prometheus trading metrics
            self.trades_total.labels(outcome=outcome).inc()
            self.pnl_total.set(self.trading_metrics.net_pnl)
            self.win_rate.set(self.trading_metrics.win_rate)
            self.drawdown_current.set(self.trading_metrics.current_drawdown)
            self.drawdown_max.set(self.trading_metrics.max_drawdown)

    def record_scan_latency(self, latency_seconds: float):
        """Record market scan latency"""
        with self._lock:
            self.system_metrics.scan_latencies.append(latency_seconds)
            self.scan_latency.observe(latency_seconds)

    def record_llm_latency(self, latency_seconds: float, model: str, cost_usd: float):
        """Record LLM call latency and cost"""
        with self._lock:
            self.system_metrics.llm_latencies.append(latency_seconds)
            self.llm_latency.observe(latency_seconds)
            self.llm_cost_total.labels(model=model).inc(cost_usd)

            # Update cost per trade
            if self.trading_metrics.total_trades > 0:
                total_llm_cost = sum(self.llm_cost_total._value.values())
                self.cost_per_trade.set(total_llm_cost / self.trading_metrics.total_trades)

    def record_error(self, error_type: str):
        """Record system error"""
        with self._lock:
            self.system_metrics.error_counts[error_type] += 1
            self.error_count.labels(error_type=error_type).inc()

    def update_system_stats(self, memory_mb: float, cpu_percent: float):
        """Update system resource usage"""
        with self._lock:
            self.system_metrics.memory_usage_mb = memory_mb
            self.system_metrics.cpu_usage_percent = cpu_percent
            self.system_metrics.uptime_seconds = time.time() - self._start_time

            # Update Prometheus system metrics
            self.memory_usage.set(memory_mb)
            self.cpu_usage.set(cpu_percent)
            self.uptime_seconds.set(self.system_metrics.uptime_seconds)

    def get_trading_summary(self) -> dict[str, Any]:
        """Get comprehensive trading metrics summary"""
        with self._lock:
            return {
                'total_trades': self.trading_metrics.total_trades,
                'win_rate': self.trading_metrics.win_rate,
                'net_pnl': self.trading_metrics.net_pnl,
                'total_fees': self.trading_metrics.total_fees,
                'total_funding': self.trading_metrics.total_funding,
                'max_drawdown': self.trading_metrics.max_drawdown,
                'current_drawdown': self.trading_metrics.current_drawdown,
                'profit_factor': self.trading_metrics.profit_factor,
                'sharpe_ratio': self._calculate_sharpe_ratio(),
                'mar_ratio': self._calculate_mar_ratio()
            }

    def get_system_summary(self) -> dict[str, Any]:
        """Get system performance summary"""
        with self._lock:
            return {
                'uptime_hours': self.system_metrics.uptime_seconds / 3600,
                'scan_latency_p95': self.system_metrics.scan_latency_p95,
                'llm_latency_p95': self.system_metrics.llm_latency_p95,
                'error_counts': dict(self.system_metrics.error_counts),
                'memory_usage_mb': self.system_metrics.memory_usage_mb,
                'cpu_usage_percent': self.system_metrics.cpu_usage_percent
            }

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from returns"""
        if len(self.trading_metrics._returns) < 2:
            return 0.0

        returns = list(self.trading_metrics._returns)
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        return (mean_return * 252) / (std_return * (252 ** 0.5))  # Annualized

    def _calculate_mar_ratio(self) -> float:
        """Calculate MAR ratio (return / max drawdown)"""
        if self.trading_metrics.max_drawdown == 0:
            return 0.0

        annual_return = (self.trading_metrics.net_pnl / max(self.trading_metrics.peak_equity, 1.0)) * 100
        return annual_return / self.trading_metrics.max_drawdown


class OpenTelemetryManager:
    """Manages OpenTelemetry tracing and metrics"""

    def __init__(self, service_name: str = "autonomous-trading-system", jaeger_endpoint: Optional[str] = None):
        self.service_name = service_name
        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None

        self._setup_tracing(jaeger_endpoint)
        self._setup_metrics()

    def _setup_tracing(self, jaeger_endpoint: Optional[str]):
        """Setup distributed tracing with Jaeger"""
        self.tracer_provider = TracerProvider()
        trace.set_tracer_provider(self.tracer_provider)

        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint=jaeger_endpoint,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)

        self.tracer = trace.get_tracer(self.service_name)

        # Auto-instrument common libraries
        RequestsInstrumentor().instrument()
        LoggingInstrumentor().instrument()

    def _setup_metrics(self):
        """Setup OpenTelemetry metrics"""
        # Create Prometheus metric reader
        prometheus_reader = PrometheusMetricReader()

        self.meter_provider = MeterProvider(metric_readers=[prometheus_reader])
        metrics.set_meter_provider(self.meter_provider)

        self.meter = metrics.get_meter(self.service_name)

    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[dict[str, Any]] = None):
        """Context manager for tracing operations"""
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            start_time = time.time()
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)


class AlertManager:
    """Manages alerts for system failures and performance degradation"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules: list[AlertRule] = []
        self.active_alerts: dict[str, Alert] = {}
        self._lock = threading.RLock()

    def add_alert_rule(self, rule: 'AlertRule'):
        """Add an alert rule"""
        with self._lock:
            self.alert_rules.append(rule)

    def check_alerts(self):
        """Check all alert rules and trigger alerts if needed"""
        with self._lock:
            for rule in self.alert_rules:
                try:
                    if rule.should_trigger(self.metrics_collector):
                        alert_id = f"{rule.name}_{int(time.time())}"
                        if alert_id not in self.active_alerts:
                            alert = Alert(
                                id=alert_id,
                                rule_name=rule.name,
                                message=rule.get_message(self.metrics_collector),
                                severity=rule.severity,
                                timestamp=datetime.now(UTC)
                            )
                            self.active_alerts[alert_id] = alert
                            self._send_alert(alert)
                except Exception as e:
                    logger.error(f"Error checking alert rule {rule.name}: {e}")

    def _send_alert(self, alert: 'Alert'):
        """Send alert notification"""
        logger.warning(f"ALERT [{alert.severity}] {alert.rule_name}: {alert.message}")
        # Here you would integrate with your alerting system (Slack, PagerDuty, etc.)


@dataclass
class Alert:
    """Represents an active alert"""
    id: str
    rule_name: str
    message: str
    severity: str
    timestamp: datetime


class AlertRule:
    """Base class for alert rules"""

    def __init__(self, name: str, severity: str = "warning"):
        self.name = name
        self.severity = severity

    def should_trigger(self, metrics: MetricsCollector) -> bool:
        """Check if alert should trigger"""
        raise NotImplementedError

    def get_message(self, metrics: MetricsCollector) -> str:
        """Get alert message"""
        raise NotImplementedError


class DrawdownAlert(AlertRule):
    """Alert for excessive drawdown"""

    def __init__(self, threshold_percent: float):
        super().__init__(f"drawdown_alert_{threshold_percent}%", "critical")
        self.threshold = threshold_percent

    def should_trigger(self, metrics: MetricsCollector) -> bool:
        return metrics.trading_metrics.current_drawdown > self.threshold

    def get_message(self, metrics: MetricsCollector) -> str:
        return f"Current drawdown {metrics.trading_metrics.current_drawdown:.2f}% exceeds threshold {self.threshold}%"


class LatencyAlert(AlertRule):
    """Alert for high latency"""

    def __init__(self, metric_type: str, threshold_seconds: float):
        super().__init__(f"{metric_type}_latency_alert", "warning")
        self.metric_type = metric_type
        self.threshold = threshold_seconds

    def should_trigger(self, metrics: MetricsCollector) -> bool:
        if self.metric_type == "scan":
            return metrics.system_metrics.scan_latency_p95 > self.threshold
        elif self.metric_type == "llm":
            return metrics.system_metrics.llm_latency_p95 > self.threshold
        return False

    def get_message(self, metrics: MetricsCollector) -> str:
        if self.metric_type == "scan":
            current = metrics.system_metrics.scan_latency_p95
        else:
            current = metrics.system_metrics.llm_latency_p95
        return f"{self.metric_type.upper()} latency P95 {current:.2f}s exceeds threshold {self.threshold}s"


class ErrorRateAlert(AlertRule):
    """Alert for high error rates"""

    def __init__(self, error_type: str, threshold_count: int, time_window_minutes: int = 5):
        super().__init__(f"{error_type}_error_alert", "warning")
        self.error_type = error_type
        self.threshold = threshold_count
        self.time_window = time_window_minutes

    def should_trigger(self, metrics: MetricsCollector) -> bool:
        error_count = metrics.system_metrics.error_counts.get(self.error_type, 0)
        return error_count > self.threshold

    def get_message(self, metrics: MetricsCollector) -> str:
        count = metrics.system_metrics.error_counts.get(self.error_type, 0)
        return f"{self.error_type} error count {count} exceeds threshold {self.threshold}"


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None
_telemetry_manager: Optional[OpenTelemetryManager] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_telemetry_manager() -> OpenTelemetryManager:
    """Get global telemetry manager instance"""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = OpenTelemetryManager()
    return _telemetry_manager


def start_prometheus_server(port: int = 8000):
    """Start Prometheus metrics server"""
    start_http_server(port)
    logger.info(f"Prometheus metrics server started on port {port}")


# Decorator for automatic operation tracing
def trace_operation(operation_name: str):
    """Decorator to automatically trace function calls"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry_manager()
            with telemetry.trace_operation(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Decorator for automatic latency tracking
def track_latency(metric_name: str):
    """Decorator to automatically track function latency"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                metrics = get_metrics_collector()
                if metric_name == "scan":
                    metrics.record_scan_latency(latency)
                elif metric_name == "llm":
                    metrics.record_llm_latency(latency, "unknown", 0.0)
        return wrapper
    return decorator


class MonitoringSystem:
    """Main monitoring system that orchestrates all monitoring components."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.telemetry_manager = OpenTelemetryManager()
        self.alert_callback = None

    async def start(self):
        """Start the monitoring system."""
        if self.config.get('metrics_enabled', True):
            # Start Prometheus server if configured
            prometheus_port = self.config.get('prometheus_port', 8000)
            start_prometheus_server(prometheus_port)

        if self.config.get('alerts_enabled', True):
            # Initialize alert rules
            self.alert_manager.add_rule(DrawdownAlert("high_drawdown", 0.08))
            self.alert_manager.add_rule(LatencyAlert("high_latency", 3000))
            self.alert_manager.add_rule(ErrorRateAlert("high_error_rate", 0.05))

    async def stop(self):
        """Stop the monitoring system."""
        pass

    def record_metric(self, name: str, value: float, labels: dict[str, str] = None):
        """Record a metric value."""
        # This would record to the appropriate metric type
        pass

    def send_alert(self, alert_type: str, data: dict[str, Any]):
        """Send an alert."""
        if self.alert_callback:
            self.alert_callback(alert_type, data)

    def set_alert_callback(self, callback):
        """Set callback for alert notifications."""
        self.alert_callback = callback
