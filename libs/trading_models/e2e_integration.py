"""
End-to-End Integration System
Wires together all system components with proper error handling and testing.
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .base import Portfolio, TradingSignal
from .confluence_scoring import ConfluenceScoring
from .error_handling import ErrorHandler
from .feature_flags import FeatureFlags
from .llm_integration import LLMRouter
from .market_data_ingestion import MarketDataIngestion
from .monitoring import MonitoringSystem
from .orchestrator import TradingOrchestrator
from .pattern_recognition import PatternRecognition
from .persistence import PersistenceManager
from .risk_management import RiskManager
from .technical_indicators import TechnicalIndicators


class SystemState(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    SAFE_MODE = "safe_mode"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


@dataclass
class E2ETestResult:
    test_name: str
    success: bool
    duration_ms: float
    error_message: Optional[str] = None
    metrics: dict[str, Any] = None


@dataclass
class SystemHealthCheck:
    component: str
    healthy: bool
    latency_ms: float
    error_message: Optional[str] = None
    last_check: datetime = None


class E2EIntegrationSystem:
    """
    Main integration system that orchestrates all trading components
    and provides comprehensive end-to-end testing capabilities.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.state = SystemState.INITIALIZING
        self.logger = logging.getLogger(__name__)

        # Initialize all components
        self._initialize_components()

        # Health tracking
        self.component_health: dict[str, SystemHealthCheck] = {}
        self.last_health_check = datetime.now()

        # Performance metrics
        self.performance_metrics = {
            'scan_latencies': [],
            'llm_latencies': [],
            'execution_latencies': [],
            'uptime_start': datetime.now(),
            'total_scans': 0,
            'successful_scans': 0,
            'error_count': 0
        }

        # Feature flags for deployment control
        self.feature_flags = FeatureFlags()

    def _initialize_components(self):
        """Initialize all system components with proper error handling."""
        try:
            # Core trading components
            self.market_data = MarketDataIngestion(self.config.get('market_data', {}))
            self.indicators = TechnicalIndicators()
            self.patterns = PatternRecognition()
            self.confluence = ConfluenceScoring()
            self.llm_router = LLMRouter(self.config.get('llm', {}))
            self.risk_manager = RiskManager(self.config.get('risk', {}))
            self.orchestrator = TradingOrchestrator(self.config.get('orchestrator', {}))
            self.persistence = PersistenceManager(self.config.get('persistence', {}))
            self.monitoring = MonitoringSystem(self.config.get('monitoring', {}))
            self.error_handler = ErrorHandler()

            # Wire components together
            self._wire_components()

            self.logger.info("All components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def _wire_components(self):
        """Wire all components together with proper dependencies."""
        try:
            # Set up component dependencies
            if hasattr(self.orchestrator, 'set_market_data'):
                self.orchestrator.set_market_data(self.market_data)
            if hasattr(self.orchestrator, 'set_indicators'):
                self.orchestrator.set_indicators(self.indicators)
            if hasattr(self.orchestrator, 'set_patterns'):
                self.orchestrator.set_patterns(self.patterns)
            if hasattr(self.orchestrator, 'set_confluence'):
                self.orchestrator.set_confluence(self.confluence)
            if hasattr(self.orchestrator, 'set_llm_router'):
                self.orchestrator.set_llm_router(self.llm_router)
            if hasattr(self.orchestrator, 'set_risk_manager'):
                self.orchestrator.set_risk_manager(self.risk_manager)
            if hasattr(self.orchestrator, 'set_persistence'):
                self.orchestrator.set_persistence(self.persistence)
            if hasattr(self.orchestrator, 'set_monitoring'):
                self.orchestrator.set_monitoring(self.monitoring)
            if hasattr(self.orchestrator, 'set_error_handler'):
                self.orchestrator.set_error_handler(self.error_handler)

            # Set up error handling callbacks
            if hasattr(self.error_handler, 'set_safe_mode_callback'):
                self.error_handler.set_safe_mode_callback(self._trigger_safe_mode)
            if hasattr(self.error_handler, 'set_recovery_callback'):
                self.error_handler.set_recovery_callback(self._attempt_recovery)

            # Set up monitoring callbacks
            if hasattr(self.monitoring, 'set_alert_callback'):
                self.monitoring.set_alert_callback(self._handle_alert)
        except Exception as e:
            self.logger.warning(f"Component wiring partially failed: {e}")

    async def start_system(self) -> bool:
        """Start the complete trading system."""
        try:
            self.logger.info("Starting E2E trading system...")

            # Perform startup health checks
            if not await self._startup_health_checks():
                self.logger.error("Startup health checks failed")
                return False

            # Start all components
            await self.market_data.start()
            await self.orchestrator.start()
            await self.monitoring.start()

            self.state = SystemState.RUNNING
            self.performance_metrics['uptime_start'] = datetime.now()

            self.logger.info("E2E trading system started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            await self.error_handler.handle_critical_error(e)
            return False

    async def stop_system(self) -> bool:
        """Gracefully stop the trading system."""
        try:
            self.logger.info("Stopping E2E trading system...")
            self.state = SystemState.SHUTDOWN

            # Stop components in reverse order
            await self.monitoring.stop()
            await self.orchestrator.stop()
            await self.market_data.stop()

            # Final persistence flush
            await self.persistence.flush_all()

            self.logger.info("E2E trading system stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error during system shutdown: {e}")
            return False

    async def _startup_health_checks(self) -> bool:
        """Perform comprehensive health checks on startup."""
        checks = [
            ('market_data', self._check_market_data_health),
            ('llm_router', self._check_llm_health),
            ('risk_manager', self._check_risk_health),
            ('persistence', self._check_persistence_health),
            ('monitoring', self._check_monitoring_health)
        ]

        all_healthy = True
        for component, check_func in checks:
            try:
                start_time = time.time()
                healthy = await check_func()
                latency = (time.time() - start_time) * 1000

                self.component_health[component] = SystemHealthCheck(
                    component=component,
                    healthy=healthy,
                    latency_ms=latency,
                    last_check=datetime.now()
                )

                if not healthy:
                    all_healthy = False
                    self.logger.warning(f"Component {component} failed health check")

            except Exception as e:
                all_healthy = False
                self.component_health[component] = SystemHealthCheck(
                    component=component,
                    healthy=False,
                    latency_ms=0,
                    error_message=str(e),
                    last_check=datetime.now()
                )
                self.logger.error(f"Health check failed for {component}: {e}")

        return all_healthy

    async def _check_market_data_health(self) -> bool:
        """Check market data component health."""
        try:
            # Test data fetch
            test_data = await self.market_data.fetch_ohlcv("BTCUSDT", "1h", limit=1)
            return test_data is not None and len(test_data) > 0
        except Exception:
            return False

    async def _check_llm_health(self) -> bool:
        """Check LLM router health."""
        try:
            # Test simple LLM call
            response = await self.llm_router.analyze_market(
                "Test market analysis", {"test": True}
            )
            return response is not None
        except Exception:
            return False

    async def _check_risk_health(self) -> bool:
        """Check risk manager health."""
        try:
            # Test risk calculation
            test_portfolio = Portfolio(
                total_equity=10000.0,
                available_margin=5000.0,
                positions=[],
                daily_pnl=0.0,
                unrealized_pnl=0.0
            )

            test_signal = TradingSignal(
                symbol="BTCUSDT",
                direction="LONG",
                confidence=0.7,
                confluence_score=65.0,
                reasoning="Test signal",
                timeframe_analysis={}
            )

            size = self.risk_manager.calculate_position_size(test_signal, test_portfolio)
            return size > 0
        except Exception:
            return False

    async def _check_persistence_health(self) -> bool:
        """Check persistence layer health."""
        try:
            # Test database connection
            await self.persistence.health_check()
            return True
        except Exception:
            return False

    async def _check_monitoring_health(self) -> bool:
        """Check monitoring system health."""
        try:
            # Test metrics collection
            self.monitoring.record_metric("health_check", 1.0)
            return True
        except Exception:
            return False

    async def run_complete_trading_cycle(self, symbol: str) -> E2ETestResult:
        """Run a complete trading cycle for testing."""
        start_time = time.time()
        test_name = f"complete_trading_cycle_{symbol}"

        try:
            self.logger.info(f"Starting complete trading cycle for {symbol}")

            # Step 1: Fetch market data
            market_data = await self.market_data.fetch_multi_timeframe_data(
                symbol, ["15m", "1h", "4h", "1d"]
            )

            if not market_data:
                raise Exception("Failed to fetch market data")

            # Step 2: Calculate indicators
            indicators = {}
            for timeframe, data in market_data.items():
                indicators[timeframe] = self.indicators.calculate_all_indicators(data)

            # Step 3: Detect patterns
            patterns = {}
            for timeframe, data in market_data.items():
                patterns[timeframe] = self.patterns.detect_all_patterns(
                    data, indicators[timeframe]
                )

            # Step 4: Calculate confluence score
            confluence_result = self.confluence.calculate_confluence_score(
                indicators, patterns, market_data
            )

            # Step 5: Get LLM analysis (if enabled)
            llm_analysis = None
            if self.feature_flags.is_enabled("llm_analysis"):
                llm_analysis = await self.llm_router.analyze_market(
                    f"Analyze {symbol} market conditions", {
                        "indicators": indicators,
                        "patterns": patterns,
                        "confluence": confluence_result
                    }
                )

            # Step 6: Generate trading signal
            signal = TradingSignal(
                symbol=symbol,
                direction=confluence_result.direction,
                confidence=confluence_result.confidence,
                confluence_score=confluence_result.score,
                reasoning=confluence_result.reasoning,
                timeframe_analysis=confluence_result.timeframe_analysis
            )

            # Step 7: Risk assessment
            current_portfolio = await self.persistence.get_current_portfolio()
            risk_assessment = self.risk_manager.assess_trade_risk(signal, current_portfolio)

            # Step 8: Execute trade (if approved)
            trade_result = None
            if risk_assessment.approved and self.feature_flags.is_enabled("live_trading"):
                trade_result = await self.orchestrator.execute_trade(signal, risk_assessment)

            # Step 9: Record results
            cycle_result = {
                'symbol': symbol,
                'signal': asdict(signal) if hasattr(signal, '__dataclass_fields__') else str(signal),
                'risk_assessment': asdict(risk_assessment) if hasattr(risk_assessment, '__dataclass_fields__') else str(risk_assessment),
                'trade_executed': trade_result is not None,
                'llm_analysis_used': llm_analysis is not None
            }

            await self.persistence.record_trading_cycle(cycle_result)

            duration_ms = (time.time() - start_time) * 1000
            self.performance_metrics['scan_latencies'].append(duration_ms)
            self.performance_metrics['total_scans'] += 1
            self.performance_metrics['successful_scans'] += 1

            # Update monitoring
            self.monitoring.record_metric("trading_cycle_duration_ms", duration_ms)
            self.monitoring.record_metric("trading_cycle_success", 1.0)

            return E2ETestResult(
                test_name=test_name,
                success=True,
                duration_ms=duration_ms,
                metrics=cycle_result
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.performance_metrics['error_count'] += 1

            self.logger.error(f"Trading cycle failed for {symbol}: {e}")
            if hasattr(self.error_handler, 'handle_trading_error') and callable(self.error_handler.handle_trading_error):
                if asyncio.iscoroutinefunction(self.error_handler.handle_trading_error):
                    await self.error_handler.handle_trading_error(e, symbol)
                else:
                    self.error_handler.handle_trading_error(e, symbol)

            return E2ETestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

    def _trigger_safe_mode(self, reason: str):
        """Trigger system safe mode."""
        self.logger.warning(f"Triggering SAFE_MODE: {reason}")
        self.state = SystemState.SAFE_MODE

        # Disable risky features
        self.feature_flags.disable("live_trading")
        self.feature_flags.disable("high_risk_trades")

        # Tighten risk controls
        self.risk_manager.enable_safe_mode()

        # Alert monitoring
        self.monitoring.send_alert("SAFE_MODE_TRIGGERED", {
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

    async def _attempt_recovery(self, error_type: str, context: dict[str, Any]):
        """Attempt automatic recovery from errors."""
        self.logger.info(f"Attempting recovery from {error_type}")

        recovery_actions = {
            'market_data_error': self._recover_market_data,
            'llm_error': self._recover_llm,
            'execution_error': self._recover_execution,
            'persistence_error': self._recover_persistence
        }

        if error_type in recovery_actions:
            try:
                success = await recovery_actions[error_type](context)
                if success:
                    self.logger.info(f"Recovery successful for {error_type}")
                    return True
            except Exception as e:
                self.logger.error(f"Recovery failed for {error_type}: {e}")

        return False

    async def _recover_market_data(self, context: dict[str, Any]) -> bool:
        """Recover from market data errors."""
        try:
            # Restart market data connection
            await self.market_data.reconnect()
            return True
        except Exception:
            return False

    async def _recover_llm(self, context: dict[str, Any]) -> bool:
        """Recover from LLM errors."""
        try:
            # Switch to backup LLM model
            await self.llm_router.switch_to_backup_model()
            return True
        except Exception:
            return False

    async def _recover_execution(self, context: dict[str, Any]) -> bool:
        """Recover from execution errors."""
        try:
            # Reset execution gateway connection
            # This would interface with the Rust execution gateway
            return True
        except Exception:
            return False

    async def _recover_persistence(self, context: dict[str, Any]) -> bool:
        """Recover from persistence errors."""
        try:
            # Reconnect to database
            await self.persistence.reconnect()
            return True
        except Exception:
            return False

    def _handle_alert(self, alert_type: str, data: dict[str, Any]):
        """Handle monitoring alerts."""
        self.logger.warning(f"Alert received: {alert_type} - {data}")

        # Handle specific alert types
        if alert_type == "HIGH_DRAWDOWN":
            self._trigger_safe_mode("High drawdown detected")
        elif alert_type == "SYSTEM_OVERLOAD":
            # Reduce system load
            self.feature_flags.disable("non_essential_features")
        elif alert_type == "COST_BUDGET_EXCEEDED":
            # Reduce LLM usage
            self.feature_flags.disable("frequent_llm_calls")

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status."""
        uptime = datetime.now() - self.performance_metrics['uptime_start']

        # Calculate uptime percentage (target: ≥99.5%)
        uptime_percentage = (
            (uptime.total_seconds() - self.performance_metrics['error_count'] * 60) /
            uptime.total_seconds() * 100
        )

        # Calculate average latencies
        avg_scan_latency = (
            sum(self.performance_metrics['scan_latencies'][-100:]) /
            len(self.performance_metrics['scan_latencies'][-100:])
            if self.performance_metrics['scan_latencies'] else 0
        )

        return {
            'state': self.state.value,
            'uptime_hours': uptime.total_seconds() / 3600,
            'uptime_percentage': uptime_percentage,
            'total_scans': self.performance_metrics['total_scans'],
            'successful_scans': self.performance_metrics['successful_scans'],
            'error_count': self.performance_metrics['error_count'],
            'avg_scan_latency_ms': avg_scan_latency,
            'component_health': {
                name: asdict(health) if hasattr(health, '__dataclass_fields__') else str(health)
                for name, health in self.component_health.items()
            },
            'feature_flags': self.feature_flags.get_all_flags(),
            'slo_compliance': {
                'uptime_target': 99.5,
                'uptime_actual': uptime_percentage,
                'scan_latency_target_ms': 1000,
                'scan_latency_actual_ms': avg_scan_latency,
                'meets_slo': uptime_percentage >= 99.5 and avg_scan_latency <= 1000
            }
        }
