#!/usr/bin/env python3
"""
End-to-End Integration Demo
Demonstrates complete system integration and validates all requirements.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from libs.trading_models.deployment_manager import DeploymentConfig, DeploymentManager
from libs.trading_models.e2e_integration import E2EIntegrationSystem
from libs.trading_models.load_testing import LoadTestingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_integration_demo.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class E2EIntegrationDemo:
    """Comprehensive end-to-end integration demonstration."""

    def __init__(self):
        self.config = self._load_demo_config()
        self.results = {
            'demo_start_time': datetime.now().isoformat(),
            'system_startup': None,
            'trading_cycles': [],
            'load_tests': {},
            'deployment_tests': {},
            'failover_tests': {},
            'slo_validation': {},
            'overall_success': False
        }

    def _load_demo_config(self) -> dict:
        """Load demo configuration."""
        return {
            'system': {
                'market_data': {
                    'sources': ['mock_binance'],
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                    'timeframes': ['15m', '1h', '4h', '1d'],
                    'mock_mode': True
                },
                'llm': {
                    'models': ['mock_claude', 'mock_gpt4'],
                    'routing_policy': 'AccuracyFirst',
                    'mock_mode': True
                },
                'risk': {
                    'max_position_size': 0.02,
                    'max_portfolio_risk': 0.20,
                    'safe_mode_drawdown': 0.08
                },
                'orchestrator': {
                    'check_interval': 60,  # 1 minute for demo
                    'symbols': ['BTCUSDT', 'ETHUSDT']
                },
                'persistence': {
                    'database_url': 'sqlite:///demo_e2e.db'
                },
                'monitoring': {
                    'metrics_enabled': True,
                    'alerts_enabled': True
                }
            },
            'demo': {
                'run_load_tests': True,
                'run_deployment_tests': True,
                'run_failover_tests': True,
                'validate_slos': True,
                'symbols_to_test': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                'test_duration_minutes': 5
            }
        }

    async def run_complete_demo(self):
        """Run the complete end-to-end integration demo."""
        logger.info("Starting E2E Integration Demo")
        logger.info("=" * 60)

        try:
            # Step 1: Initialize and start system
            logger.info("Step 1: System Initialization and Startup")
            e2e_system = await self._initialize_system()
            if not e2e_system:
                logger.error("System initialization failed")
                return False

            # Step 2: Test basic trading cycles
            logger.info("\nStep 2: Basic Trading Cycle Tests")
            await self._test_trading_cycles(e2e_system)

            # Step 3: Load testing
            if self.config['demo']['run_load_tests']:
                logger.info("\nStep 3: Load Testing")
                await self._run_load_tests(e2e_system)

            # Step 4: Deployment testing
            if self.config['demo']['run_deployment_tests']:
                logger.info("\nStep 4: Deployment Testing")
                await self._test_deployments(e2e_system)

            # Step 5: Failover testing
            if self.config['demo']['run_failover_tests']:
                logger.info("\nStep 5: Failover and Recovery Testing")
                await self._test_failover_scenarios(e2e_system)

            # Step 6: SLO validation
            if self.config['demo']['validate_slos']:
                logger.info("\nStep 6: SLO Validation")
                await self._validate_slos(e2e_system)

            # Step 7: Generate final report
            logger.info("\nStep 7: Generating Final Report")
            await self._generate_final_report()

            # Step 8: Cleanup
            logger.info("\nStep 8: System Cleanup")
            await self._cleanup_system(e2e_system)

            self.results['overall_success'] = True
            logger.info("\n" + "=" * 60)
            logger.info("E2E Integration Demo completed successfully!")

            return True

        except Exception as e:
            logger.error(f"Demo failed with error: {e}")
            self.results['error'] = str(e)
            return False
        finally:
            self.results['demo_end_time'] = datetime.now().isoformat()

    async def _initialize_system(self) -> E2EIntegrationSystem:
        """Initialize the E2E system with mock components."""
        try:
            logger.info("Initializing E2E Integration System...")

            # Create system with demo config
            e2e_system = E2EIntegrationSystem(self.config['system'])

            # Mock external dependencies for demo
            await self._setup_mock_components(e2e_system)

            # Start the system
            startup_success = await e2e_system.start_system()

            self.results['system_startup'] = {
                'success': startup_success,
                'timestamp': datetime.now().isoformat(),
                'component_health': e2e_system.component_health
            }

            if startup_success:
                logger.info("✓ System started successfully")

                # Display system status
                status = e2e_system.get_system_status()
                logger.info(f"  State: {status['state']}")
                logger.info(f"  Components healthy: {len([h for h in status['component_health'].values() if h['healthy']])}/{len(status['component_health'])}")

                return e2e_system
            else:
                logger.error("✗ System startup failed")
                return None

        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.results['system_startup'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return None

    async def _setup_mock_components(self, e2e_system: E2EIntegrationSystem):
        """Set up mock components for demo."""
        from unittest.mock import AsyncMock, Mock

        # Mock market data with realistic responses
        mock_market_data = {
            "15m": [{"open": 50000, "high": 50100, "low": 49900, "close": 50050, "volume": 100}] * 96,  # 24 hours
            "1h": [{"open": 49800, "high": 50200, "low": 49700, "close": 50050, "volume": 400}] * 24,   # 24 hours
            "4h": [{"open": 49500, "high": 50300, "low": 49400, "close": 50050, "volume": 1600}] * 6,   # 24 hours
            "1d": [{"open": 48000, "high": 51000, "low": 47500, "close": 50050, "volume": 6400}] * 1    # 1 day
        }

        # Mock indicators
        mock_indicators = {
            "15m": {"rsi": 65, "ema_20": 49950, "macd": 0.5, "bb_upper": 50100, "bb_lower": 49900},
            "1h": {"rsi": 62, "ema_20": 49900, "macd": 0.3, "bb_upper": 50150, "bb_lower": 49850},
            "4h": {"rsi": 58, "ema_20": 49800, "macd": 0.1, "bb_upper": 50200, "bb_lower": 49800},
            "1d": {"rsi": 55, "ema_20": 49500, "macd": -0.1, "bb_upper": 50500, "bb_lower": 49500}
        }

        # Mock patterns
        mock_patterns = {
            "15m": [{"type": "bullish_engulfing", "confidence": 0.8, "strength": 0.7}],
            "1h": [{"type": "support_break", "confidence": 0.7, "strength": 0.6}],
            "4h": [{"type": "trend_continuation", "confidence": 0.6, "strength": 0.5}],
            "1d": [{"type": "breakout", "confidence": 0.8, "strength": 0.8}]
        }

        # Set up mocks
        e2e_system.market_data.fetch_multi_timeframe_data = AsyncMock(return_value=mock_market_data)
        e2e_system.market_data.fetch_ohlcv = AsyncMock(return_value=mock_market_data["1h"])

        def mock_calculate_indicators(timeframe_data):
            # Return indicators based on timeframe
            for tf, data in mock_market_data.items():
                if data == timeframe_data:
                    return mock_indicators.get(tf, mock_indicators["1h"])
            return mock_indicators["1h"]

        e2e_system.indicators.calculate_all_indicators = Mock(side_effect=mock_calculate_indicators)

        def mock_detect_patterns(timeframe_data, indicators):
            # Return patterns based on timeframe
            for tf, data in mock_market_data.items():
                if data == timeframe_data:
                    return mock_patterns.get(tf, [])
            return []

        e2e_system.patterns.detect_all_patterns = Mock(side_effect=mock_detect_patterns)

        # Mock confluence scoring
        mock_confluence = Mock()
        mock_confluence.direction = "LONG"
        mock_confluence.confidence = 0.75
        mock_confluence.score = 72.5
        mock_confluence.reasoning = "Strong bullish confluence across multiple timeframes"
        mock_confluence.timeframe_analysis = {"15m": 0.8, "1h": 0.7, "4h": 0.6, "1d": 0.8}

        e2e_system.confluence.calculate_confluence_score = Mock(return_value=mock_confluence)

        # Mock LLM responses
        e2e_system.llm_router.analyze_market = AsyncMock(return_value={
            "analysis": "Bullish momentum building across timeframes",
            "confidence": 0.75,
            "key_factors": ["RSI showing strength", "Breakout pattern confirmed", "Volume supporting move"]
        })

        # Mock portfolio and risk management
        from libs.trading_models.base import Portfolio
        mock_portfolio = Portfolio(
            total_equity=10000.0,
            available_margin=5000.0,
            positions=[],
            daily_pnl=0.0,
            unrealized_pnl=0.0
        )

        e2e_system.persistence.get_current_portfolio = AsyncMock(return_value=mock_portfolio)

        mock_risk_assessment = Mock()
        mock_risk_assessment.approved = True
        mock_risk_assessment.position_size = 0.1
        mock_risk_assessment.stop_loss = 49500
        mock_risk_assessment.take_profit = 51000
        mock_risk_assessment.risk_reward_ratio = 2.0

        e2e_system.risk_manager.assess_trade_risk = Mock(return_value=mock_risk_assessment)

        # Mock execution (disabled for demo safety)
        e2e_system.orchestrator.execute_trade = AsyncMock(return_value=None)  # No actual execution

        # Mock persistence
        e2e_system.persistence.record_trading_cycle = AsyncMock()
        e2e_system.persistence.health_check = AsyncMock()

        # Mock monitoring
        e2e_system.monitoring.record_metric = Mock()
        e2e_system.monitoring.send_alert = Mock()

        # Mock feature flags
        e2e_system.feature_flags.is_enabled = Mock(return_value=True)

        logger.info("✓ Mock components configured")

    async def _test_trading_cycles(self, e2e_system: E2EIntegrationSystem):
        """Test basic trading cycles for multiple symbols."""
        symbols = self.config['demo']['symbols_to_test']

        for symbol in symbols:
            logger.info(f"Testing trading cycle for {symbol}...")

            start_time = time.time()
            result = await e2e_system.run_complete_trading_cycle(symbol)
            duration = time.time() - start_time

            cycle_result = {
                'symbol': symbol,
                'success': result.success,
                'duration_ms': result.duration_ms,
                'test_duration_s': duration,
                'error_message': result.error_message,
                'timestamp': datetime.now().isoformat()
            }

            self.results['trading_cycles'].append(cycle_result)

            if result.success:
                logger.info(f"  ✓ {symbol}: {result.duration_ms:.1f}ms")
            else:
                logger.warning(f"  ✗ {symbol}: {result.error_message}")

        successful_cycles = len([r for r in self.results['trading_cycles'] if r['success']])
        logger.info(f"Trading cycles completed: {successful_cycles}/{len(symbols)} successful")

    async def _run_load_tests(self, e2e_system: E2EIntegrationSystem):
        """Run comprehensive load tests."""
        load_tester = LoadTestingSystem(e2e_system)

        # Run selected load scenarios
        scenarios_to_run = ['baseline', 'moderate_load']

        for scenario_name in scenarios_to_run:
            logger.info(f"Running load test: {scenario_name}")

            try:
                config = load_tester.load_scenarios[scenario_name]
                # Reduce duration for demo
                config.duration_seconds = min(config.duration_seconds, 120)  # Max 2 minutes

                metrics = await load_tester.run_load_test(config)

                self.results['load_tests'][scenario_name] = {
                    'success': True,
                    'metrics': {
                        'requests_per_second': metrics.requests_per_second,
                        'avg_latency_ms': metrics.avg_latency_ms,
                        'p95_latency_ms': metrics.p95_latency_ms,
                        'error_rate_percent': metrics.error_rate_percent,
                        'slo_compliance': metrics.slo_compliance
                    }
                }

                logger.info(f"  ✓ {scenario_name}: {metrics.requests_per_second:.1f} RPS, "
                           f"{metrics.avg_latency_ms:.1f}ms avg, "
                           f"{metrics.error_rate_percent:.1f}% errors")

            except Exception as e:
                logger.error(f"  ✗ {scenario_name}: {e}")
                self.results['load_tests'][scenario_name] = {
                    'success': False,
                    'error': str(e)
                }

        # Validate SLO compliance
        slo_validation = await load_tester.validate_slo_compliance()
        self.results['load_tests']['slo_compliance'] = slo_validation

        compliant_slos = len([slo for slo, passed in slo_validation.items() if passed])
        logger.info(f"SLO Compliance: {compliant_slos}/{len(slo_validation)} SLOs met")

    async def _test_deployments(self, e2e_system: E2EIntegrationSystem):
        """Test deployment scenarios including blue/green and canary."""
        from libs.trading_models.monitoring import MonitoringSystem

        monitoring = MonitoringSystem({})
        deployment_manager = DeploymentManager(e2e_system, monitoring)

        # Test canary deployment
        logger.info("Testing canary deployment...")

        canary_config = DeploymentConfig(
            version="v1.2.0-demo",
            environment="staging",
            canary_percentage=10.0,
            canary_duration_minutes=1,  # Short for demo
            max_error_rate=0.05,
            max_latency_ms=2000,
            rollback_threshold_errors=3,
            health_check_interval_seconds=10,
            feature_flags={
                "new_indicator": True,
                "enhanced_patterns": True,
                "demo_mode": True
            }
        )

        try:
            deployment_success = await deployment_manager.deploy_version(canary_config)

            self.results['deployment_tests']['canary_deployment'] = {
                'success': deployment_success,
                'version': canary_config.version,
                'canary_percentage': canary_config.canary_percentage,
                'deployment_status': deployment_manager.get_deployment_status()
            }

            if deployment_success:
                logger.info("  ✓ Canary deployment successful")
            else:
                logger.warning("  ✗ Canary deployment failed or rolled back")

        except Exception as e:
            logger.error(f"  ✗ Canary deployment error: {e}")
            self.results['deployment_tests']['canary_deployment'] = {
                'success': False,
                'error': str(e)
            }

        # Test rollback capability
        logger.info("Testing rollback capability...")

        try:
            rollback_time = time.time()
            rollback_success = await deployment_manager.emergency_rollback()
            rollback_duration = time.time() - rollback_time

            self.results['deployment_tests']['rollback_test'] = {
                'success': rollback_success,
                'rollback_time_seconds': rollback_duration,
                'within_slo': rollback_duration <= 60  # Should rollback within 1 minute
            }

            if rollback_success and rollback_duration <= 60:
                logger.info(f"  ✓ Rollback successful in {rollback_duration:.1f}s")
            else:
                logger.warning(f"  ✗ Rollback issues: success={rollback_success}, time={rollback_duration:.1f}s")

        except Exception as e:
            logger.error(f"  ✗ Rollback test error: {e}")
            self.results['deployment_tests']['rollback_test'] = {
                'success': False,
                'error': str(e)
            }

    async def _test_failover_scenarios(self, e2e_system: E2EIntegrationSystem):
        """Test system failover and recovery scenarios."""
        load_tester = LoadTestingSystem(e2e_system)

        logger.info("Testing failover scenarios...")

        try:
            failover_results = await load_tester.run_failover_test()
            self.results['failover_tests'] = failover_results

            for test_name, result in failover_results.items():
                if result.get('recovery_successful', False):
                    logger.info(f"  ✓ {test_name}: Recovery successful")
                else:
                    logger.warning(f"  ✗ {test_name}: Recovery failed or incomplete")

        except Exception as e:
            logger.error(f"Failover testing failed: {e}")
            self.results['failover_tests'] = {'error': str(e)}

    async def _validate_slos(self, e2e_system: E2EIntegrationSystem):
        """Validate system against all SLO requirements."""
        logger.info("Validating SLO compliance...")

        # Get current system status
        status = e2e_system.get_system_status()

        # Check SLO compliance
        slo_results = {
            'uptime_slo': {
                'target': 99.5,
                'actual': status.get('uptime_percentage', 0),
                'passed': status.get('uptime_percentage', 0) >= 99.5
            },
            'scan_latency_slo': {
                'target_ms': 1000,
                'actual_ms': status.get('avg_scan_latency_ms', 0),
                'passed': status.get('avg_scan_latency_ms', 0) <= 1000
            },
            'error_rate_slo': {
                'target_percent': 0.5,
                'actual_percent': (status.get('error_count', 0) / max(status.get('total_scans', 1), 1)) * 100,
                'passed': (status.get('error_count', 0) / max(status.get('total_scans', 1), 1)) * 100 <= 0.5
            }
        }

        self.results['slo_validation'] = slo_results

        passed_slos = len([slo for slo in slo_results.values() if slo['passed']])
        total_slos = len(slo_results)

        logger.info(f"SLO Validation Results: {passed_slos}/{total_slos} SLOs passed")

        for slo_name, slo_data in slo_results.items():
            status_icon = "✓" if slo_data['passed'] else "✗"
            logger.info(f"  {status_icon} {slo_name}: {slo_data.get('actual', 'N/A')} (target: {slo_data.get('target', 'N/A')})")

    async def _generate_final_report(self):
        """Generate comprehensive final report."""
        logger.info("Generating final integration report...")

        # Calculate overall success metrics
        trading_success_rate = len([r for r in self.results['trading_cycles'] if r['success']]) / max(len(self.results['trading_cycles']), 1)
        load_test_success_rate = len([r for r in self.results['load_tests'].values() if isinstance(r, dict) and r.get('success', False)]) / max(len(self.results['load_tests']), 1)

        # Generate summary
        summary = {
            'overall_success': self.results['overall_success'],
            'trading_cycle_success_rate': trading_success_rate,
            'load_test_success_rate': load_test_success_rate,
            'slo_compliance': self.results.get('slo_validation', {}),
            'deployment_tests_passed': len([r for r in self.results.get('deployment_tests', {}).values() if isinstance(r, dict) and r.get('success', False)]),
            'failover_tests_passed': len([r for r in self.results.get('failover_tests', {}).values() if isinstance(r, dict) and r.get('recovery_successful', False)])
        }

        self.results['summary'] = summary

        # Save detailed results
        results_file = Path('e2e_integration_results.json')
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"✓ Detailed results saved to {results_file}")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("E2E INTEGRATION DEMO SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall Success: {'✓' if summary['overall_success'] else '✗'}")
        logger.info(f"Trading Cycles: {trading_success_rate:.1%} success rate")
        logger.info(f"Load Tests: {load_test_success_rate:.1%} success rate")
        logger.info(f"Deployment Tests: {summary['deployment_tests_passed']} passed")
        logger.info(f"Failover Tests: {summary['failover_tests_passed']} passed")
        logger.info("=" * 60)

    async def _cleanup_system(self, e2e_system: E2EIntegrationSystem):
        """Clean up system resources."""
        try:
            await e2e_system.stop_system()
            logger.info("✓ System cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")


async def main():
    """Run the complete E2E integration demo."""
    demo = E2EIntegrationDemo()

    try:
        success = await demo.run_complete_demo()

        if success:
            print("\n🎉 E2E Integration Demo completed successfully!")
            print("📊 Check 'e2e_integration_results.json' for detailed results")
            print("📝 Check 'e2e_integration_demo.log' for detailed logs")
            return 0
        else:
            print("\n❌ E2E Integration Demo failed")
            print("📝 Check 'e2e_integration_demo.log' for error details")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Demo failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
