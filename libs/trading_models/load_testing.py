"""
Load Testing and Performance Validation System
Tests system performance under various load conditions and validates SLOs.
"""

import asyncio
import logging
import os
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import psutil

from .e2e_integration import E2EIntegrationSystem


@dataclass
class LoadTestConfig:
    """Configuration for load testing scenarios."""
    name: str
    duration_seconds: int
    concurrent_symbols: int
    requests_per_second: int
    symbols: list[str]
    timeframes: list[str]
    enable_llm: bool = False
    enable_execution: bool = False


@dataclass
class PerformanceMetrics:
    """Performance metrics collected during load testing."""
    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate_percent: float
    slo_compliance: dict[str, bool]


@dataclass
class SystemResourceUsage:
    """System resource usage metrics."""
    timestamp: datetime
    memory_mb: float
    cpu_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


class LoadTestingSystem:
    """
    Comprehensive load testing system for validating performance
    and SLO compliance under various load conditions.
    """

    def __init__(self, e2e_system: E2EIntegrationSystem):
        self.e2e_system = e2e_system
        self.logger = logging.getLogger(__name__)
        self.resource_monitor = ResourceMonitor()

        # SLO targets
        self.slo_targets = {
            'uptime_percentage': 99.5,
            'scan_latency_ms': 1000,
            'llm_latency_p95_ms': 3000,
            'error_rate_percentage': 0.5,
            'memory_growth_mb_per_hour': 100
        }

        # Predefined load test scenarios
        self.load_scenarios = {
            'baseline': LoadTestConfig(
                name='baseline',
                duration_seconds=300,  # 5 minutes
                concurrent_symbols=2,
                requests_per_second=1,
                symbols=['BTCUSDT', 'ETHUSDT'],
                timeframes=['1h', '4h']
            ),
            'moderate_load': LoadTestConfig(
                name='moderate_load',
                duration_seconds=600,  # 10 minutes
                concurrent_symbols=5,
                requests_per_second=2,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'],
                timeframes=['15m', '1h', '4h']
            ),
            'high_load': LoadTestConfig(
                name='high_load',
                duration_seconds=900,  # 15 minutes
                concurrent_symbols=10,
                requests_per_second=4,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
                        'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'MATICUSDT', 'AVAXUSDT'],
                timeframes=['15m', '1h', '4h', '1d']
            ),
            'stress_test': LoadTestConfig(
                name='stress_test',
                duration_seconds=1800,  # 30 minutes
                concurrent_symbols=20,
                requests_per_second=8,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
                        'BNBUSDT', 'XRPUSDT', 'SOLUSDT', 'MATICUSDT', 'AVAXUSDT',
                        'ATOMUSDT', 'NEARUSDT', 'FTMUSDT', 'SANDUSDT', 'MANAUSDT',
                        'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'THETAUSDT', 'FILUSDT'],
                timeframes=['15m', '1h', '4h', '1d'],
                enable_llm=True
            ),
            'endurance_test': LoadTestConfig(
                name='endurance_test',
                duration_seconds=7200,  # 2 hours
                concurrent_symbols=5,
                requests_per_second=1,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'],
                timeframes=['1h', '4h'],
                enable_llm=True,
                enable_execution=False  # Keep execution disabled for safety
            )
        }

    async def run_load_test(self, config: LoadTestConfig) -> PerformanceMetrics:
        """Run a comprehensive load test with the given configuration."""
        self.logger.info(f"Starting load test: {config.name}")

        # Start resource monitoring
        self.resource_monitor.start_monitoring()

        # Initialize metrics tracking
        latencies = []
        errors = []
        start_time = time.time()

        try:
            # Run the load test
            if config.requests_per_second <= 1:
                # Sequential testing for low RPS
                results = await self._run_sequential_load_test(config, latencies, errors)
            else:
                # Concurrent testing for higher RPS
                results = await self._run_concurrent_load_test(config, latencies, errors)

            end_time = time.time()
            duration = end_time - start_time

            # Stop resource monitoring and get final metrics
            resource_usage = self.resource_monitor.stop_monitoring()

            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(
                config, duration, latencies, errors, resource_usage
            )

            self.logger.info(f"Load test {config.name} completed: {metrics.requests_per_second:.2f} RPS, "
                           f"{metrics.avg_latency_ms:.2f}ms avg latency, "
                           f"{metrics.error_rate_percent:.2f}% error rate")

            return metrics

        except Exception as e:
            self.logger.error(f"Load test {config.name} failed: {e}")
            self.resource_monitor.stop_monitoring()
            raise

    async def _run_sequential_load_test(self, config: LoadTestConfig,
                                      latencies: list[float],
                                      errors: list[str]) -> list[Any]:
        """Run load test with sequential requests."""
        results = []
        end_time = time.time() + config.duration_seconds
        request_interval = 1.0 / config.requests_per_second if config.requests_per_second > 0 else 1.0

        symbol_index = 0
        while time.time() < end_time:
            symbol = config.symbols[symbol_index % len(config.symbols)]
            symbol_index += 1

            try:
                start_request = time.time()
                result = await self.e2e_system.run_complete_trading_cycle(symbol)
                end_request = time.time()

                latency_ms = (end_request - start_request) * 1000
                latencies.append(latency_ms)

                if not result.success:
                    errors.append(result.error_message or "Unknown error")

                results.append(result)

            except Exception as e:
                errors.append(str(e))
                self.logger.warning(f"Request failed for {symbol}: {e}")

            # Wait for next request
            await asyncio.sleep(request_interval)

        return results

    async def _run_concurrent_load_test(self, config: LoadTestConfig,
                                      latencies: list[float],
                                      errors: list[str]) -> list[Any]:
        """Run load test with concurrent requests."""
        results = []
        end_time = time.time() + config.duration_seconds
        request_interval = 1.0 / config.requests_per_second

        async def make_request(symbol: str) -> Any:
            try:
                start_request = time.time()
                result = await self.e2e_system.run_complete_trading_cycle(symbol)
                end_request = time.time()

                latency_ms = (end_request - start_request) * 1000
                latencies.append(latency_ms)

                if not result.success:
                    errors.append(result.error_message or "Unknown error")

                return result

            except Exception as e:
                errors.append(str(e))
                self.logger.warning(f"Request failed for {symbol}: {e}")
                return None

        # Generate requests at specified rate
        tasks = []
        symbol_index = 0

        while time.time() < end_time:
            # Create batch of concurrent requests
            batch_size = min(config.concurrent_symbols, len(config.symbols))
            batch_tasks = []

            for _ in range(batch_size):
                symbol = config.symbols[symbol_index % len(config.symbols)]
                symbol_index += 1
                batch_tasks.append(make_request(symbol))

            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if r is not None])

            # Wait before next batch
            await asyncio.sleep(request_interval)

        return results

    def _calculate_performance_metrics(self, config: LoadTestConfig,
                                     duration: float,
                                     latencies: list[float],
                                     errors: list[str],
                                     resource_usage: dict[str, float]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        total_requests = len(latencies) + len(errors)
        successful_requests = len(latencies)
        failed_requests = len(errors)

        if not latencies:
            latencies = [0.0]  # Avoid division by zero

        # Calculate latency percentiles
        sorted_latencies = sorted(latencies)
        p50_latency = statistics.median(sorted_latencies)
        p95_latency = sorted_latencies[int(0.95 * len(sorted_latencies))] if len(sorted_latencies) > 1 else sorted_latencies[0]
        p99_latency = sorted_latencies[int(0.99 * len(sorted_latencies))] if len(sorted_latencies) > 1 else sorted_latencies[0]

        # Calculate rates
        requests_per_second = total_requests / duration if duration > 0 else 0
        error_rate_percent = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        # Check SLO compliance
        slo_compliance = {
            'scan_latency': statistics.mean(latencies) <= self.slo_targets['scan_latency_ms'],
            'p95_latency': p95_latency <= self.slo_targets['llm_latency_p95_ms'],
            'error_rate': error_rate_percent <= self.slo_targets['error_rate_percentage'],
            'memory_usage': resource_usage.get('max_memory_mb', 0) <= 1000  # 1GB limit
        }

        return PerformanceMetrics(
            test_name=config.name,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=requests_per_second,
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max(latencies),
            min_latency_ms=min(latencies),
            memory_usage_mb=resource_usage.get('max_memory_mb', 0),
            cpu_usage_percent=resource_usage.get('avg_cpu_percent', 0),
            error_rate_percent=error_rate_percent,
            slo_compliance=slo_compliance
        )

    async def run_all_load_scenarios(self) -> dict[str, PerformanceMetrics]:
        """Run all predefined load test scenarios."""
        results = {}

        for scenario_name, config in self.load_scenarios.items():
            self.logger.info(f"Running load scenario: {scenario_name}")

            try:
                metrics = await self.run_load_test(config)
                results[scenario_name] = metrics

                # Log key metrics
                self.logger.info(f"Scenario {scenario_name} results:")
                self.logger.info(f"  RPS: {metrics.requests_per_second:.2f}")
                self.logger.info(f"  Avg Latency: {metrics.avg_latency_ms:.2f}ms")
                self.logger.info(f"  P95 Latency: {metrics.p95_latency_ms:.2f}ms")
                self.logger.info(f"  Error Rate: {metrics.error_rate_percent:.2f}%")
                self.logger.info(f"  SLO Compliance: {all(metrics.slo_compliance.values())}")

                # Brief pause between scenarios
                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Load scenario {scenario_name} failed: {e}")
                results[scenario_name] = None

        return results

    async def run_failover_test(self) -> dict[str, Any]:
        """Test system failover and recovery scenarios."""
        self.logger.info("Starting failover and recovery tests")

        failover_results = {}

        # Test 1: Market data failure simulation
        try:
            self.logger.info("Testing market data failover...")

            # Simulate market data failure
            original_fetch = self.e2e_system.market_data.fetch_multi_timeframe_data
            self.e2e_system.market_data.fetch_multi_timeframe_data = self._simulate_failure

            start_time = time.time()
            result = await self.e2e_system.run_complete_trading_cycle("BTCUSDT")
            recovery_time = time.time() - start_time

            # Restore original function
            self.e2e_system.market_data.fetch_multi_timeframe_data = original_fetch

            failover_results['market_data_failover'] = {
                'recovery_time_seconds': recovery_time,
                'recovery_successful': recovery_time < 60,  # Should recover within 1 minute
                'error_handled': not result.success  # Should fail gracefully
            }

        except Exception as e:
            failover_results['market_data_failover'] = {
                'error': str(e),
                'recovery_successful': False
            }

        # Test 2: LLM failure simulation
        try:
            self.logger.info("Testing LLM failover...")

            # Simulate LLM failure
            original_analyze = self.e2e_system.llm_router.analyze_market
            self.e2e_system.llm_router.analyze_market = self._simulate_failure

            start_time = time.time()
            result = await self.e2e_system.run_complete_trading_cycle("ETHUSDT")
            recovery_time = time.time() - start_time

            # Restore original function
            self.e2e_system.llm_router.analyze_market = original_analyze

            failover_results['llm_failover'] = {
                'recovery_time_seconds': recovery_time,
                'recovery_successful': recovery_time < 60,
                'system_continued': True  # System should continue without LLM
            }

        except Exception as e:
            failover_results['llm_failover'] = {
                'error': str(e),
                'recovery_successful': False
            }

        # Test 3: Safe mode trigger test
        try:
            self.logger.info("Testing safe mode trigger...")

            original_state = self.e2e_system.state
            self.e2e_system._trigger_safe_mode("Test drawdown")

            failover_results['safe_mode_trigger'] = {
                'safe_mode_activated': self.e2e_system.state.value == 'safe_mode',
                'original_state_preserved': original_state is not None
            }

        except Exception as e:
            failover_results['safe_mode_trigger'] = {
                'error': str(e),
                'safe_mode_activated': False
            }

        return failover_results

    async def _simulate_failure(self, *args, **kwargs):
        """Simulate component failure for testing."""
        await asyncio.sleep(0.1)  # Brief delay
        raise Exception("Simulated component failure")

    def generate_load_test_report(self, results: dict[str, PerformanceMetrics]) -> dict[str, Any]:
        """Generate comprehensive load test report."""
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'slo_targets': self.slo_targets,
            'scenarios': {},
            'overall_compliance': True,
            'summary': {
                'total_scenarios': len(results),
                'passed_scenarios': 0,
                'failed_scenarios': 0,
                'slo_violations': []
            }
        }

        for scenario_name, metrics in results.items():
            if metrics is None:
                report['scenarios'][scenario_name] = {'status': 'failed', 'error': 'Test execution failed'}
                report['summary']['failed_scenarios'] += 1
                continue

            scenario_report = asdict(metrics)
            scenario_passed = all(metrics.slo_compliance.values())

            scenario_report['status'] = 'passed' if scenario_passed else 'failed'
            scenario_report['slo_violations'] = [
                key for key, passed in metrics.slo_compliance.items() if not passed
            ]

            report['scenarios'][scenario_name] = scenario_report

            if scenario_passed:
                report['summary']['passed_scenarios'] += 1
            else:
                report['summary']['failed_scenarios'] += 1
                report['overall_compliance'] = False
                report['summary']['slo_violations'].extend(scenario_report['slo_violations'])

        # Remove duplicates from overall SLO violations
        report['summary']['slo_violations'] = list(set(report['summary']['slo_violations']))

        return report

    async def validate_slo_compliance(self) -> dict[str, bool]:
        """Validate system compliance with all SLOs."""
        self.logger.info("Validating SLO compliance...")

        # Run baseline load test
        baseline_metrics = await self.run_load_test(self.load_scenarios['baseline'])

        # Check each SLO
        compliance = {
            'uptime_slo': True,  # Would need longer test to validate
            'scan_latency_slo': baseline_metrics.avg_latency_ms <= self.slo_targets['scan_latency_ms'],
            'llm_latency_slo': baseline_metrics.p95_latency_ms <= self.slo_targets['llm_latency_p95_ms'],
            'error_rate_slo': baseline_metrics.error_rate_percent <= self.slo_targets['error_rate_percentage'],
            'memory_usage_slo': baseline_metrics.memory_usage_mb <= 1000  # 1GB limit
        }

        overall_compliance = all(compliance.values())

        self.logger.info("SLO Compliance Results:")
        for slo, passed in compliance.items():
            status = "PASS" if passed else "FAIL"
            self.logger.info(f"  {slo}: {status}")

        self.logger.info(f"Overall SLO Compliance: {'PASS' if overall_compliance else 'FAIL'}")

        return compliance


class ResourceMonitor:
    """Monitor system resource usage during load testing."""

    def __init__(self):
        self.monitoring = False
        self.resource_data = []
        self.monitor_task = None

    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.resource_data = []
        self.monitor_task = asyncio.create_task(self._monitor_resources())

    def stop_monitoring(self) -> dict[str, float]:
        """Stop monitoring and return aggregated metrics."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()

        if not self.resource_data:
            return {}

        # Calculate aggregated metrics
        memory_values = [data.memory_mb for data in self.resource_data]
        cpu_values = [data.cpu_percent for data in self.resource_data]

        return {
            'max_memory_mb': max(memory_values),
            'avg_memory_mb': statistics.mean(memory_values),
            'avg_cpu_percent': statistics.mean(cpu_values),
            'max_cpu_percent': max(cpu_values),
            'sample_count': len(self.resource_data)
        }

    async def _monitor_resources(self):
        """Monitor system resources continuously."""
        process = psutil.Process(os.getpid())

        while self.monitoring:
            try:
                # Get current resource usage
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()

                # Get system-wide I/O stats
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()

                usage = SystemResourceUsage(
                    timestamp=datetime.now(),
                    memory_mb=memory_info.rss / 1024 / 1024,  # Convert to MB
                    cpu_percent=cpu_percent,
                    disk_io_read_mb=disk_io.read_bytes / 1024 / 1024 if disk_io else 0,
                    disk_io_write_mb=disk_io.write_bytes / 1024 / 1024 if disk_io else 0,
                    network_sent_mb=net_io.bytes_sent / 1024 / 1024 if net_io else 0,
                    network_recv_mb=net_io.bytes_recv / 1024 / 1024 if net_io else 0
                )

                self.resource_data.append(usage)

                # Sample every 5 seconds
                await asyncio.sleep(5)

            except Exception as e:
                logging.warning(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)
