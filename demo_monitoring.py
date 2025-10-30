#!/usr/bin/env python3
"""
Demo script for the autonomous trading system monitoring and telemetry.
Demonstrates real-time metrics collection, health checks, and alerting.
"""

import asyncio
import logging
import random
import threading
import time
from datetime import UTC, datetime, timezone
from typing import Any

from libs.trading_models.grafana_dashboards import export_dashboards_and_alerts
from libs.trading_models.health_checks import (
    run_health_checks,
    setup_default_health_checks,
)
from libs.trading_models.monitoring import (
    AlertManager,
    DrawdownAlert,
    ErrorRateAlert,
    LatencyAlert,
    get_metrics_collector,
    get_telemetry_manager,
    start_prometheus_server,
    trace_operation,
    track_latency,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingSimulator:
    """Simulates trading activity for monitoring demonstration"""

    def __init__(self):
        self.symbols = ['BTCUSD', 'ETHUSD', 'ADAUSD', 'SOLUSD', 'DOTUSD']
        self.patterns = ['breakout', 'reversal', 'continuation', 'divergence', 'support_resistance']
        self.running = False

    @trace_operation("simulate_trade")
    def simulate_trade(self) -> dict[str, Any]:
        """Simulate a single trade execution"""
        symbol = random.choice(self.symbols)
        pattern = random.choice(self.patterns)

        # Simulate trade outcome (70% win rate for demo)
        is_winner = random.random() < 0.7

        # Generate realistic P&L, fees, and funding
        if is_winner:
            pnl = random.uniform(50, 500)
            outcome = 'win'
        else:
            pnl = random.uniform(-300, -20)
            outcome = 'loss'

        fees = abs(pnl) * random.uniform(0.001, 0.003)  # 0.1-0.3% fees
        funding = random.uniform(-2, 2)  # Funding can be positive or negative

        return {
            'symbol': symbol,
            'pattern': pattern,
            'pnl': pnl,
            'fees': fees,
            'funding': funding,
            'outcome': outcome
        }

    @track_latency("scan")
    def simulate_market_scan(self):
        """Simulate market scanning with variable latency"""
        # Simulate processing time
        scan_time = random.uniform(0.1, 1.2)  # 100ms to 1.2s
        time.sleep(scan_time)

        # Occasionally simulate errors
        if random.random() < 0.05:  # 5% error rate
            error_type = random.choice(['data_error', 'api_error', 'timeout_error'])
            get_metrics_collector().record_error(error_type)
            logger.warning(f"Simulated {error_type} during market scan")

    def simulate_llm_call(self):
        """Simulate LLM API call with latency and cost tracking"""
        models = ['claude-3', 'gpt-4-turbo', 'gemini-pro', 'mixtral-8x7b']
        model = random.choice(models)

        # Simulate LLM latency (varies by model)
        latency_ranges = {
            'claude-3': (0.8, 2.5),
            'gpt-4-turbo': (1.2, 3.8),
            'gemini-pro': (0.6, 2.2),
            'mixtral-8x7b': (1.5, 4.2)
        }

        min_lat, max_lat = latency_ranges[model]
        latency = random.uniform(min_lat, max_lat)
        time.sleep(latency)

        # Simulate cost (varies by model)
        cost_per_second = {
            'claude-3': 0.015,
            'gpt-4-turbo': 0.030,
            'gemini-pro': 0.010,
            'mixtral-8x7b': 0.008
        }

        cost = latency * cost_per_second[model]
        get_metrics_collector().record_llm_latency(latency, model, cost)

    def run_simulation(self, duration_minutes: int = 5):
        """Run trading simulation for specified duration"""
        logger.info(f"Starting trading simulation for {duration_minutes} minutes...")
        self.running = True

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        trade_count = 0

        while time.time() < end_time and self.running:
            try:
                # Simulate market scanning (every 15-30 seconds)
                self.simulate_market_scan()

                # Simulate LLM analysis (every 2-3 scans)
                if random.random() < 0.4:
                    self.simulate_llm_call()

                # Simulate trade execution (every 5-10 scans)
                if random.random() < 0.15:
                    trade_data = self.simulate_trade()

                    # Record trade metrics
                    get_metrics_collector().record_trade(
                        pnl=trade_data['pnl'],
                        fees=trade_data['fees'],
                        funding=trade_data['funding'],
                        outcome=trade_data['outcome'],
                        pattern_id=trade_data['pattern']
                    )

                    trade_count += 1
                    logger.info(f"Trade #{trade_count}: {trade_data['symbol']} "
                              f"{trade_data['outcome']} P&L: ${trade_data['pnl']:.2f}")

                # Update system metrics
                memory_mb = random.uniform(800, 1200)
                cpu_percent = random.uniform(20, 80)
                get_metrics_collector().update_system_stats(memory_mb, cpu_percent)

                # Wait before next cycle
                time.sleep(random.uniform(10, 25))

            except KeyboardInterrupt:
                logger.info("Simulation interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in simulation: {e}")
                get_metrics_collector().record_error('simulation_error')

        self.running = False
        logger.info(f"Simulation completed. Total trades: {trade_count}")


async def setup_monitoring_system():
    """Setup the complete monitoring system"""
    logger.info("Setting up monitoring system...")

    # Initialize metrics collector and telemetry
    metrics_collector = get_metrics_collector()
    telemetry_manager = get_telemetry_manager()

    # Setup alert manager with rules
    alert_manager = AlertManager(metrics_collector)

    # Add alert rules
    alert_manager.add_alert_rule(DrawdownAlert(threshold_percent=8.0))
    alert_manager.add_alert_rule(LatencyAlert("scan", threshold_seconds=1.0))
    alert_manager.add_alert_rule(LatencyAlert("llm", threshold_seconds=3.0))
    alert_manager.add_alert_rule(ErrorRateAlert("data_error", threshold_count=5))

    # Setup health checks (with mocked dependencies for demo)
    def mock_db_connection():
        """Mock database connection for demo"""
        from unittest.mock import Mock
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    setup_default_health_checks(
        db_connection_func=mock_db_connection,
        market_data_url="https://api.example.com",
        execution_gateway_url="http://localhost:8001"
    )

    # Start Prometheus metrics server
    try:
        start_prometheus_server(port=8000)
        logger.info("Prometheus metrics server started on port 8000")
    except Exception as e:
        logger.warning(f"Could not start Prometheus server: {e}")

    # Export Grafana dashboards and alerts
    try:
        export_dashboards_and_alerts("monitoring_config")
        logger.info("Grafana dashboards and alerts exported to monitoring_config/")
    except Exception as e:
        logger.warning(f"Could not export Grafana configs: {e}")

    return alert_manager


async def run_monitoring_loop(alert_manager: AlertManager):
    """Run continuous monitoring and alerting loop"""
    logger.info("Starting monitoring loop...")

    while True:
        try:
            # Check alerts
            alert_manager.check_alerts()

            # Run health checks
            health_summary = await run_health_checks()

            # Log system status every minute
            metrics_collector = get_metrics_collector()
            trading_summary = metrics_collector.get_trading_summary()
            system_summary = metrics_collector.get_system_summary()

            logger.info("=== SYSTEM STATUS ===")
            logger.info(f"Overall Health: {health_summary['overall_status']}")
            logger.info(f"Total Trades: {trading_summary['total_trades']}")
            logger.info(f"Win Rate: {trading_summary['win_rate']:.1f}%")
            logger.info(f"Net P&L: ${trading_summary['net_pnl']:.2f}")
            logger.info(f"Current Drawdown: {trading_summary['current_drawdown']:.1f}%")
            logger.info(f"Scan Latency P95: {system_summary['scan_latency_p95']:.3f}s")
            logger.info(f"LLM Latency P95: {system_summary['llm_latency_p95']:.3f}s")
            logger.info(f"Memory Usage: {system_summary['memory_usage_mb']:.1f} MB")
            logger.info(f"CPU Usage: {system_summary['cpu_usage_percent']:.1f}%")
            logger.info("=====================")

            # Wait before next check
            await asyncio.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Monitoring loop interrupted")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(10)


async def demonstrate_timezone_handling():
    """Demonstrate UTC timezone handling"""
    logger.info("Demonstrating timezone handling...")

    from datetime import timedelta

    from libs.trading_models.health_checks import ensure_utc_timezone

    # Test with different timezone scenarios
    test_cases = [
        ("Naive datetime", datetime(2024, 1, 1, 12, 0, 0)),
        ("UTC datetime", datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)),
        ("EST datetime", datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-5)))),
        ("JST datetime", datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=9))))
    ]

    for name, dt in test_cases:
        utc_dt = ensure_utc_timezone(dt)
        logger.info(f"{name}: {dt} -> UTC: {utc_dt}")

    logger.info("Timezone handling demonstration completed")


async def main():
    """Main demo function"""
    logger.info("Starting Autonomous Trading System Monitoring Demo")
    logger.info("=" * 60)

    try:
        # Setup monitoring system
        alert_manager = await setup_monitoring_system()

        # Demonstrate timezone handling
        await demonstrate_timezone_handling()

        # Create trading simulator
        simulator = TradingSimulator()

        # Start simulation in background thread
        simulation_thread = threading.Thread(
            target=simulator.run_simulation,
            args=(10,),  # Run for 10 minutes
            daemon=True
        )
        simulation_thread.start()

        # Run monitoring loop
        await run_monitoring_loop(alert_manager)

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")
        raise
    finally:
        logger.info("Demo completed")

        # Print final metrics summary
        metrics_collector = get_metrics_collector()
        trading_summary = metrics_collector.get_trading_summary()
        system_summary = metrics_collector.get_system_summary()

        print("\n" + "=" * 60)
        print("FINAL METRICS SUMMARY")
        print("=" * 60)
        print(f"Total Trades: {trading_summary['total_trades']}")
        print(f"Win Rate: {trading_summary['win_rate']:.1f}%")
        print(f"Net P&L: ${trading_summary['net_pnl']:.2f}")
        print(f"Total Fees: ${trading_summary['total_fees']:.2f}")
        print(f"Total Funding: ${trading_summary['total_funding']:.2f}")
        print(f"Max Drawdown: {trading_summary['max_drawdown']:.1f}%")
        print(f"Profit Factor: {trading_summary['profit_factor']:.2f}")
        print(f"Sharpe Ratio: {trading_summary['sharpe_ratio']:.2f}")
        print(f"MAR Ratio: {trading_summary['mar_ratio']:.2f}")
        print(f"System Uptime: {system_summary['uptime_hours']:.1f} hours")
        print(f"Scan Latency P95: {system_summary['scan_latency_p95']:.3f}s")
        print(f"LLM Latency P95: {system_summary['llm_latency_p95']:.3f}s")
        print("=" * 60)

        # Show pattern performance
        pattern_metrics = metrics_collector.pattern_metrics
        if pattern_metrics:
            print("\nPATTERN PERFORMANCE")
            print("-" * 40)
            for pattern_id, metrics in pattern_metrics.items():
                print(f"{pattern_id:20} | Hit Rate: {metrics.hit_rate:5.1f}% | "
                      f"Expectancy: ${metrics.expectancy:7.2f} | "
                      f"Signals: {metrics.total_signals:3d}")

        print("\nPrometheus metrics available at: http://localhost:8000/metrics")
        print("Grafana configs exported to: monitoring_config/")


if __name__ == "__main__":
    asyncio.run(main())
