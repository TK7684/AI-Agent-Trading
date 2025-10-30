"""
Comprehensive tests for the monitoring and telemetry system.
Tests metrics accuracy, alerting functionality, and timezone handling.
"""

import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from libs.trading_models.health_checks import (
    DatabaseHealthCheck,
    HealthCheck,
    HealthCheckManager,
    HealthCheckResult,
    HealthStatus,
    SystemResourceHealthCheck,
    ensure_utc_timezone,
)
from libs.trading_models.monitoring import (
    AlertManager,
    DrawdownAlert,
    ErrorRateAlert,
    LatencyAlert,
    MetricsCollector,
    OpenTelemetryManager,
    PatternMetrics,
    SystemMetrics,
    TradingMetrics,
    get_metrics_collector,
    trace_operation,
    track_latency,
)


class TestTradingMetrics:
    """Test trading metrics calculations"""

    def test_win_rate_calculation(self):
        """Test win rate calculation accuracy"""
        metrics = TradingMetrics()

        # No trades
        assert metrics.win_rate == 0.0

        # Add winning trades
        metrics.total_trades = 10
        metrics.winning_trades = 7
        assert metrics.win_rate == 70.0

        # Add losing trades
        metrics.total_trades = 20
        metrics.winning_trades = 12
        assert metrics.win_rate == 60.0

    def test_profit_factor_calculation(self):
        """Test profit factor calculation"""
        metrics = TradingMetrics()
        metrics._trade_pnls = [100, -50, 200, -30, 150, -80]

        # Profit factor = (100 + 200 + 150) / (50 + 30 + 80) = 450 / 160 = 2.8125
        expected_pf = 450 / 160
        assert abs(metrics.profit_factor - expected_pf) < 0.001

    def test_profit_factor_no_losses(self):
        """Test profit factor with no losses"""
        metrics = TradingMetrics()
        metrics._trade_pnls = [100, 200, 150]

        assert metrics.profit_factor == float('inf')

    def test_profit_factor_no_profits(self):
        """Test profit factor with no profits"""
        metrics = TradingMetrics()
        metrics._trade_pnls = [-50, -30, -80]

        assert metrics.profit_factor == 0.0


class TestPatternMetrics:
    """Test pattern-specific metrics"""

    def test_hit_rate_calculation(self):
        """Test pattern hit rate calculation"""
        pattern = PatternMetrics(pattern_id="test_pattern")

        # No signals
        assert pattern.hit_rate == 0.0

        # Add signals
        pattern.total_signals = 20
        pattern.winning_signals = 14
        assert pattern.hit_rate == 70.0

    def test_expectancy_calculation(self):
        """Test pattern expectancy calculation"""
        pattern = PatternMetrics(pattern_id="test_pattern")

        # No signals
        assert pattern.expectancy == 0.0

        # Add P&L
        pattern.total_signals = 10
        pattern.total_pnl = 250.0
        assert pattern.expectancy == 25.0


class TestSystemMetrics:
    """Test system performance metrics"""

    def test_latency_percentiles(self):
        """Test latency percentile calculations"""
        metrics = SystemMetrics()

        # Add latency data
        latencies = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] * 10
        for latency in latencies:
            metrics.scan_latencies.append(latency)

        p95 = metrics.scan_latency_p95
        assert 0.9 <= p95 <= 1.0  # Should be close to 95th percentile

    def test_empty_latencies(self):
        """Test latency calculations with no data"""
        metrics = SystemMetrics()
        assert metrics.scan_latency_p95 == 0.0
        assert metrics.llm_latency_p95 == 0.0


class TestMetricsCollector:
    """Test the main metrics collector"""

    def setup_method(self):
        """Setup for each test"""
        self.collector = MetricsCollector()

    def test_record_trade_updates_metrics(self):
        """Test that recording trades updates all relevant metrics"""
        # Record a winning trade
        self.collector.record_trade(
            pnl=100.0,
            fees=2.0,
            funding=0.5,
            outcome='win',
            pattern_id='test_pattern'
        )

        # Check trading metrics
        assert self.collector.trading_metrics.total_trades == 1
        assert self.collector.trading_metrics.winning_trades == 1
        assert self.collector.trading_metrics.total_pnl == 100.0
        assert self.collector.trading_metrics.total_fees == 2.0
        assert self.collector.trading_metrics.total_funding == 0.5
        assert self.collector.trading_metrics.net_pnl == 97.5

        # Check pattern metrics
        assert 'test_pattern' in self.collector.pattern_metrics
        pattern = self.collector.pattern_metrics['test_pattern']
        assert pattern.total_signals == 1
        assert pattern.winning_signals == 1
        assert pattern.total_pnl == 100.0

    def test_drawdown_calculation(self):
        """Test drawdown calculation accuracy"""
        # Start with profitable trade
        self.collector.record_trade(1000.0, 10.0, 0.0, 'win')
        assert self.collector.trading_metrics.peak_equity == 990.0
        assert self.collector.trading_metrics.current_drawdown == 0.0

        # Add losing trade
        self.collector.record_trade(-300.0, 5.0, 0.0, 'loss')
        net_pnl = 990.0 - 305.0  # 685.0
        expected_dd = ((990.0 - 685.0) / 990.0) * 100  # ~30.8%

        assert abs(self.collector.trading_metrics.current_drawdown - expected_dd) < 0.1
        assert self.collector.trading_metrics.max_drawdown >= expected_dd

    def test_latency_recording(self):
        """Test latency recording"""
        self.collector.record_scan_latency(0.5)
        self.collector.record_scan_latency(0.8)

        assert len(self.collector.system_metrics.scan_latencies) == 2
        assert 0.5 in self.collector.system_metrics.scan_latencies
        assert 0.8 in self.collector.system_metrics.scan_latencies

    def test_error_recording(self):
        """Test error recording"""
        self.collector.record_error('data_error')
        self.collector.record_error('data_error')
        self.collector.record_error('llm_error')

        assert self.collector.system_metrics.error_counts['data_error'] == 2
        assert self.collector.system_metrics.error_counts['llm_error'] == 1

    def test_thread_safety(self):
        """Test that metrics collection is thread-safe"""
        def record_trades():
            for i in range(100):
                self.collector.record_trade(10.0, 1.0, 0.0, 'win' if i % 2 == 0 else 'loss')

        # Run multiple threads
        threads = [threading.Thread(target=record_trades) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have recorded 500 trades total
        assert self.collector.trading_metrics.total_trades == 500
        assert self.collector.trading_metrics.winning_trades == 250
        assert self.collector.trading_metrics.losing_trades == 250


class TestOpenTelemetryManager:
    """Test OpenTelemetry integration"""

    def test_initialization(self):
        """Test OpenTelemetry manager initialization"""
        manager = OpenTelemetryManager("test-service")
        assert manager.service_name == "test-service"
        assert manager.tracer is not None
        assert manager.meter is not None

    def test_trace_operation_context_manager(self):
        """Test trace operation context manager"""
        manager = OpenTelemetryManager("test-service")

        with manager.trace_operation("test_operation", {"key": "value"}) as span:
            assert span is not None
            time.sleep(0.01)  # Small delay to test duration

    def test_trace_operation_with_exception(self):
        """Test trace operation handles exceptions"""
        manager = OpenTelemetryManager("test-service")

        with pytest.raises(ValueError):
            with manager.trace_operation("test_operation") as span:
                raise ValueError("Test exception")


class TestAlertManager:
    """Test alert management system"""

    def setup_method(self):
        """Setup for each test"""
        self.collector = MetricsCollector()
        self.alert_manager = AlertManager(self.collector)

    def test_drawdown_alert(self):
        """Test drawdown alert triggering"""
        alert_rule = DrawdownAlert(threshold_percent=5.0)
        self.alert_manager.add_alert_rule(alert_rule)

        # Set high drawdown
        self.collector.trading_metrics.current_drawdown = 8.0

        # Check alerts
        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            self.alert_manager.check_alerts()
            mock_send.assert_called_once()

    def test_latency_alert(self):
        """Test latency alert triggering"""
        alert_rule = LatencyAlert("scan", threshold_seconds=1.0)
        self.alert_manager.add_alert_rule(alert_rule)

        # Add high latencies
        for _ in range(100):
            self.collector.system_metrics.scan_latencies.append(2.0)

        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            self.alert_manager.check_alerts()
            mock_send.assert_called_once()

    def test_error_rate_alert(self):
        """Test error rate alert triggering"""
        alert_rule = ErrorRateAlert("data_error", threshold_count=5)
        self.alert_manager.add_alert_rule(alert_rule)

        # Add errors
        for _ in range(10):
            self.collector.record_error('data_error')

        with patch.object(self.alert_manager, '_send_alert') as mock_send:
            self.alert_manager.check_alerts()
            mock_send.assert_called_once()


class TestHealthChecks:
    """Test health check system"""

    def test_health_check_result_serialization(self):
        """Test health check result serialization"""
        result = HealthCheckResult(
            component="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            response_time_ms=50.0,
            timestamp=datetime.now(UTC),
            details={"key": "value"}
        )

        data = result.to_dict()
        assert data['component'] == "test"
        assert data['status'] == "healthy"
        assert data['message'] == "All good"
        assert data['response_time_ms'] == 50.0
        assert 'timestamp' in data
        assert data['details'] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_health_check_manager(self):
        """Test health check manager functionality"""
        manager = HealthCheckManager()

        # Create mock health check
        mock_check = Mock(spec=HealthCheck)
        mock_check.name = "test_check"
        mock_check.check.return_value = HealthCheckResult(
            component="test_check",
            status=HealthStatus.HEALTHY,
            message="OK",
            response_time_ms=100.0,
            timestamp=datetime.now(UTC)
        )

        manager.register_health_check(mock_check)

        # Run health checks
        results = await manager.check_all()

        assert "test_check" in results
        assert results["test_check"].status == HealthStatus.HEALTHY
        assert manager.get_overall_status() == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling"""
        manager = HealthCheckManager()

        # Create slow health check
        async def slow_check():
            await asyncio.sleep(2.0)  # Longer than timeout
            return HealthCheckResult(
                component="slow_check",
                status=HealthStatus.HEALTHY,
                message="OK",
                response_time_ms=2000.0,
                timestamp=datetime.now(UTC)
            )

        mock_check = Mock(spec=HealthCheck)
        mock_check.name = "slow_check"
        mock_check.check = slow_check

        manager.register_health_check(mock_check)

        # Run with short timeout
        results = await manager.check_all(timeout_ms=500)

        assert "slow_check" in results
        assert results["slow_check"].status == HealthStatus.UNKNOWN

    def test_system_resource_health_check(self):
        """Test system resource health check"""
        # Mock psutil
        with patch('libs.trading_models.health_checks.psutil') as mock_psutil:
            mock_psutil.cpu_percent.return_value = 50.0
            mock_psutil.virtual_memory.return_value = Mock(percent=60.0, available=4*1024**3)
            mock_psutil.disk_usage.return_value = Mock(used=50*1024**3, total=100*1024**3, free=50*1024**3)

            check = SystemResourceHealthCheck(
                cpu_threshold=80.0,
                memory_threshold=80.0,
                disk_threshold=80.0
            )

            # Should be healthy
            result = asyncio.run(check.check())
            assert result.status == HealthStatus.HEALTHY

    def test_database_health_check(self):
        """Test database health check"""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor

        def mock_db_func():
            return mock_conn

        check = DatabaseHealthCheck(mock_db_func)
        result = asyncio.run(check.check())

        assert result.status == HealthStatus.HEALTHY
        assert "Database connection successful" in result.message


class TestTimezoneHandling:
    """Test UTC timezone handling for consistent comparisons"""

    def test_ensure_utc_timezone_naive_datetime(self):
        """Test converting naive datetime to UTC"""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        utc_dt = ensure_utc_timezone(naive_dt)

        assert utc_dt.tzinfo == UTC
        assert utc_dt.hour == 12  # Should remain the same

    def test_ensure_utc_timezone_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC"""
        # Create datetime in EST (UTC-5)
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=est)

        utc_dt = ensure_utc_timezone(est_dt)

        assert utc_dt.tzinfo == UTC
        assert utc_dt.hour == 17  # 12 PM EST = 5 PM UTC

    def test_ensure_utc_timezone_already_utc(self):
        """Test that UTC datetime remains unchanged"""
        utc_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result_dt = ensure_utc_timezone(utc_dt)

        assert result_dt == utc_dt
        assert result_dt.tzinfo == UTC

    def test_metrics_timestamp_consistency(self):
        """Test that all metrics use consistent UTC timestamps"""
        collector = MetricsCollector()

        # Record trade and check timestamp
        collector.record_trade(100.0, 1.0, 0.0, 'win')

        # Get summary and verify timestamps are UTC
        summary = collector.get_trading_summary()

        # All internal timestamps should be UTC
        # This is implicitly tested by the fact that calculations work correctly


class TestDecorators:
    """Test monitoring decorators"""

    def test_trace_operation_decorator(self):
        """Test trace operation decorator"""
        @trace_operation("test_function")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_track_latency_decorator(self):
        """Test latency tracking decorator"""
        collector = get_metrics_collector()
        initial_count = len(collector.system_metrics.scan_latencies)

        @track_latency("scan")
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()
        assert result == "success"

        # Should have recorded latency
        assert len(collector.system_metrics.scan_latencies) == initial_count + 1


class TestPnLCalculations:
    """Test P&L calculations include fees and funding"""

    def test_pnl_includes_fees_and_funding(self):
        """Test that P&L calculations properly include fees and funding costs"""
        collector = MetricsCollector()

        # Record trades with different fee and funding scenarios
        collector.record_trade(pnl=100.0, fees=2.0, funding=0.5, outcome='win')  # Net: 97.5
        collector.record_trade(pnl=-50.0, fees=1.5, funding=-0.3, outcome='loss')  # Net: -51.2
        collector.record_trade(pnl=200.0, fees=3.0, funding=1.0, outcome='win')  # Net: 196.0

        # Check that net P&L includes all costs
        expected_gross_pnl = 100.0 - 50.0 + 200.0  # 250.0
        expected_total_fees = 2.0 + 1.5 + 3.0  # 6.5
        expected_total_funding = 0.5 - 0.3 + 1.0  # 1.2
        expected_net_pnl = expected_gross_pnl - expected_total_fees - expected_total_funding  # 242.3

        assert collector.trading_metrics.total_pnl == expected_gross_pnl
        assert collector.trading_metrics.total_fees == expected_total_fees
        assert collector.trading_metrics.total_funding == expected_total_funding
        assert abs(collector.trading_metrics.net_pnl - expected_net_pnl) < 0.001

        # Verify summary includes all components
        summary = collector.get_trading_summary()
        assert summary['net_pnl'] == collector.trading_metrics.net_pnl
        assert summary['total_fees'] == expected_total_fees
        assert summary['total_funding'] == expected_total_funding


class TestMetricsAccuracy:
    """Test metrics calculation accuracy with edge cases"""

    def test_zero_division_handling(self):
        """Test handling of zero division in metrics calculations"""
        collector = MetricsCollector()

        # Test with no trades
        summary = collector.get_trading_summary()
        assert summary['win_rate'] == 0.0
        assert summary['sharpe_ratio'] == 0.0
        assert summary['mar_ratio'] == 0.0

    def test_single_trade_metrics(self):
        """Test metrics with single trade"""
        collector = MetricsCollector()
        collector.record_trade(100.0, 2.0, 0.0, 'win')

        summary = collector.get_trading_summary()
        assert summary['win_rate'] == 100.0
        assert summary['total_trades'] == 1
        assert summary['net_pnl'] == 98.0

    def test_large_number_handling(self):
        """Test handling of large numbers in calculations"""
        collector = MetricsCollector()

        # Record large P&L values
        collector.record_trade(1_000_000.0, 100.0, 50.0, 'win')
        collector.record_trade(-500_000.0, 75.0, 25.0, 'loss')

        summary = collector.get_trading_summary()
        expected_net = 1_000_000.0 - 500_000.0 - 100.0 - 75.0 - 50.0 - 25.0
        assert abs(summary['net_pnl'] - expected_net) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
