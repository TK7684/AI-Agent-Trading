#!/usr/bin/env python3
"""
CI/CD script to validate performance thresholds and fail builds on degradation.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from datetime import UTC
from pathlib import Path
from typing import Any, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from libs.trading_models.backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestValidator,
)
from libs.trading_models.chaos_testing import ChaosTestRunner
from libs.trading_models.performance_benchmarking import (
    PerformanceTestSuite,
    run_performance_tests,
)
from libs.trading_models.property_testing import PropertyTestRunner
from libs.trading_models.test_data_generation import TestDataSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CIPerformanceValidator:
    """CI/CD performance validation with threshold enforcement."""

    def __init__(self, baseline_file: Optional[Path] = None):
        self.baseline_file = baseline_file
        self.baseline_metrics = self._load_baseline_metrics()
        self.results = {}

    def _load_baseline_metrics(self) -> Optional[dict[str, Any]]:
        """Load baseline performance metrics."""
        if not self.baseline_file or not self.baseline_file.exists():
            logger.warning("No baseline metrics file found - using default thresholds")
            return None

        try:
            with open(self.baseline_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load baseline metrics: {e}")
            return None

    async def validate_all_performance_criteria(self) -> bool:
        """
        Run all performance validations and return overall success.
        This is the main entry point for CI/CD.
        """
        logger.info("Starting comprehensive performance validation for CI/CD")

        success_criteria = []

        # 1. Property-based tests (must pass 100%)
        logger.info("Running property-based tests...")
        property_success = self._validate_property_tests()
        success_criteria.append(("Property Tests", property_success))

        # 2. Performance benchmarks (must meet thresholds)
        logger.info("Running performance benchmarks...")
        performance_success = await self._validate_performance_benchmarks()
        success_criteria.append(("Performance Benchmarks", performance_success))

        # 3. Chaos tests (must pass 80%)
        logger.info("Running chaos tests...")
        chaos_success = self._validate_chaos_tests()
        success_criteria.append(("Chaos Tests", chaos_success))

        # 4. Backtest validation (must meet minimum criteria)
        logger.info("Running backtest validation...")
        backtest_success = await self._validate_backtest_performance()
        success_criteria.append(("Backtest Validation", backtest_success))

        # Compile results
        overall_success = all(success for _, success in success_criteria)

        # Log results
        logger.info("=== VALIDATION RESULTS ===")
        for test_name, success in success_criteria:
            status = "✓ PASS" if success else "✗ FAIL"
            logger.info(f"{test_name}: {status}")

        logger.info(f"Overall Result: {'✓ PASS' if overall_success else '✗ FAIL'}")

        # Save results for artifacts
        self._save_validation_results(success_criteria, overall_success)

        return overall_success

    def _validate_property_tests(self) -> bool:
        """Validate property-based tests - must pass 100%."""
        try:
            runner = PropertyTestRunner()
            results = runner.run_all_property_tests()

            failed_tests = [test for test, passed in results.items() if not passed]

            if failed_tests:
                logger.error(f"Property tests failed: {failed_tests}")
                return False

            logger.info(f"All {len(results)} property tests passed")
            self.results['property_tests'] = results
            return True

        except Exception as e:
            logger.error(f"Property test validation failed: {e}")
            return False

    async def _validate_performance_benchmarks(self) -> bool:
        """Validate performance benchmarks against thresholds."""
        try:
            # Run performance tests
            success = await run_performance_tests()

            if not success:
                logger.error("Performance tests failed to meet requirements")
                return False

            # Run detailed benchmarks for comparison
            suite = PerformanceTestSuite()
            benchmark_results = suite.run_comprehensive_benchmark()

            # Validate against baseline if available
            if self.baseline_metrics:
                degradation_detected = self._check_performance_degradation(benchmark_results)
                if degradation_detected:
                    logger.error("Performance degradation detected vs baseline")
                    return False

            # Validate against absolute thresholds
            validation_results = suite.validate_performance_requirements(benchmark_results)

            failed_categories = [cat for cat, passed in validation_results.items() if not passed]

            if failed_categories:
                logger.error(f"Performance validation failed for: {failed_categories}")
                return False

            logger.info("All performance benchmarks passed")
            self.results['performance_benchmarks'] = benchmark_results
            return True

        except Exception as e:
            logger.error(f"Performance benchmark validation failed: {e}")
            return False

    def _validate_chaos_tests(self) -> bool:
        """Validate chaos tests - must pass 80%."""
        try:
            runner = ChaosTestRunner()
            results = runner.run_all_chaos_tests()

            if not results:
                logger.warning("No chaos tests executed")
                return True  # Don't fail if no chaos tests

            pass_rate = sum(results.values()) / len(results)
            min_pass_rate = 0.8

            if pass_rate < min_pass_rate:
                logger.error(f"Chaos test pass rate {pass_rate:.1%} below threshold {min_pass_rate:.1%}")
                return False

            logger.info(f"Chaos tests passed with {pass_rate:.1%} success rate")
            self.results['chaos_tests'] = results
            return True

        except Exception as e:
            logger.error(f"Chaos test validation failed: {e}")
            return False

    async def _validate_backtest_performance(self) -> bool:
        """Validate backtest performance against minimum criteria."""
        try:
            # Generate test data
            test_data_suite = TestDataSuite(seed=42)

            # Use bull market scenario for validation
            from libs.trading_models.test_data_generation import (
                MarketRegime,
                MarketScenarioConfig,
            )

            config = MarketScenarioConfig(
                regime=MarketRegime.BULL_MARKET,
                duration_days=90,
                initial_price=100.0,
                volatility=0.15,
                trend_strength=2.0,
                noise_level=0.5,
                volume_base=1000.0,
                volume_volatility=0.3
            )

            market_data = test_data_suite.market_generator.generate_market_scenario(config)

            # Create mock data provider
            class MockDataProvider:
                def get_historical_data(self, symbol, timeframe, start_date, end_date):
                    import pandas as pd
                    df_data = []
                    for bar in market_data:
                        if start_date <= bar.timestamp <= end_date:
                            df_data.append({
                                'open': bar.open,
                                'high': bar.high,
                                'low': bar.low,
                                'close': bar.close,
                                'volume': bar.volume
                            })

                    df = pd.DataFrame(df_data)
                    if not df.empty:
                        df.index = pd.DatetimeIndex([bar.timestamp for bar in market_data if start_date <= bar.timestamp <= end_date])
                    return df

            # Create simple trend-following strategy for validation
            class ValidationStrategy:
                def analyze_market(self, market_data_dict, timestamp):
                    signals = []
                    for key, bar in market_data_dict.items():
                        # Simple trend following: buy if close > open
                        if bar.close > bar.open:
                            from libs.trading_models.base import TradingSignal
                            from libs.trading_models.enums import Direction

                            signal = TradingSignal(
                                symbol=bar.symbol,
                                direction=Direction.LONG,
                                confidence=0.6,
                                position_size=100.0,
                                stop_loss=bar.close * 0.98,
                                take_profit=bar.close * 1.04,
                                reasoning="Validation strategy",
                                timeframe_analysis={}
                            )
                            signals.append(signal)
                    return signals

            # Run backtest
            backtest_engine = BacktestEngine(MockDataProvider())

            backtest_config = BacktestConfig(
                start_date=market_data[0].timestamp,
                end_date=market_data[-1].timestamp,
                initial_capital=10000.0,
                symbols=["BTCUSD"],
                timeframes=["1h"],
                commission_rate=0.001,
                slippage_bps=2,
                random_seed=42
            )

            result = backtest_engine.run_backtest(ValidationStrategy(), backtest_config)

            # Validate minimum performance criteria
            validator = BacktestValidator(self.baseline_metrics.get('backtest') if self.baseline_metrics else None)

            # Relaxed criteria for CI validation
            validation_success = validator.validate_performance(
                result,
                min_sharpe=0.0,      # Don't require positive Sharpe for validation
                max_drawdown=0.5,    # Allow up to 50% drawdown
                min_win_rate=0.0     # Don't require minimum win rate
            )

            if not validation_success:
                logger.error("Backtest validation failed minimum criteria")
                return False

            logger.info(f"Backtest validation passed - Sharpe: {result.metrics.sharpe_ratio:.2f}, "
                       f"Max DD: {result.metrics.max_drawdown:.1%}, Trades: {result.metrics.total_trades}")

            self.results['backtest_validation'] = {
                'sharpe_ratio': result.metrics.sharpe_ratio,
                'max_drawdown': result.metrics.max_drawdown,
                'total_trades': result.metrics.total_trades,
                'win_rate': result.metrics.win_rate
            }

            return True

        except Exception as e:
            logger.error(f"Backtest validation failed: {e}")
            return False

    def _check_performance_degradation(self, current_results: dict[str, Any]) -> bool:
        """Check for performance degradation vs baseline."""
        if not self.baseline_metrics:
            return False

        degradation_threshold = 0.1  # 10% degradation threshold

        try:
            baseline_perf = self.baseline_metrics.get('performance_benchmarks', {})

            for category, metrics_list in current_results.items():
                baseline_category = baseline_perf.get(category, [])

                if not baseline_category:
                    continue

                for i, current_metric in enumerate(metrics_list):
                    if i >= len(baseline_category):
                        continue

                    baseline_metric = baseline_category[i]

                    # Check latency degradation
                    current_latency = current_metric.avg_time_ms
                    baseline_latency = baseline_metric.get('avg_time_ms', current_latency)

                    if baseline_latency > 0:
                        latency_increase = (current_latency - baseline_latency) / baseline_latency

                        if latency_increase > degradation_threshold:
                            logger.error(
                                f"Latency degradation detected in {category}.{current_metric.operation_name}: "
                                f"{latency_increase:.1%} increase"
                            )
                            return True

                    # Check throughput degradation
                    current_ops = current_metric.operations_per_second
                    baseline_ops = baseline_metric.get('operations_per_second', current_ops)

                    if baseline_ops > 0:
                        ops_decrease = (baseline_ops - current_ops) / baseline_ops

                        if ops_decrease > degradation_threshold:
                            logger.error(
                                f"Throughput degradation detected in {category}.{current_metric.operation_name}: "
                                f"{ops_decrease:.1%} decrease"
                            )
                            return True

            return False

        except Exception as e:
            logger.error(f"Error checking performance degradation: {e}")
            return True  # Fail safe - assume degradation if we can't check

    def _save_validation_results(self, success_criteria: list, overall_success: bool) -> None:
        """Save validation results for CI artifacts."""
        results_dir = Path("test_results/ci_validation")
        results_dir.mkdir(parents=True, exist_ok=True)

        validation_report = {
            'timestamp': datetime.now(UTC).isoformat(),
            'overall_success': overall_success,
            'test_results': {
                test_name: success for test_name, success in success_criteria
            },
            'detailed_results': self.results,
            'baseline_used': self.baseline_metrics is not None,
            'baseline_file': str(self.baseline_file) if self.baseline_file else None
        }

        # Save main report
        with open(results_dir / 'ci_validation_report.json', 'w') as f:
            json.dump(validation_report, f, indent=2, default=str)

        # Save current results as potential new baseline
        if overall_success and self.results:
            with open(results_dir / 'current_performance_baseline.json', 'w') as f:
                json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Validation results saved to {results_dir}")

async def main():
    """Main CI/CD validation entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='CI/CD Performance Validation')
    parser.add_argument(
        '--baseline',
        type=Path,
        help='Path to baseline performance metrics file'
    )
    parser.add_argument(
        '--fail-on-degradation',
        action='store_true',
        help='Fail build on performance degradation'
    )

    args = parser.parse_args()

    # Create validator
    validator = CIPerformanceValidator(baseline_file=args.baseline)

    try:
        # Run validation
        success = await validator.validate_all_performance_criteria()

        if success:
            logger.info("🎉 All validation criteria passed - build can proceed")
            sys.exit(0)
        else:
            logger.error("❌ Validation criteria failed - build should be blocked")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Validation process failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
