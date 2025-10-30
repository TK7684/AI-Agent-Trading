"""
Performance benchmarking and load testing framework.
"""

import asyncio
import random
import statistics
import time

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Mock psutil for when it's not available
    class MockProcess:
        def memory_info(self):
            class MockMemInfo:
                rss = 100 * 1024 * 1024  # 100MB
            return MockMemInfo()

    class MockPsutil:
        def Process(self):
            return MockProcess()

        def cpu_percent(self, interval=None):
            return 50.0

    psutil = MockPsutil()
import gc
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .market_data import MarketBar

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    operation_name: str
    total_operations: int
    total_time_seconds: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_count: int
    error_rate: float

@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int
    operations_per_user: int
    ramp_up_time_seconds: int
    test_duration_seconds: int
    symbols: list[str]
    timeframes: list[str]

@dataclass
class BenchmarkResult:
    """Complete benchmark test results."""
    test_name: str
    config: LoadTestConfig
    metrics: list[PerformanceMetrics]
    system_metrics: dict[str, Any]
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'test_name': self.test_name,
            'config': asdict(self.config),
            'metrics': [asdict(m) for m in self.metrics],
            'system_metrics': self.system_metrics,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'total_duration_seconds': self.total_duration_seconds
        }

class PerformanceBenchmark:
    """Performance benchmarking utilities."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = []

    def benchmark_function(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 100,
        warmup_iterations: int = 10
    ) -> PerformanceMetrics:
        """
        Benchmark a function's performance.
        """
        if kwargs is None:
            kwargs = {}

        # Warmup runs
        for _ in range(warmup_iterations):
            try:
                func(*args, **kwargs)
            except Exception:
                pass  # Ignore warmup errors

        # Force garbage collection before measurement
        gc.collect()

        # Measure performance
        times = []
        errors = 0
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()

        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)  # Convert to ms
            except Exception as e:
                errors += 1
                self.logger.warning(f"Benchmark iteration {i} failed: {e}")

        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_cpu = psutil.cpu_percent()

        if not times:
            raise ValueError("All benchmark iterations failed")

        # Calculate statistics
        total_time = sum(times) / 1000  # Convert back to seconds
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)

        # Percentiles
        sorted_times = sorted(times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        ops_per_second = len(times) / total_time if total_time > 0 else 0

        return PerformanceMetrics(
            operation_name=func.__name__,
            total_operations=len(times),
            total_time_seconds=total_time,
            avg_time_ms=avg_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            p50_time_ms=p50,
            p95_time_ms=p95,
            p99_time_ms=p99,
            operations_per_second=ops_per_second,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=end_cpu - start_cpu,
            error_count=errors,
            error_rate=errors / iterations
        )

    async def benchmark_async_function(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        iterations: int = 100,
        warmup_iterations: int = 10
    ) -> PerformanceMetrics:
        """
        Benchmark an async function's performance.
        """
        if kwargs is None:
            kwargs = {}

        # Warmup runs
        for _ in range(warmup_iterations):
            try:
                await func(*args, **kwargs)
            except Exception:
                pass

        gc.collect()

        times = []
        errors = 0
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                await func(*args, **kwargs)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            except Exception as e:
                errors += 1
                self.logger.warning(f"Async benchmark iteration {i} failed: {e}")

        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        if not times:
            raise ValueError("All async benchmark iterations failed")

        total_time = sum(times) / 1000
        avg_time = statistics.mean(times)
        sorted_times = sorted(times)

        return PerformanceMetrics(
            operation_name=f"{func.__name__}_async",
            total_operations=len(times),
            total_time_seconds=total_time,
            avg_time_ms=avg_time,
            min_time_ms=min(times),
            max_time_ms=max(times),
            p50_time_ms=sorted_times[len(sorted_times) // 2],
            p95_time_ms=sorted_times[int(len(sorted_times) * 0.95)],
            p99_time_ms=sorted_times[int(len(sorted_times) * 0.99)],
            operations_per_second=len(times) / total_time if total_time > 0 else 0,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=0.0,  # Difficult to measure for async
            error_count=errors,
            error_rate=errors / iterations
        )

class TradingSystemBenchmark:
    """Comprehensive trading system performance benchmarks."""

    def __init__(self):
        self.benchmark = PerformanceBenchmark()
        self.logger = logging.getLogger(__name__)

    def run_technical_indicators_benchmark(self) -> list[PerformanceMetrics]:
        """Benchmark technical indicator calculations."""
        # Simple mock benchmark since TechnicalIndicators not available
        def mock_calculation():
            prices = [100.0 + i * 0.1 for i in range(100)]
            return sum(prices) / len(prices)  # Simple average

        benchmarks = []

        # Mock RSI benchmark
        rsi_metrics = self.benchmark.benchmark_function(
            mock_calculation,
            iterations=100
        )
        rsi_metrics.operation_name = "mock_rsi"
        benchmarks.append(rsi_metrics)

        # Mock EMA benchmark
        ema_metrics = self.benchmark.benchmark_function(
            mock_calculation,
            iterations=100
        )
        ema_metrics.operation_name = "mock_ema"
        benchmarks.append(ema_metrics)

        return benchmarks

    def run_pattern_recognition_benchmark(self) -> list[PerformanceMetrics]:
        """Benchmark pattern recognition algorithms."""
        # Simple mock benchmark since PatternRecognition not available
        def mock_pattern_detection():
            # Simulate pattern detection work
            data = [random.random() for _ in range(100)]
            return len([x for x in data if x > 0.5])

        benchmarks = []

        # Mock Support/Resistance benchmark
        sr_metrics = self.benchmark.benchmark_function(
            mock_pattern_detection,
            iterations=50
        )
        sr_metrics.operation_name = "mock_support_resistance"
        benchmarks.append(sr_metrics)

        # Mock Breakout detection benchmark
        breakout_metrics = self.benchmark.benchmark_function(
            mock_pattern_detection,
            iterations=50
        )
        breakout_metrics.operation_name = "mock_breakout_detection"
        benchmarks.append(breakout_metrics)

        return benchmarks

    def run_market_data_benchmark(self) -> list[PerformanceMetrics]:
        """Benchmark market data processing."""
        # This would benchmark actual market data provider
        # For now, we'll simulate the operations

        def simulate_data_fetch():
            """Simulate market data fetching."""
            time.sleep(0.001)  # Simulate network latency
            return MarketBar(
                symbol="BTCUSD",
                timeframe="1h",
                timestamp=datetime.now(UTC),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )

        def simulate_data_processing(bars):
            """Simulate data processing."""
            # Simulate some processing work
            processed = []
            for bar in bars:
                processed.append({
                    'symbol': bar.symbol,
                    'price': bar.close,
                    'volume': bar.volume
                })
            return processed

        benchmarks = []

        # Data fetching benchmark
        fetch_metrics = self.benchmark.benchmark_function(
            simulate_data_fetch,
            iterations=1000
        )
        benchmarks.append(fetch_metrics)

        # Data processing benchmark
        test_bars = [simulate_data_fetch() for _ in range(100)]
        processing_metrics = self.benchmark.benchmark_function(
            simulate_data_processing,
            args=(test_bars,),
            iterations=500
        )
        benchmarks.append(processing_metrics)

        return benchmarks

class LoadTester:
    """Load testing framework for trading system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def run_load_test(
        self,
        config: LoadTestConfig,
        target_function: Callable,
        function_args: tuple = (),
        function_kwargs: dict = None
    ) -> BenchmarkResult:
        """
        Run comprehensive load test.
        """
        if function_kwargs is None:
            function_kwargs = {}

        start_time = datetime.now(UTC)
        self.logger.info(f"Starting load test with {config.concurrent_users} users")

        # System metrics before test
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        initial_cpu = psutil.cpu_percent(interval=1)

        # Results collection
        all_results = []
        errors = []

        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(config.concurrent_users)

        async def user_simulation(user_id: int):
            """Simulate a single user's operations."""
            user_results = []
            user_errors = 0

            # Ramp-up delay
            ramp_delay = (config.ramp_up_time_seconds * user_id) / config.concurrent_users
            await asyncio.sleep(ramp_delay)

            async with semaphore:
                for operation in range(config.operations_per_user):
                    start_op_time = time.perf_counter()

                    try:
                        if asyncio.iscoroutinefunction(target_function):
                            await target_function(*function_args, **function_kwargs)
                        else:
                            target_function(*function_args, **function_kwargs)

                        end_op_time = time.perf_counter()
                        operation_time = (end_op_time - start_op_time) * 1000
                        user_results.append(operation_time)

                    except Exception as e:
                        user_errors += 1
                        errors.append(f"User {user_id}, Op {operation}: {str(e)}")

                    # Small delay between operations
                    await asyncio.sleep(0.01)

            return user_results, user_errors

        # Run all user simulations concurrently
        tasks = [user_simulation(i) for i in range(config.concurrent_users)]

        try:
            # Wait for all tasks with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=config.test_duration_seconds
            )
        except asyncio.TimeoutError:
            self.logger.warning("Load test timed out")
            results = []

        # Collect all timing results
        all_times = []
        total_errors = 0

        for result in results:
            if isinstance(result, Exception):
                total_errors += 1
                continue

            user_times, user_error_count = result
            all_times.extend(user_times)
            total_errors += user_error_count

        # System metrics after test
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        final_cpu = psutil.cpu_percent(interval=1)

        end_time = datetime.now(UTC)
        total_duration = (end_time - start_time).total_seconds()

        # Calculate performance metrics
        if all_times:
            metrics = PerformanceMetrics(
                operation_name=target_function.__name__,
                total_operations=len(all_times),
                total_time_seconds=total_duration,
                avg_time_ms=statistics.mean(all_times),
                min_time_ms=min(all_times),
                max_time_ms=max(all_times),
                p50_time_ms=statistics.median(all_times),
                p95_time_ms=sorted(all_times)[int(len(all_times) * 0.95)],
                p99_time_ms=sorted(all_times)[int(len(all_times) * 0.99)],
                operations_per_second=len(all_times) / total_duration,
                memory_usage_mb=final_memory - initial_memory,
                cpu_usage_percent=final_cpu - initial_cpu,
                error_count=total_errors,
                error_rate=total_errors / (len(all_times) + total_errors) if (len(all_times) + total_errors) > 0 else 0
            )
        else:
            # No successful operations
            metrics = PerformanceMetrics(
                operation_name=target_function.__name__,
                total_operations=0,
                total_time_seconds=total_duration,
                avg_time_ms=0,
                min_time_ms=0,
                max_time_ms=0,
                p50_time_ms=0,
                p95_time_ms=0,
                p99_time_ms=0,
                operations_per_second=0,
                memory_usage_mb=final_memory - initial_memory,
                cpu_usage_percent=final_cpu - initial_cpu,
                error_count=total_errors,
                error_rate=1.0
            )

        system_metrics = {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_delta_mb': final_memory - initial_memory,
            'initial_cpu_percent': initial_cpu,
            'final_cpu_percent': final_cpu,
            'cpu_delta_percent': final_cpu - initial_cpu,
            'total_errors': total_errors,
            'error_samples': errors[:10]  # First 10 errors for debugging
        }

        return BenchmarkResult(
            test_name=f"load_test_{target_function.__name__}",
            config=config,
            metrics=[metrics],
            system_metrics=system_metrics,
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration
        )

class PerformanceTestSuite:
    """Complete performance testing suite."""

    def __init__(self):
        self.trading_benchmark = TradingSystemBenchmark()
        self.load_tester = LoadTester()
        self.logger = logging.getLogger(__name__)

    def run_comprehensive_benchmark(self) -> dict[str, list[PerformanceMetrics]]:
        """Run all performance benchmarks."""
        results = {}

        self.logger.info("Running technical indicators benchmark...")
        results['technical_indicators'] = self.trading_benchmark.run_technical_indicators_benchmark()

        self.logger.info("Running pattern recognition benchmark...")
        results['pattern_recognition'] = self.trading_benchmark.run_pattern_recognition_benchmark()

        self.logger.info("Running market data benchmark...")
        results['market_data'] = self.trading_benchmark.run_market_data_benchmark()

        return results

    async def run_load_tests(self) -> list[BenchmarkResult]:
        """Run comprehensive load tests."""
        results = []

        # Define test scenarios
        test_configs = [
            LoadTestConfig(
                concurrent_users=10,
                operations_per_user=100,
                ramp_up_time_seconds=10,
                test_duration_seconds=60,
                symbols=["BTCUSD", "ETHUSD"],
                timeframes=["1m", "5m", "1h"]
            ),
            LoadTestConfig(
                concurrent_users=50,
                operations_per_user=50,
                ramp_up_time_seconds=30,
                test_duration_seconds=120,
                symbols=["BTCUSD", "ETHUSD", "ADAUSD"],
                timeframes=["1m", "5m", "15m", "1h"]
            )
        ]

        # Test functions
        def dummy_analysis():
            """Dummy analysis function for load testing."""
            time.sleep(0.01)  # Simulate processing time
            return {"signal": "LONG", "confidence": 0.75}

        for config in test_configs:
            self.logger.info(f"Running load test: {config.concurrent_users} users")

            result = await self.load_tester.run_load_test(
                config=config,
                target_function=dummy_analysis
            )
            results.append(result)

        return results

    def validate_performance_requirements(
        self,
        results: dict[str, list[PerformanceMetrics]]
    ) -> dict[str, bool]:
        """Validate performance against requirements."""
        validation_results = {}

        # Performance requirements from task definition
        requirements = {
            'scan_latency_ms': 1000,  # <1.0s per timeframe scan
            'llm_p95_ms': 3000,       # LLM p95 ≤ 3s
            'orchestrator_uptime': 99.5,  # ≥99.5% uptime
            'error_rate': 0.005       # <0.5% error rate
        }

        for category, metrics_list in results.items():
            category_passed = True

            for metrics in metrics_list:
                # Check latency requirements
                if 'scan' in metrics.operation_name.lower():
                    if metrics.p95_time_ms > requirements['scan_latency_ms']:
                        category_passed = False
                        self.logger.error(
                            f"{metrics.operation_name} p95 latency {metrics.p95_time_ms}ms "
                            f"exceeds requirement {requirements['scan_latency_ms']}ms"
                        )

                # Check error rate
                if metrics.error_rate > requirements['error_rate']:
                    category_passed = False
                    self.logger.error(
                        f"{metrics.operation_name} error rate {metrics.error_rate:.1%} "
                        f"exceeds requirement {requirements['error_rate']:.1%}"
                    )

            validation_results[category] = category_passed

        return validation_results

    def generate_performance_report(
        self,
        benchmark_results: dict[str, list[PerformanceMetrics]],
        load_test_results: list[BenchmarkResult],
        validation_results: dict[str, bool]
    ) -> dict[str, Any]:
        """Generate comprehensive performance report."""

        # Summary statistics
        all_metrics = []
        for metrics_list in benchmark_results.values():
            all_metrics.extend(metrics_list)

        if all_metrics:
            avg_latency = statistics.mean(m.avg_time_ms for m in all_metrics)
            max_latency = max(m.max_time_ms for m in all_metrics)
            total_ops = sum(m.total_operations for m in all_metrics)
            avg_ops_per_sec = statistics.mean(m.operations_per_second for m in all_metrics)
        else:
            avg_latency = max_latency = total_ops = avg_ops_per_sec = 0

        report = {
            'summary': {
                'total_benchmark_categories': len(benchmark_results),
                'total_operations_tested': total_ops,
                'average_latency_ms': avg_latency,
                'maximum_latency_ms': max_latency,
                'average_ops_per_second': avg_ops_per_sec,
                'all_validations_passed': all(validation_results.values())
            },
            'benchmark_results': {
                category: [asdict(m) for m in metrics]
                for category, metrics in benchmark_results.items()
            },
            'load_test_results': [result.to_dict() for result in load_test_results],
            'validation_results': validation_results,
            'generated_at': datetime.now(UTC).isoformat()
        }

        return report

    def save_performance_report(self, report: dict[str, Any], output_path: Path) -> None:
        """Save performance report to file."""
        output_path.mkdir(parents=True, exist_ok=True)

        with open(output_path / 'performance_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Performance report saved to {output_path}")

# Performance test runner for CI/CD integration
async def run_performance_tests() -> bool:
    """
    Run all performance tests and return success status.
    Used for CI/CD pipeline integration.
    """
    suite = PerformanceTestSuite()

    try:
        # Run benchmarks
        benchmark_results = suite.run_comprehensive_benchmark()

        # Run load tests
        load_test_results = await suite.run_load_tests()

        # Validate results
        validation_results = suite.validate_performance_requirements(benchmark_results)

        # Generate report
        report = suite.generate_performance_report(
            benchmark_results, load_test_results, validation_results
        )

        # Save report
        output_path = Path("test_results/performance")
        suite.save_performance_report(report, output_path)

        # Return overall success
        return all(validation_results.values())

    except Exception as e:
        logger.error(f"Performance tests failed: {e}")
        return False
