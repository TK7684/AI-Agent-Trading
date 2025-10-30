"""
Market Data Ingestion and Analysis Engine

This module provides market data adapters, technical indicator calculations,
and multi-timeframe synchronization for the autonomous trading system.
"""

import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import aiohttp
import numpy as np
import websockets

from .enums import Timeframe
from .market_data import MarketBar

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    WEBSOCKET = "websocket"
    REST = "rest"


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class DataQualityMetrics:
    """Metrics for tracking data quality"""
    total_messages: int = 0
    parsed_messages: int = 0
    failed_messages: int = 0
    duplicate_messages: int = 0
    out_of_order_messages: int = 0
    missing_data_gaps: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)

    @property
    def parse_success_rate(self) -> float:
        if self.total_messages == 0:
            return 0.0
        return self.parsed_messages / self.total_messages

    @property
    def quality_score(self) -> float:
        """Overall quality score (0-1)"""
        if self.total_messages == 0:
            return 0.0

        parse_rate = self.parse_success_rate
        duplicate_rate = self.duplicate_messages / self.total_messages
        error_rate = (self.failed_messages + self.out_of_order_messages) / self.total_messages

        return max(0.0, parse_rate - duplicate_rate - error_rate)


@dataclass
class ReconnectConfig:
    """Configuration for reconnection logic"""
    max_retries: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


class MarketDataAdapter(ABC):
    """Abstract base class for market data adapters"""

    def __init__(self, symbol: str, timeframes: list[Timeframe]):
        self.symbol = symbol
        self.timeframes = timeframes
        self.state = ConnectionState.DISCONNECTED
        self.quality_metrics = DataQualityMetrics()
        self.reconnect_config = ReconnectConfig()
        self.callbacks: list[Callable[[OHLCV, Timeframe], None]] = []
        self.last_heartbeat = datetime.now(UTC)
        self._reconnect_count = 0

    def add_callback(self, callback: Callable[[MarketBar], None]):
        """Add callback for new market data"""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[MarketBar], None]):
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _notify_callbacks(self, market_bar: MarketBar):
        """Notify all callbacks of new data"""
        for callback in self.callbacks:
            try:
                callback(market_bar)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to data source"""
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from data source"""
        pass

    @abstractmethod
    async def fetch_historical(self, timeframe: Timeframe, limit: int = 1000) -> list[MarketBar]:
        """Fetch historical OHLCV data"""
        pass

    def _calculate_reconnect_delay(self) -> float:
        """Calculate delay for next reconnection attempt"""
        delay = min(
            self.reconnect_config.initial_delay * (
                self.reconnect_config.backoff_multiplier ** self._reconnect_count
            ),
            self.reconnect_config.max_delay
        )

        if self.reconnect_config.jitter:
            delay *= (0.5 + np.random.random() * 0.5)

        return delay


class WebSocketAdapter(MarketDataAdapter):
    """WebSocket-based market data adapter"""

    def __init__(self, symbol: str, timeframes: list[Timeframe], ws_url: str):
        super().__init__(symbol, timeframes)
        self.ws_url = ws_url
        self.websocket = None
        self._running = False
        self._message_hashes = deque(maxlen=1000)  # For duplicate detection

    async def connect(self) -> bool:
        """Connect to WebSocket"""
        try:
            self.state = ConnectionState.CONNECTING
            self.websocket = await websockets.connect(self.ws_url)
            self.state = ConnectionState.CONNECTED
            self._running = True
            self._reconnect_count = 0

            # Start message processing task
            asyncio.create_task(self._process_messages())

            logger.info(f"Connected to WebSocket for {self.symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect WebSocket for {self.symbol}: {e}")
            self.state = ConnectionState.FAILED
            return False

    async def disconnect(self):
        """Disconnect from WebSocket"""
        self._running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.state = ConnectionState.DISCONNECTED
        logger.info(f"Disconnected WebSocket for {self.symbol}")

    async def _process_messages(self):
        """Process incoming WebSocket messages"""
        while self._running and self.websocket:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
                await self._handle_message(message)
                self.last_heartbeat = datetime.now(UTC)

            except asyncio.TimeoutError:
                logger.warning(f"WebSocket timeout for {self.symbol}")
                await self._attempt_reconnect()
                break

            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket connection closed for {self.symbol}")
                await self._attempt_reconnect()
                break

            except Exception as e:
                logger.error(f"Error processing WebSocket message for {self.symbol}: {e}")
                self.quality_metrics.failed_messages += 1

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket message"""
        self.quality_metrics.total_messages += 1

        try:
            # Check for duplicates
            message_hash = hashlib.md5(message.encode()).hexdigest()
            if message_hash in self._message_hashes:
                self.quality_metrics.duplicate_messages += 1
                return
            self._message_hashes.append(message_hash)

            # Parse message (implementation depends on exchange format)
            data = json.loads(message)
            market_bar = self._parse_ohlcv(data)

            if market_bar:
                self.quality_metrics.parsed_messages += 1
                self._notify_callbacks(market_bar)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            self.quality_metrics.failed_messages += 1
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.quality_metrics.failed_messages += 1

    def _parse_ohlcv(self, data: dict) -> Optional[MarketBar]:
        """Parse OHLCV data from WebSocket message"""
        # This is a generic implementation - would need to be customized per exchange
        try:
            if 'k' in data:  # Binance format
                kline = data['k']
                market_bar = MarketBar(
                    symbol=self.symbol,
                    timeframe=Timeframe(kline['i']),
                    timestamp=datetime.fromtimestamp(kline['t'] / 1000),
                    open=Decimal(str(kline['o'])),
                    high=Decimal(str(kline['h'])),
                    low=Decimal(str(kline['l'])),
                    close=Decimal(str(kline['c'])),
                    volume=Decimal(str(kline['v']))
                )
                return market_bar

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing OHLCV data: {e}")

        return None

    async def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        if self._reconnect_count >= self.reconnect_config.max_retries:
            logger.error(f"Max reconnection attempts reached for {self.symbol}")
            self.state = ConnectionState.FAILED
            return

        self.state = ConnectionState.RECONNECTING
        self._reconnect_count += 1

        delay = self._calculate_reconnect_delay()
        logger.info(f"Reconnecting to {self.symbol} in {delay:.2f}s (attempt {self._reconnect_count})")

        await asyncio.sleep(delay)

        if await self.connect():
            logger.info(f"Successfully reconnected to {self.symbol}")
        else:
            await self._attempt_reconnect()

    async def fetch_historical(self, timeframe: Timeframe, limit: int = 1000) -> list[MarketBar]:
        """Fetch historical data via REST API"""
        # This would typically use a REST endpoint
        # Implementation depends on the specific exchange
        return []


class RESTAdapter(MarketDataAdapter):
    """REST API-based market data adapter"""

    def __init__(self, symbol: str, timeframes: list[Timeframe], base_url: str):
        super().__init__(symbol, timeframes)
        self.base_url = base_url
        self.session = None

    async def connect(self) -> bool:
        """Initialize HTTP session"""
        try:
            self.session = aiohttp.ClientSession()
            self.state = ConnectionState.CONNECTED
            logger.info(f"Initialized REST adapter for {self.symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize REST adapter: {e}")
            self.state = ConnectionState.FAILED
            return False

    async def disconnect(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        self.state = ConnectionState.DISCONNECTED

    async def fetch_historical(self, timeframe: Timeframe, limit: int = 1000) -> list[MarketBar]:
        """Fetch historical OHLCV data"""
        if not self.session:
            raise RuntimeError("REST adapter not connected")

        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': self.symbol,
                'interval': timeframe.value,
                'limit': limit
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_historical_data(data, timeframe)
                else:
                    logger.error(f"REST API error: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []

    def _parse_historical_data(self, data: list, timeframe: Timeframe) -> list[MarketBar]:
        """Parse historical OHLCV data from REST response"""
        market_bars = []

        for item in data:
            try:
                # Binance format: [timestamp, open, high, low, close, volume, ...]
                market_bar = MarketBar(
                    symbol=self.symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(item[0] / 1000),
                    open=Decimal(str(item[1])),
                    high=Decimal(str(item[2])),
                    low=Decimal(str(item[3])),
                    close=Decimal(str(item[4])),
                    volume=Decimal(str(item[5]))
                )
                market_bars.append(market_bar)

            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"Error parsing OHLCV item: {e}")
                continue

        self.quality_metrics.total_messages += len(data)
        self.quality_metrics.parsed_messages += len(market_bars)
        self.quality_metrics.failed_messages += len(data) - len(market_bars)

        return market_bars


class MarketDataIngestion:
    """Main market data ingestion system that orchestrates multiple adapters."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.adapters: dict[str, MarketDataAdapter] = {}
        self.data_cache: dict[str, list[MarketBar]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start all market data adapters."""
        self.logger.info("Starting market data ingestion system")

        # Initialize adapters based on config
        for source in self.config.get('sources', ['binance']):
            if source == 'binance':
                # Mock adapter for demo
                adapter = RESTAdapter(
                    symbol='BTCUSDT',
                    timeframes=[Timeframe.HOUR_1, Timeframe.HOUR_4],
                    base_url='https://api.binance.com/api/v3'
                )
                await adapter.connect()
                self.adapters[source] = adapter

    async def stop(self):
        """Stop all market data adapters."""
        self.logger.info("Stopping market data ingestion system")

        for adapter in self.adapters.values():
            await adapter.disconnect()

        self.adapters.clear()

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch OHLCV data for a symbol and timeframe."""
        # Mock implementation for demo
        mock_data = []
        for i in range(limit):
            mock_data.append({
                'open': 50000 + i,
                'high': 50100 + i,
                'low': 49900 + i,
                'close': 50050 + i,
                'volume': 100 + i,
                'timestamp': datetime.now().timestamp() - (limit - i) * 3600
            })

        return mock_data

    async def fetch_multi_timeframe_data(self, symbol: str, timeframes: list[str]) -> dict[str, list[dict[str, Any]]]:
        """Fetch data for multiple timeframes."""
        result = {}

        for timeframe in timeframes:
            result[timeframe] = await self.fetch_ohlcv(symbol, timeframe)

        return result

    async def reconnect(self):
        """Reconnect all adapters."""
        for adapter in self.adapters.values():
            if adapter.state != ConnectionState.CONNECTED:
                await adapter.connect()
