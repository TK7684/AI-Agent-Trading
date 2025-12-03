"""
Automated Trading System Launcher
Main entry point for the comprehensive auto-trading system with database integration
and adaptive learning capabilities.
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv

from auto_trading_system.api.llm_client import LLMProvider, TradingAnalyzer
from auto_trading_system.core.live_trading_engine import LiveTradingEngine

# Import demo mode
from auto_trading_system.market_data.mock_provider import MockMarketDataProvider
from auto_trading_system.monitoring.performance_monitor import (
    AlertConfig,
    PerformanceMonitor,
)
from libs.trading_models.config_manager import get_config_manager

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("automated_trading.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


class AutomatedTradingSystem:
    """
    Main automated trading system that coordinates all components:
    - Live trading engine
    - Performance monitoring
    - Database integration
    - Adaptive learning
    """

    def __init__(self, config_path: str = None):
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()

        # Initialize LLM provider with OpenAI and Gemini
        openai_key = os.getenv("OPENAI_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")

        if not openai_key:
            logger.warning("OpenAI API key not found in environment variables")
        if not gemini_key:
            logger.warning("Gemini API key not found in environment variables")

        self.llm_provider = LLMProvider(
            openai_api_key=openai_key, gemini_api_key=gemini_key
        )
        self.trading_analyzer = TradingAnalyzer(self.llm_provider)

        # Initialize components
        self.trading_engine = LiveTradingEngine(config_path)
        self.performance_monitor = PerformanceMonitor(
            config=AlertConfig(
                cpu_threshold=self.config.get("monitoring", {}).get(
                    "cpu_threshold", 80.0
                ),
                memory_threshold=self.config.get("monitoring", {}).get(
                    "memory_threshold", 85.0
                ),
                disk_threshold=self.config.get("monitoring", {}).get(
                    "disk_threshold", 90.0
                ),
                drawdown_threshold=self.config.get("trading", {}).get(
                    "max_drawdown_pct", 10.0
                ),
                win_rate_threshold=self.config.get("trading", {}).get(
                    "min_win_rate", 40.0
                ),
                error_rate_threshold=self.config.get("monitoring", {}).get(
                    "error_threshold", 5.0
                ),
            )
        )

        # System state
        self.is_running = False
        self.shutdown_requested = False

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Automated Trading System initialized with OpenAI and Gemini")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

    async def start(self) -> None:
        """Start the automated trading system"""
        if self.is_running:
            logger.warning("Trading system is already running")
            return

        logger.info("🚀 Starting Automated Trading System")
        logger.info("=" * 80)
        logger.info("📈 AUTO-TRADING ENGINE ACTIVATED")
        logger.info("🤖 ADAPTIVE LEARNING ENABLED")
        logger.info("📊 REAL-TIME MONITORING STARTED")
        logger.info("💾 DATABASE INTEGRATION ACTIVE")
        logger.info("=" * 80)

        try:
            # Start performance monitoring
            await self.performance_monitor.start_monitoring()
            logger.info("✅ Performance monitoring started")

            # Add alert callback
            self.performance_monitor.add_alert_callback(self._handle_alert)

            # Start the trading engine
            trading_task = asyncio.create_task(self.trading_engine.start_trading())

            self.is_running = True
            logger.info("✅ Live trading engine started")

            # Main system loop
            await self._system_loop(trading_task)

        except Exception as e:
            logger.error(f"Error starting trading system: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the automated trading system"""
        if not self.is_running:
            return

        logger.info("🛑 Stopping Automated Trading System")

        try:
            # Stop trading engine
            await self.trading_engine.stop_trading()
            logger.info("✅ Trading engine stopped")

            # Stop performance monitoring
            await self.performance_monitor.stop_monitoring()
            logger.info("✅ Performance monitoring stopped")

            # Generate final report
            await self._generate_final_report()

            self.is_running = False
            logger.info("✅ Automated trading system stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping trading system: {e}")

    async def _system_loop(self, trading_task: asyncio.Task) -> None:
        """Main system monitoring loop"""
        system_check_interval = 300  # 5 minutes
        report_interval = 3600  # 1 hour

        last_system_check = datetime.now(timezone.utc)
        last_report = datetime.now(timezone.utc)

        while self.is_running and not self.shutdown_requested:
            try:
                # Check if trading task is still running
                if trading_task.done():
                    if trading_task.exception():
                        logger.error(f"Trading task failed: {trading_task.exception()}")
                    else:
                        logger.info("Trading task completed normally")
                    break

                # Periodic system health check
                now = datetime.now(timezone.utc)
                if (now - last_system_check).seconds >= system_check_interval:
                    await self._perform_system_health_check()
                    last_system_check = now

                # Periodic performance report
                if (now - last_report).seconds >= report_interval:
                    await self._generate_performance_report()
                    last_report = now

                # Check for shutdown request
                if self.shutdown_requested:
                    logger.info("Shutdown requested, stopping...")
                    break

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in system loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error

        # Cancel trading task if still running
        if not trading_task.done():
            trading_task.cancel()
            try:
                await trading_task
            except asyncio.CancelledError:
                pass

    async def _perform_system_health_check(self) -> None:
        """Perform comprehensive system health check"""
        try:
            current_metrics = self.performance_monitor.get_current_metrics()

            logger.info("🔍 System Health Check:")
            logger.info(
                f"   CPU Usage: {current_metrics.get('system', {}).get('cpu_usage', 0):.1f}%"
            )
            logger.info(
                f"   Memory Usage: {current_metrics.get('system', {}).get('memory_usage', 0):.1f}%"
            )
            logger.info(
                f"   Active Positions: {current_metrics.get('trading', {}).get('active_positions', 0)}"
            )
            logger.info(
                f"   Daily P&L: ${current_metrics.get('trading', {}).get('daily_pnl', 0):.2f}"
            )
            logger.info(
                f"   Win Rate: {current_metrics.get('trading', {}).get('win_rate', 0):.1f}%"
            )

            # Check for critical conditions
            system_metrics = current_metrics.get("system", {})
            trading_metrics = current_metrics.get("trading", {})

            if system_metrics.get("cpu_usage", 0) > 90:
                logger.warning("⚠️ High CPU usage detected")

            if system_metrics.get("memory_usage", 0) > 90:
                logger.warning("⚠️ High memory usage detected")

            if trading_metrics.get("current_drawdown", 0) > 15:
                logger.warning("⚠️ High drawdown detected")

        except Exception as e:
            logger.error(f"Error in health check: {e}")

    async def _generate_performance_report(self) -> None:
        """Generate and log performance report"""
        try:
            report = self.performance_monitor.get_performance_report(hours=24)

            logger.info("📊 24-Hour Performance Report:")
            logger.info("=" * 50)

            # System performance
            system_perf = report.get("system_performance", {})
            if system_perf:
                logger.info("System:")
                logger.info(f"   Avg CPU: {system_perf.get('avg_cpu_usage', 0):.1f}%")
                logger.info(
                    f"   Avg Memory: {system_perf.get('avg_memory_usage', 0):.1f}%"
                )
                logger.info(f"   Uptime: {system_perf.get('uptime_hours', 0):.1f}h")

            # Trading performance
            trading_perf = report.get("trading_performance", {})
            if trading_perf:
                logger.info("Trading:")
                logger.info(f"   Total Trades: {trading_perf.get('total_trades', 0)}")
                logger.info(f"   Win Rate: {trading_perf.get('win_rate', 0):.1f}%")
                logger.info(f"   Daily P&L: ${trading_perf.get('daily_pnl', 0):.2f}")
                logger.info(
                    f"   Max Drawdown: {trading_perf.get('max_drawdown', 0):.1f}%"
                )

            # Learning performance
            learning_perf = report.get("learning_performance", {})
            if learning_perf:
                logger.info("Learning:")
                logger.info(
                    f"   Learning Cycles: {learning_perf.get('total_learning_cycles', 0)}"
                )
                logger.info(
                    f"   Accuracy Improvement: {learning_perf.get('avg_accuracy_improvement', 0):.3f}"
                )
                logger.info(
                    f"   Profit Improvement: {learning_perf.get('avg_profit_improvement', 0):.3f}"
                )

            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Error generating performance report: {e}")

    async def _generate_final_report(self) -> None:
        """Generate final trading session report"""
        try:
            current_metrics = self.performance_monitor.get_current_metrics()
            trading_metrics = current_metrics.get("trading", {})
            learning_metrics = current_metrics.get("learning", {})

            logger.info("📈 FINAL TRADING SESSION REPORT")
            logger.info("=" * 80)

            # Summary
            total_trades = trading_metrics.get("total_trades", 0)
            win_rate = trading_metrics.get("win_rate", 0)
            daily_pnl = trading_metrics.get("daily_pnl", 0)

            logger.info(f"📊 Performance Summary:")
            logger.info(f"   Total Trades: {total_trades}")
            logger.info(f"   Win Rate: {win_rate:.1f}%")
            logger.info(f"   Daily P&L: ${daily_pnl:+.2f}")
            logger.info(
                f"   Active Positions: {trading_metrics.get('active_positions', 0)}"
            )

            # Learning Summary
            logger.info(f"🤖 Learning Summary:")
            logger.info(
                f"   Learning Cycles: {learning_metrics.get('learning_cycles_today', 0)}"
            )
            logger.info(
                f"   Confidence Score: {learning_metrics.get('confidence_score', 0):.3f}"
            )
            logger.info(
                f"   Strategies Optimized: {learning_metrics.get('strategies_optimized', 0)}"
            )

            # Grade the performance
            if win_rate >= 70 and daily_pnl > 0:
                grade = "A+ - EXCELLENT"
                message = (
                    "🏆 Outstanding performance! System operating at peak efficiency."
                )
            elif win_rate >= 60 and daily_pnl > 0:
                grade = "A - VERY GOOD"
                message = "👍 Strong performance with profitable results."
            elif win_rate >= 50:
                grade = "B+ - GOOD"
                message = "📈 Solid performance with room for improvement."
            else:
                grade = "B - NEEDS OPTIMIZATION"
                message = "⚠️ Performance below optimal, consider strategy adjustments."

            logger.info(f"🏆 SYSTEM GRADE: {grade}")
            logger.info(f"   {message}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Error generating final report: {e}")

    async def _handle_alert(self, alert_type: str, alert_data: dict) -> None:
        """Handle performance alerts"""
        try:
            level = alert_data.get("level", "INFO")
            message = alert_data.get("message", "Unknown alert")
            metric = alert_data.get("metric", "unknown")
            value = alert_data.get("value", 0)
            threshold = alert_data.get("threshold", 0)

            if level == "CRITICAL":
                logger.error(f"🚨 CRITICAL ALERT [{alert_type}]: {message}")
                logger.error(f"   Metric: {metric} = {value} (Threshold: {threshold})")
            elif level == "WARNING":
                logger.warning(f"⚠️ WARNING ALERT [{alert_type}]: {message}")
                logger.warning(
                    f"   Metric: {metric} = {value} (Threshold: {threshold})"
                )
            else:
                logger.info(f"ℹ️ INFO ALERT [{alert_type}]: {message}")

        except Exception as e:
            logger.error(f"Error handling alert: {e}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Automated Trading System")
    parser.add_argument(
        "--config", type=str, help="Path to configuration file", default=None
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run in simulation mode (no real trades)"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run demo mode with simulated data"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run simulation mode with mock market data",
    )

    args = parser.parse_args()

    # Create and start the system
    system = AutomatedTradingSystem(config_path=args.config)

    try:
        if args.dry_run:
            logger.info("🔍 DRY RUN MODE - No real trades will be executed")
        elif args.demo:
            logger.info("🎭 DEMO MODE - Using simulated market data")
        elif args.simulation:
            logger.info(
                "🔬 SIMULATION MODE - Using mock market data with realistic patterns"
            )
        else:
            logger.info("💰 LIVE TRADING MODE - Real trades will be executed")

        await system.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await system.stop()


if __name__ == "__main__":
    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              AUTOMATED TRADING SYSTEM v2.0                   ║
    ║                                                              ║
    ║  🚀 Auto-Run Real Trading                                   ║
    ║  📊 Database Integration                                    ║
    ║  🤖 Adaptive Learning & Logic Adjustment                     ║
    ║  📈 Real-time Performance Monitoring                         ║
    ║  🧠 AI-Powered Analysis (OpenAI + Gemini)                   ║
    ║                                                              ║
    ║  Press Ctrl+C to stop gracefully                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    print("🔑 API Key Status:")
    print(f"   OpenAI: {'✅ Configured' if openai_key else '❌ Missing'}")
    print(f"   Gemini: {'✅ Configured' if gemini_key else '❌ Missing'}")
    print()

    if not openai_key or not gemini_key:
        print("⚠️ WARNING: Some API keys are missing. Please set them in your .env file")
        print()

    asyncio.run(main())
