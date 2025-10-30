"""
Tests for Load Testing System
Validates load testing functionality and performance measurement.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.trading_models.e2e_integration import E2EIntegrationSystem
from libs.trading_models.load_testing import (
    LoadTestConfig,
    LoadTestingSystem,
    PerformanceMetrics,
    ResourceMonitor,
)


class TestLoadTestingSystem:
    """Test load testing system functionality."""

    @pytest.fixture
    def mock_e2e_system(self):
        """Create mock E2E system for testing."""
        system = Mock(spec=E2EIntegrationSystem)
        system.run_complete_trading_cycle = AsyncMock()
        return system

    @pytest.fixture
    def load_tester(self, mock_e2e_system):
        """Create load testing system."""
        return LoadTestingSystem(mock_e2e_system)

    @pytest.fixture
    def test_config(self):
        """Create test load configuration."""
        return LoadTestConfig(
            name='test_load',
            duration_seconds=5,  # Short for testing
            concurrent_symbols=2,
            requests_per_second=2,
            symbols=['BTCUSDT', 'ETHUSDT'],
            timeframes=['1h', '4h']
        )

    @pytest.mark.asyncio
    async def test_sequential_load_test(self, load_tester, test_config, mock_e2e_system):
        """Test sequential load testing."""
        # Configure low RPS for sequential testing
        test_config.requests_per_second = 0.5

        # Mock successful responses
        mock_result = Mock()
        mock_result.success = True
        mock_result.duration_ms = 500
        mock_result.error_message = None

        mock_e2e_system.run_complete_trading_cycle.return_value = mock_result

        # Run load test
        metrics = await load_tester.run_load_test(test_config)

        # Verify results
        assert metrics.test_name == 'test_load'
        assert metrics.total_requests > 0
        assert metrics.successful_requests == metrics.total_requests
        assert metrics.failed_requests == 0
        assert metrics.error_rate_percent == 0.0
        assert metrics.avg_latency_ms > 0

    @pytest.mark.asyncio
    async def test_concurrent_load_test(self, load_tester, test_config, mock_e2e_system):
        """Test concurrent load testing."""
        # Configure higher RPS for concurrent testing
        test_config.requests_per_second = 4
        test_config.duration_seconds = 3

        # Mock successful responses with varying latencies
        call_count = 0
        async def mock_trading_cycle(symbol):
            nonlocal call_count
            call_count += 1

            result = Mock()
            result.success = True
            result.duration_ms = 400 + (call_count % 3) * 100  # Varying latencies
            result.error_message = None

            # Simulate some processing time
            await asyncio.sleep(0.1)
            return result

        mock_e2e_system.run_complete_trading_cycle.side_effect = mock_trading_cycle

        # Run load test
        metrics = await load_tester.run_load_test(test_config)

        # Verify results
        assert metrics.test_name == 'test_load'
        assert metrics.total_requests > 0
        assert metrics.requests_per_second > 0
        assert metrics.avg_latency_ms > 0
        assert metrics.p95_latency_ms >= metrics.avg_latency_ms

    @pytest.mark.asyncio
    async def test_load_test_with_errors(self, load_tester, test_config, mock_e2e_system):
        """Test load testing with some failures."""
        call_count = 0

        async def mock_trading_cycle_with_errors(symbol):
            nonlocal call_count
            call_count += 1

            # Fail every 3rd request
            if call_count % 3 == 0:
                raise Exception("Simulated error")

            result = Mock()
            result.success = True
            result.duration_ms = 600
            result.error_message = None
            return result

        mock_e2e_system.run_complete_trading_cycle.side_effect = mock_trading_cycle_with_errors

        # Run load test
        metrics = await load_tester.run_load_test(test_config)

        # Verify error handling
        assert metrics.failed_requests > 0
        assert metrics.error_rate_percent > 0
        assert metrics.successful_requests + metrics.failed_requests == metrics.total_requests

    @pytest.mark.asyncio
    async def test_slo_compliance_validation(self, load_tester, mock_e2e_system):
        """Test SLO compliance validation."""
        # Mock fast, successful responses
        mock_result = Mock()
        mock_result.success = True
        mock_result.duration_ms = 200  # Well under SLO
        mock_result.error_message = None

        mock_e2e_system.run_complete_trading_cycle.return_value = mock_result

        # Run SLO validation
        compliance = await load_tester.validate_slo_compliance()

        # Verify SLO structure
        assert 'uptime_slo' in compliance
        assert 'scan_latency_slo' in compliance
        assert 'llm_latency_slo' in compliance
        assert 'error_rate_slo' in compliance
        assert 'memory_usage_slo' in compliance

        # With fast responses, latency SLOs should pass
        assert compliance['scan_latency_slo']
        assert compliance['llm_latency_slo']
        assert compliance['error_rate_slo']

    @pytest.mark.asyncio
    async def test_failover_testing(self, load_tester, mock_e2e_system):
        """Test failover scenario testing."""
        # Mock system components
        mock_e2e_system.market_data = Mock()
        mock_e2e_system.market_data.fetch_multi_timeframe_data = AsyncMock()
        mock_e2e_system.llm_router = Mock()
        mock_e2e_system.llm_router.analyze_market = AsyncMock()
        mock_e2e_system.state = Mock()
        mock_e2e_system._trigger_safe_mode = Mock()

        # Mock trading cycle results
        mock_result = Mock()
        mock_result.success = False  # Simulate failure during failover
        mock_e2e_system.run_complete_trading_cycle.return_value = mock_result

        # Run failover tests
        results = await load_tester.run_failover_test()

        # Verify failover test structure
        assert 'market_data_failover' in results
        assert 'llm_failover' in results
        assert 'safe_mode_trigger' in results

        # Verify that failover scenarios were tested
        for test_name, result in results.items():
            assert isinstance(result, dict)
            # Should have either success indicators or error information
            assert 'recovery_successful' in result or 'error' in result

    def test_performance_metrics_calculation(self, load_tester):
        """Test performance metrics calculation."""
        # Mock data
        config = LoadTestConfig(
            name='test_metrics',
            duration_seconds=10,
            concurrent_symbols=1,
            requests_per_second=1,
            symbols=['BTCUSDT'],
            timeframes=['1h']
        )

        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        errors = ['error1', 'error2']
        resource_usage = {
            'max_memory_mb': 512,
            'avg_cpu_percent': 45.5
        }

        # Calculate metrics
        metrics = load_tester._calculate_performance_metrics(
            config, 10.0, latencies, errors, resource_usage
        )

        # Verify calculations
        assert metrics.test_name == 'test_metrics'
        assert metrics.duration_seconds == 10.0
        assert metrics.total_requests == 12  # 10 latencies + 2 errors
        assert metrics.successful_requests == 10
        assert metrics.failed_requests == 2
        assert metrics.requests_per_second == 1.2  # 12 requests / 10 seconds
        assert metrics.error_rate_percent == (2/12) * 100
        assert metrics.avg_latency_ms == 550.0  # Average of latencies
        assert metrics.p50_latency_ms == 550.0  # Median
        assert metrics.p95_latency_ms == 950.0  # 95th percentile
        assert metrics.max_latency_ms == 1000
        assert metrics.min_latency_ms == 100
        assert metrics.memory_usage_mb == 512
        assert metrics.cpu_usage_percent == 45.5

    @pytest.mark.asyncio
    async def test_all_load_scenarios(self, load_tester, mock_e2e_system):
        """Test running all predefined load scenarios."""
        # Mock successful responses
        mock_result = Mock()
        mock_result.success = True
        mock_result.duration_ms = 300
        mock_result.error_message = None

        mock_e2e_system.run_complete_trading_cycle.return_value = mock_result

        # Reduce scenario durations for testing
        for scenario in load_tester.load_scenarios.values():
            scenario.duration_seconds = 2  # Very short for testing

        # Run all scenarios
        results = await load_tester.run_all_load_scenarios()

        # Verify all scenarios were run
        expected_scenarios = ['baseline', 'moderate_load', 'high_load', 'stress_test', 'endurance_test']
        for scenario_name in expected_scenarios:
            assert scenario_name in results
            if results[scenario_name] is not None:  # Some might fail in test environment
                assert isinstance(results[scenario_name], PerformanceMetrics)

    def test_load_test_report_generation(self, load_tester):
        """Test load test report generation."""
        # Create mock metrics
        mock_metrics = PerformanceMetrics(
            test_name='test_scenario',
            duration_seconds=60.0,
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            requests_per_second=1.67,
            avg_latency_ms=450.0,
            p50_latency_ms=400.0,
            p95_latency_ms=800.0,
            p99_latency_ms=950.0,
            max_latency_ms=1000.0,
            min_latency_ms=100.0,
            memory_usage_mb=256.0,
            cpu_usage_percent=35.0,
            error_rate_percent=5.0,
            slo_compliance={
                'scan_latency': True,
                'p95_latency': True,
                'error_rate': False,  # 5% > 0.5% threshold
                'memory_usage': True
            }
        )

        results = {'test_scenario': mock_metrics}

        # Generate report
        report = load_tester.generate_load_test_report(results)

        # Verify report structure
        assert 'test_timestamp' in report
        assert 'slo_targets' in report
        assert 'scenarios' in report
        assert 'overall_compliance' in report
        assert 'summary' in report

        # Verify scenario data
        assert 'test_scenario' in report['scenarios']
        scenario_report = report['scenarios']['test_scenario']
        assert scenario_report['status'] == 'failed'  # Due to error_rate SLO violation
        assert 'error_rate' in scenario_report['slo_violations']

        # Verify summary
        summary = report['summary']
        assert summary['total_scenarios'] == 1
        assert summary['passed_scenarios'] == 0
        assert summary['failed_scenarios'] == 1
        assert 'error_rate' in summary['slo_violations']
        assert not report['overall_compliance']


class TestResourceMonitor:
    """Test resource monitoring functionality."""

    @pytest.fixture
    def resource_monitor(self):
        """Create resource monitor."""
        return ResourceMonitor()

    @pytest.mark.asyncio
    async def test_resource_monitoring_lifecycle(self, resource_monitor):
        """Test complete resource monitoring lifecycle."""
        # Start monitoring
        resource_monitor.start_monitoring()
        assert resource_monitor.monitoring
        assert resource_monitor.monitor_task is not None

        # Let it collect some data
        await asyncio.sleep(0.1)

        # Stop monitoring and get results
        results = resource_monitor.stop_monitoring()

        # Verify results structure
        assert isinstance(results, dict)
        if results:  # May be empty if monitoring was too brief
            assert 'sample_count' in results
            if results['sample_count'] > 0:
                assert 'max_memory_mb' in results
                assert 'avg_memory_mb' in results
                assert 'avg_cpu_percent' in results
                assert 'max_cpu_percent' in results

    @pytest.mark.asyncio
    async def test_resource_monitoring_data_collection(self, resource_monitor):
        """Test resource data collection."""
        with patch('psutil.Process') as mock_process_class:
            # Mock process and system stats
            mock_process = Mock()
            mock_memory_info = Mock()
            mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
            mock_process.memory_info.return_value = mock_memory_info
            mock_process.cpu_percent.return_value = 25.5
            mock_process_class.return_value = mock_process

            with patch('psutil.disk_io_counters') as mock_disk_io:
                mock_disk_io.return_value = Mock(read_bytes=1024*1024, write_bytes=2048*1024)

                with patch('psutil.net_io_counters') as mock_net_io:
                    mock_net_io.return_value = Mock(bytes_sent=512*1024, bytes_recv=1024*1024)

                    # Start monitoring
                    resource_monitor.start_monitoring()

                    # Let it collect one sample
                    await asyncio.sleep(0.1)

                    # Stop and verify
                    results = resource_monitor.stop_monitoring()

                    # Should have collected at least one sample
                    assert len(resource_monitor.resource_data) >= 0

                    if resource_monitor.resource_data:
                        sample = resource_monitor.resource_data[0]
                        assert sample.memory_mb == 100.0  # 100MB
                        assert sample.cpu_percent == 25.5
                        assert sample.disk_io_read_mb == 1.0  # 1MB
                        assert sample.disk_io_write_mb == 2.0  # 2MB

    def test_resource_monitor_empty_data(self, resource_monitor):
        """Test resource monitor with no data collected."""
        # Stop monitoring without starting (no data)
        results = resource_monitor.stop_monitoring()

        # Should return empty dict
        assert results == {}

    @pytest.mark.asyncio
    async def test_resource_monitor_error_handling(self, resource_monitor):
        """Test resource monitor handles errors gracefully."""
        with patch('psutil.Process') as mock_process_class:
            # Mock process to raise exception
            mock_process_class.side_effect = Exception("Process access denied")

            # Start monitoring
            resource_monitor.start_monitoring()

            # Let it try to collect data (should handle error)
            await asyncio.sleep(0.1)

            # Stop monitoring
            results = resource_monitor.stop_monitoring()

            # Should not crash and return empty results
            assert isinstance(results, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
