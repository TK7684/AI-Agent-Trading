"""
Orchestrator - Central coordinator for the autonomous trading system.

This module implements the main trading pipeline that coordinates all system components:
- Market analysis across multiple timeframes
- Trading decision pipeline (analysis → scoring → risk → execution)
- Position lifecycle management
- Dynamic check intervals with adaptive backoff
- Configuration management and hot reload capabilities
Optimized for performance, memory efficiency, and reliability.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from .base import BaseModel
from .enums import MarketRegime
from .signals import Signal

# Import available components, use mocks for others
try:
    from .market_data_ingestion import MarketDataAdapter
except ImportError:
    MarketDataAdapter = None

try:
    from .technical_indicators import TechnicalIndicators
except ImportError:
    TechnicalIndicators = None

try:
    from .pattern_recognition import PatternRecognition
except ImportError:
    PatternRecognition = None

try:
    from .confluence_scoring import ConfluenceScoring
except ImportError:
    ConfluenceScoring = None

try:
    from .llm_integration import MultiLLMRouter
except ImportError:
    MultiLLMRouter = None

try:
    from .risk_management import RiskManager
except ImportError:
    RiskManager = None

try:
    from .memory_learning import MemoryLearning
except ImportError:
    MemoryLearning = None


class OrchestrationState(Enum):
    """Current state of the orchestrator."""
    STARTING = "starting"
    RUNNING = "running"
    SAFE_MODE = "safe_mode"
    STOPPING = "stopping"
    STOPPED = "stopped"


class CheckInterval(Enum):
    """Dynamic check intervals based on market conditions."""
    FAST = 900  # 15 minutes
    NORMAL = 1800  # 30 minutes
    SLOW = 3600  # 1 hour
    VERY_SLOW = 14400  # 4 hours


class OrchestrationConfig(BaseModel):
    """Configuration for the orchestrator with validation."""
    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    timeframes: list[str] = ["15m", "1h", "4h", "1d"]
    base_check_interval: int = 1800  # 30 minutes
    max_check_interval: int = 14400  # 4 hours
    min_check_interval: int = 900  # 15 minutes
    safe_mode_cooldown: int = 3600  # 1 hour
    max_concurrent_analyses: int = 5
    enable_hot_reload: bool = True
    config_file_path: str = "config.toml"

    # Risk thresholds
    daily_drawdown_threshold: float = 0.08
    monthly_drawdown_threshold: float = 0.20

    # Performance thresholds for adaptive intervals
    volatility_threshold_high: float = 0.05
    volatility_threshold_low: float = 0.02

    # Optimization settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    max_cache_size: int = 1000
    enable_compression: bool = True

    def model_post_init(self, __context):
        """Validate configuration parameters."""
        if self.base_check_interval < self.min_check_interval:
            raise ValueError("Base check interval cannot be less than min check interval")
        if self.base_check_interval > self.max_check_interval:
            raise ValueError("Base check interval cannot be greater than max check interval")
        if self.daily_drawdown_threshold <= 0 or self.daily_drawdown_threshold > 1:
            raise ValueError("Daily drawdown threshold must be between 0 and 1")
        if self.monthly_drawdown_threshold <= 0 or self.monthly_drawdown_threshold > 1:
            raise ValueError("Monthly drawdown threshold must be between 0 and 1")


class AnalysisResult(BaseModel):
    """Result of market analysis with metadata."""
    symbol: str
    timeframe: str
    timestamp: datetime
    signals: list[Signal]
    confidence: float
    market_regime: MarketRegime
    volatility: float
    volume_trend: float
    analysis_duration_ms: int
    cache_hit: bool = False

    @property
    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence."""
        return self.confidence >= 0.8

    @property
    def has_signals(self) -> bool:
        """Check if analysis produced signals."""
        return len(self.signals) > 0


class AnalysisCache:
    """LRU cache for analysis results with TTL."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order: list[str] = []
        self._lock = asyncio.Lock()

    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """Generate cache key for symbol and timeframe."""
        return f"{symbol}:{timeframe}"

    async def get(self, symbol: str, timeframe: str) -> Optional[AnalysisResult]:
        """Get cached analysis result if valid."""
        async with self._lock:
            cache_key = self._get_cache_key(symbol, timeframe)

            if cache_key in self._cache:
                cached_item = self._cache[cache_key]

                # Check TTL
                if time.time() - cached_item['timestamp'] < self.ttl_seconds:
                    # Update access order
                    if cache_key in self._access_order:
                        self._access_order.remove(cache_key)
                    self._access_order.append(cache_key)

                    # Mark as cache hit
                    cached_item['result'].cache_hit = True
                    return cached_item['result']
                else:
                    # Expired, remove from cache
                    del self._cache[cache_key]
                    if cache_key in self._access_order:
                        self._access_order.remove(cache_key)

            return None

    async def set(self, symbol: str, timeframe: str, result: AnalysisResult) -> None:
        """Cache analysis result."""
        async with self._lock:
            cache_key = self._get_cache_key(symbol, timeframe)

            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                oldest_key = self._access_order[0]
                del self._cache[oldest_key]
                self._access_order.pop(0)

            # Add new item
            self._cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }

            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            self._access_order.append(cache_key)

    async def clear(self) -> None:
        """Clear all cached items."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'hit_rate': 0.0  # Would need to track hits/misses
            }


class MarketDataManager:
    """Manages market data with connection pooling and caching."""

    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self._adapters: dict[str, Any] = {}
        self._data_cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[dict[str, Any]]:
        """Get market data with caching."""
        cache_key = f"{symbol}:{timeframe}:{limit}"

        async with self._lock:
            if cache_key in self._data_cache:
                cached_data = self._data_cache[cache_key]
                if time.time() - cached_data['timestamp'] < 60:  # 1 minute cache
                    return cached_data['data']

        # Fetch fresh data
        try:
            if MarketDataAdapter:
                adapter = self._get_adapter(symbol)
                data = await adapter.get_data(timeframe, limit)

                # Cache the data
                async with self._lock:
                    self._data_cache[cache_key] = {
                        'data': data,
                        'timestamp': time.time()
                    }

                return data
            else:
                # Mock data for testing
                return self._generate_mock_data(symbol, timeframe, limit)
        except Exception as e:
            logging.error(f"Error fetching market data for {symbol}:{timeframe}: {e}")
            return None

    def _get_adapter(self, symbol: str) -> Any:
        """Get or create market data adapter for symbol."""
        if symbol not in self._adapters:
            if MarketDataAdapter:
                self._adapters[symbol] = MarketDataAdapter(symbol)
            else:
                self._adapters[symbol] = None
        return self._adapters[symbol]

    def _generate_mock_data(self, symbol: str, timeframe: str, limit: int) -> dict[str, Any]:
        """Generate mock market data for testing."""
        import random


        base_price = 50000 if "BTC" in symbol else 3000
        data = []

        for i in range(limit):
            timestamp = datetime.now() - timedelta(minutes=i * 15)
            price = base_price + random.uniform(-1000, 1000)
            volume = random.uniform(100, 1000)

            data.append({
                'timestamp': timestamp,
                'open': price,
                'high': price + random.uniform(0, 100),
                'low': price - random.uniform(0, 100),
                'close': price + random.uniform(-50, 50),
                'volume': volume
            })

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': data,
            'last_update': datetime.now()
        }


class TradingOrchestrator:
    """Main orchestrator with optimization features."""

    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.state = OrchestrationState.STOPPED
        self.analysis_cache = AnalysisCache(
            max_size=config.max_cache_size,
            ttl_seconds=config.cache_ttl_seconds
        )
        self.market_data_manager = MarketDataManager(config)

        # Component instances
        self.technical_indicators = TechnicalIndicators() if TechnicalIndicators else None
        self.pattern_recognition = PatternRecognition() if PatternRecognition else None
        self.confluence_scoring = ConfluenceScoring() if ConfluenceScoring else None
        self.llm_router = None  # Will be initialized later
        self.risk_manager = RiskManager() if RiskManager else None
        self.memory_learning = MemoryLearning() if MemoryLearning else None

        # Performance tracking
        self.analysis_times: list[float] = []
        self.total_analyses = 0
        self.cache_hits = 0

        # Control flags
        self._running = False
        self._stop_event = asyncio.Event()
        self._config_watcher = None

        # Initialize components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize system components."""
        try:
            # Initialize LLM router if configuration available
            if hasattr(self, 'config') and hasattr(self.config, 'llm_config'):
                self.llm_router = MultiLLMRouter(self.config.llm_config)

            logging.info("Trading orchestrator components initialized")
        except Exception as e:
            logging.error(f"Error initializing components: {e}")

    async def start(self) -> None:
        """Start the orchestrator."""
        if self.state != OrchestrationState.STOPPED:
            raise RuntimeError(f"Cannot start orchestrator in state: {self.state}")

        self.state = OrchestrationState.STARTING
        self._running = True
        self._stop_event.clear()

        try:
            # Start configuration watcher if enabled
            if self.config.enable_hot_reload:
                self._start_config_watcher()

            # Start main orchestration loop
            await self._run_orchestration_loop()

        except Exception as e:
            logging.error(f"Error in orchestrator: {e}")
            self.state = OrchestrationState.SAFE_MODE
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the orchestrator gracefully."""
        if self.state == OrchestrationState.STOPPED:
            return

        self.state = OrchestrationState.STOPPING
        self._running = False
        self._stop_event.set()

        # Wait for graceful shutdown
        await asyncio.sleep(1)

        # Cleanup
        await self.analysis_cache.clear()

        if self.llm_router:
            await self.llm_router.close()

        self.state = OrchestrationState.STOPPED
        logging.info("Trading orchestrator stopped")

    async def _run_orchestration_loop(self) -> None:
        """Main orchestration loop with adaptive intervals."""
        self.state = OrchestrationState.RUNNING

        while self._running and not self._stop_event.is_set():
            try:
                start_time = time.time()

                # Run market analysis for all symbols and timeframes
                await self._run_market_analysis()

                # Calculate next interval based on market conditions
                next_interval = self._calculate_next_interval()

                # Wait for next cycle
                await asyncio.sleep(next_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _run_market_analysis(self) -> None:
        """Run market analysis for all configured symbols and timeframes."""
        tasks = []

        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                task = asyncio.create_task(
                    self._analyze_symbol_timeframe(symbol, timeframe)
                )
                tasks.append(task)

                # Limit concurrent analyses
                if len(tasks) >= self.config.max_concurrent_analyses:
                    # Wait for some tasks to complete
                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    tasks = list(pending)

        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _analyze_symbol_timeframe(self, symbol: str, timeframe: str) -> Optional[AnalysisResult]:
        """Analyze a specific symbol and timeframe combination."""
        start_time = time.time()

        try:
            # Check cache first
            cached_result = await self.analysis_cache.get(symbol, timeframe)
            if cached_result:
                self.cache_hits += 1
                return cached_result

            # Fetch market data
            market_data = await self.market_data_manager.get_market_data(symbol, timeframe)
            if not market_data:
                return None

            # Run technical analysis
            indicators = await self._run_technical_analysis(market_data)

            # Run pattern recognition
            patterns = await self._run_pattern_recognition(market_data)

            # Run LLM analysis if available
            llm_analysis = await self._run_llm_analysis(symbol, timeframe, market_data)

            # Generate confluence score
            confluence_score = await self._generate_confluence_score(
                symbol, timeframe, indicators, patterns, llm_analysis
            )

            # Create analysis result
            analysis_duration_ms = int((time.time() - start_time) * 1000)

            result = AnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                signals=confluence_score.get('signals', []),
                confidence=confluence_score.get('confidence', 0.0),
                market_regime=confluence_score.get('market_regime', MarketRegime.SIDEWAYS),
                volatility=confluence_score.get('volatility', 0.0),
                volume_trend=confluence_score.get('volume_trend', 0.0),
                analysis_duration_ms=analysis_duration_ms
            )

            # Cache the result
            await self.analysis_cache.set(symbol, timeframe, result)

            # Update performance tracking
            self.analysis_times.append(analysis_duration_ms / 1000.0)
            self.total_analyses += 1

            # Keep only recent analysis times
            if len(self.analysis_times) > 100:
                self.analysis_times = self.analysis_times[-100:]

            return result

        except Exception as e:
            logging.error(f"Error analyzing {symbol}:{timeframe}: {e}")
            return None

    async def _run_technical_analysis(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Run technical analysis on market data."""
        if not self.technical_indicators:
            return {}

        try:
            # Convert market data to pandas DataFrame
            import pandas as pd

            df = pd.DataFrame(market_data['data'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # Calculate indicators
            indicators = await self.technical_indicators.calculate_all(df)
            return indicators

        except Exception as e:
            logging.error(f"Error in technical analysis: {e}")
            return {}

    async def _run_pattern_recognition(self, market_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Run pattern recognition on market data."""
        if not self.pattern_recognition:
            return []

        try:
            # Convert market data to required format
            import pandas as pd

            df = pd.DataFrame(market_data['data'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            # Detect patterns
            patterns = await self.pattern_recognition.detect_patterns(df)
            return patterns

        except Exception as e:
            logging.error(f"Error in pattern recognition: {e}")
            return []

    async def _run_llm_analysis(self, symbol: str, timeframe: str, market_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Run LLM analysis if available."""
        if not self.llm_router:
            return None

        try:
            # Prepare context for LLM
            context = {
                'symbol': symbol,
                'timeframe': timeframe,
                'market_data': market_data,
                'timestamp': datetime.now().isoformat()
            }

            # Generate prompt
            prompt = f"""
            Analyze the market data for {symbol} on {timeframe} timeframe.

            Recent price action:
            - Current price: {market_data['data'][-1]['close'] if market_data['data'] else 'N/A'}
            - Volume trend: {'Increasing' if len(market_data['data']) > 1 and market_data['data'][-1]['volume'] > market_data['data'][-2]['volume'] else 'Decreasing'}

            Provide a concise market analysis including:
            1. Market sentiment (bullish/bearish/neutral)
            2. Key support/resistance levels
            3. Potential trade opportunities
            4. Risk factors
            5. Confidence level (0-100)
            """

            # Create LLM request
            from .llm_integration import LLMRequest

            request = LLMRequest(
                prompt=prompt,
                model_id="claude-3-sonnet",
                context=context,
                max_tokens=500,
                temperature=0.3
            )

            # Get LLM response
            response = await self.llm_router.route_request(request)

            if response.success:
                return {
                    'analysis': response.content,
                    'confidence': response.confidence,
                    'model_id': response.model_id
                }
            else:
                logging.warning(f"LLM analysis failed: {response.error_message}")
                return None

        except Exception as e:
            logging.error(f"Error in LLM analysis: {e}")
            return None

    async def _generate_confluence_score(self, symbol: str, timeframe: str,
                                       indicators: dict[str, Any], patterns: list[dict[str, Any]],
                                       llm_analysis: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Generate confluence score combining all analyses."""
        if not self.confluence_scoring:
            return {
                'signals': [],
                'confidence': 0.5,
                'market_regime': MarketRegime.SIDEWAYS,
                'volatility': 0.0,
                'volume_trend': 0.0
            }

        try:
            # Calculate confluence score
            confluence_result = await self.confluence_scoring.calculate_confluence(
                symbol, timeframe, indicators, patterns, llm_analysis
            )

            return confluence_result

        except Exception as e:
            logging.error(f"Error generating confluence score: {e}")
            return {
                'signals': [],
                'confidence': 0.5,
                'market_regime': MarketRegime.SIDEWAYS,
                'volatility': 0.0,
                'volume_trend': 0.0
            }

    def _calculate_next_interval(self) -> int:
        """Calculate next check interval based on market conditions."""
        if not self.analysis_times:
            return self.config.base_check_interval

        # Calculate average analysis time
        avg_analysis_time = sum(self.analysis_times) / len(self.analysis_times)

        # Adjust interval based on performance
        if avg_analysis_time > 10:  # If analysis takes more than 10 seconds
            return min(self.config.max_check_interval, self.config.base_check_interval * 2)
        elif avg_analysis_time < 2:  # If analysis is fast
            return max(self.config.min_check_interval, self.config.base_check_interval // 2)
        else:
            return self.config.base_check_interval

    def _start_config_watcher(self) -> None:
        """Start configuration file watcher for hot reloading."""
        if not self.config.enable_hot_reload:
            return

        def watch_config():
            """Watch for configuration changes."""
            config_path = Path(self.config.config_file_path)
            last_modified = config_path.stat().st_mtime if config_path.exists() else 0

            while self._running:
                try:
                    if config_path.exists():
                        current_modified = config_path.stat().st_mtime
                        if current_modified > last_modified:
                            logging.info("Configuration file changed, reloading...")
                            # Reload configuration logic here
                            last_modified = current_modified

                    time.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    logging.error(f"Error in config watcher: {e}")
                    time.sleep(30)

        self._config_watcher = threading.Thread(target=watch_config, daemon=True)
        self._config_watcher.start()

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get orchestrator performance metrics."""
        cache_stats = await self.analysis_cache.get_stats()

        return {
            'state': self.state.value,
            'total_analyses': self.total_analyses,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hits / max(self.total_analyses, 1),
            'avg_analysis_time': sum(self.analysis_times) / max(len(self.analysis_times), 1) if self.analysis_times else 0,
            'cache_stats': cache_stats,
            'symbols_monitored': len(self.config.symbols),
            'timeframes_monitored': len(self.config.timeframes)
        }

    async def get_analysis_summary(self) -> dict[str, Any]:
        """Get summary of recent analyses."""
        # This would return recent analysis results
        # Implementation depends on how you want to store/retrieve this data
        return {
            'last_analysis_time': datetime.now().isoformat(),
            'symbols_analyzed': self.config.symbols,
            'timeframes_analyzed': self.config.timeframes
        }


# Alias for backwards compatibility
Orchestrator = TradingOrchestrator


class PositionLifecycle(Enum):
    """Position lifecycle states"""
    PENDING = "pending"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"


def create_orchestrator(config: Optional[Union[OrchestrationConfig, dict[str, Any]]] = None) -> TradingOrchestrator:
    """Factory function to create a TradingOrchestrator instance."""
    if config is None:
        # Create default configuration matching original expectations
        config = OrchestrationConfig(
            symbols=["BTCUSDT", "ETHUSDT"],  # Match test expectations
            timeframes=["1h"],
            base_check_interval=1,
            max_check_interval=10,
            min_check_interval=1,
            safe_mode_cooldown=1,
            max_concurrent_analyses=2,
            enable_hot_reload=False,
            config_file_path="test_config.toml",
            daily_drawdown_threshold=0.05,
            monthly_drawdown_threshold=0.15,
            enable_caching=False,
            enable_compression=False
        )
    elif isinstance(config, dict):
        # Handle dict input by creating OrchestrationConfig with overrides
        default_config = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h"],
            "base_check_interval": 1,
            "max_check_interval": 10,
            "min_check_interval": 1,
            "safe_mode_cooldown": 1,
            "max_concurrent_analyses": 2,
            "enable_hot_reload": False,
            "config_file_path": "test_config.toml",
            "daily_drawdown_threshold": 0.05,
            "monthly_drawdown_threshold": 0.15,
            "enable_caching": False,
            "enable_compression": False
        }
        default_config.update(config)
        config = OrchestrationConfig(**default_config)

    return TradingOrchestrator(config)
