"""
Multi-Timeframe Data Synchronization System

This module handles synchronization of market data across multiple timeframes
with clock-skew protection and data quality validation.
"""

import asyncio
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from .enums import Timeframe
from .market_data import MarketBar
from .market_data_ingestion import MarketDataAdapter
from .technical_indicators import IndicatorEngine

logger = logging.getLogger(__name__)


@dataclass
class TimeframeSyncStatus:
    """Status of timeframe synchronization"""
    timeframe: Timeframe
    last_update: Optional[datetime] = None
    data_count: int = 0
    sync_latency_ms: float = 0.0
    is_synchronized: bool = False
    quality_score: float = 0.0


@dataclass
class SyncConfiguration:
    """Configuration for data synchronization"""
    max_clock_skew_ms: int = 250  # Maximum allowed clock skew
    sync_timeout_ms: int = 100    # Target sync latency
    buffer_size: int = 1000       # Size of data buffers
    min_data_points: int = 200    # Minimum data points for analysis
    quality_threshold: float = 0.95  # Minimum quality score


class TimeframeBuffer:
    """Buffer for storing OHLCV data for a specific timeframe"""

    def __init__(self, timeframe: Timeframe, max_size: int = 1000):
        self.timeframe = timeframe
        self.max_size = max_size
        self.data: deque[MarketBar] = deque(maxlen=max_size)
        self.last_update = None
        self.lock = threading.RLock()

    def add_data(self, market_bar: MarketBar) -> bool:
        """Add OHLCV data to buffer with validation"""
        with self.lock:
            # Validate timestamp ordering
            if self.data and market_bar.timestamp <= self.data[-1].timestamp:
                logger.warning(f"Out-of-order data for {self.timeframe}: {market_bar.timestamp}")
                return False

            self.data.append(market_bar)
            self.last_update = datetime.now(UTC)
            return True

    def get_data(self, count: Optional[int] = None) -> list[MarketBar]:
        """Get data from buffer"""
        with self.lock:
            if count is None:
                return list(self.data)
            else:
                return list(self.data)[-count:] if count <= len(self.data) else list(self.data)

    def get_latest(self) -> Optional[MarketBar]:
        """Get latest OHLCV data"""
        with self.lock:
            return self.data[-1] if self.data else None

    def clear_old_data(self, cutoff_time: datetime):
        """Remove data older than cutoff time"""
        with self.lock:
            while self.data and self.data[0].timestamp < cutoff_time:
                self.data.popleft()


class DataSynchronizer:
    """Multi-timeframe data synchronization manager"""

    def __init__(self, symbol: str, timeframes: list[Timeframe], config: Optional[SyncConfiguration] = None):
        self.symbol = symbol
        self.timeframes = timeframes
        self.config = config or SyncConfiguration()

        # Data buffers for each timeframe
        self.buffers: dict[Timeframe, TimeframeBuffer] = {
            tf: TimeframeBuffer(tf, self.config.buffer_size) for tf in timeframes
        }

        # Synchronization status
        self.sync_status: dict[Timeframe, TimeframeSyncStatus] = {
            tf: TimeframeSyncStatus(tf) for tf in timeframes
        }

        # Adapters and callbacks
        self.adapters: list[MarketDataAdapter] = []
        self.sync_callbacks: list[Callable[[dict[Timeframe, list[OHLCV]]], None]] = []

        # Indicator engine
        self.indicator_engine = IndicatorEngine()

        # Synchronization control
        self.is_running = False
        self.sync_task = None
        self.last_sync_time = datetime.now(UTC)

    def add_adapter(self, adapter: MarketDataAdapter):
        """Add market data adapter"""
        adapter.add_callback(self._on_market_data)
        self.adapters.append(adapter)
        logger.info(f"Added adapter for {self.symbol}")

    def add_sync_callback(self, callback: Callable[[dict[Timeframe, list[MarketBar]]], None]):
        """Add callback for synchronized data"""
        self.sync_callbacks.append(callback)

    def _on_market_data(self, market_bar: MarketBar):
        """Handle incoming market data"""
        timeframe = market_bar.timeframe
        if timeframe not in self.buffers:
            logger.warning(f"Received data for unknown timeframe: {timeframe}")
            return

        # Check clock skew
        now = datetime.now(UTC)
        time_diff = abs((now - market_bar.timestamp).total_seconds() * 1000)

        if time_diff > self.config.max_clock_skew_ms:
            logger.warning(f"Clock skew detected: {time_diff}ms for {timeframe}")
            # Still process the data but mark quality issue

        # Add to buffer
        if self.buffers[timeframe].add_data(market_bar):
            # Update sync status
            self.sync_status[timeframe].last_update = now
            self.sync_status[timeframe].data_count = len(self.buffers[timeframe].data)

            # Trigger synchronization check
            asyncio.create_task(self._check_synchronization())

    async def _check_synchronization(self):
        """Check if all timeframes are synchronized"""
        sync_start = time.time()

        try:
            # Check if all timeframes have recent data
            now = datetime.now(UTC)
            all_synchronized = True

            for timeframe in self.timeframes:
                status = self.sync_status[timeframe]
                buffer = self.buffers[timeframe]

                # Check data availability
                if len(buffer.data) < self.config.min_data_points:
                    all_synchronized = False
                    status.is_synchronized = False
                    continue

                # Check data freshness (within reasonable time window)
                if status.last_update:
                    age_seconds = (now - status.last_update).total_seconds()
                    max_age = self._get_max_age_for_timeframe(timeframe)

                    if age_seconds > max_age:
                        all_synchronized = False
                        status.is_synchronized = False
                        continue

                # Calculate quality score from adapters
                quality_scores = [adapter.quality_metrics.quality_score for adapter in self.adapters]
                status.quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

                if status.quality_score < self.config.quality_threshold:
                    all_synchronized = False
                    status.is_synchronized = False
                    continue

                status.is_synchronized = True

            # Calculate sync latency
            sync_latency = (time.time() - sync_start) * 1000

            # Update sync latencies
            for status in self.sync_status.values():
                status.sync_latency_ms = sync_latency

            # If all synchronized and within latency target, notify callbacks
            if all_synchronized and sync_latency <= self.config.sync_timeout_ms:
                await self._notify_sync_callbacks()
                self.last_sync_time = now

        except Exception as e:
            logger.error(f"Error in synchronization check: {e}")

    def _get_max_age_for_timeframe(self, timeframe: Timeframe) -> float:
        """Get maximum allowed age for timeframe data"""
        # Map timeframe to seconds
        timeframe_seconds = {
            Timeframe.M15: 15 * 60,
            Timeframe.H1: 60 * 60,
            Timeframe.H4: 4 * 60 * 60,
            Timeframe.D1: 24 * 60 * 60
        }

        base_seconds = timeframe_seconds.get(timeframe, 60 * 60)  # Default 1 hour
        return base_seconds * 2  # Allow 2x the timeframe period

    async def _notify_sync_callbacks(self):
        """Notify all sync callbacks with current data"""
        try:
            # Prepare synchronized data
            sync_data = {}
            for timeframe in self.timeframes:
                if self.sync_status[timeframe].is_synchronized:
                    sync_data[timeframe] = self.buffers[timeframe].get_data()

            # Notify callbacks
            for callback in self.sync_callbacks:
                try:
                    callback(sync_data)
                except Exception as e:
                    logger.error(f"Error in sync callback: {e}")

        except Exception as e:
            logger.error(f"Error notifying sync callbacks: {e}")

    async def start(self):
        """Start data synchronization"""
        if self.is_running:
            return

        self.is_running = True

        # Connect all adapters
        for adapter in self.adapters:
            await adapter.connect()

        # Start periodic cleanup task
        self.sync_task = asyncio.create_task(self._periodic_cleanup())

        logger.info(f"Started data synchronization for {self.symbol}")

    async def stop(self):
        """Stop data synchronization"""
        self.is_running = False

        # Cancel sync task
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

        # Disconnect all adapters
        for adapter in self.adapters:
            await adapter.disconnect()

        logger.info(f"Stopped data synchronization for {self.symbol}")

    async def _periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while self.is_running:
            try:
                # Clean up old data (keep last 24 hours)
                cutoff_time = datetime.now(UTC) - timedelta(hours=24)

                for buffer in self.buffers.values():
                    buffer.clear_old_data(cutoff_time)

                # Sleep for 1 hour
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute

    def get_synchronized_data(self) -> dict[Timeframe, list[MarketBar]]:
        """Get current synchronized data"""
        result = {}

        for timeframe in self.timeframes:
            if self.sync_status[timeframe].is_synchronized:
                result[timeframe] = self.buffers[timeframe].get_data()

        return result

    def get_sync_status(self) -> dict[Timeframe, TimeframeSyncStatus]:
        """Get synchronization status for all timeframes"""
        return self.sync_status.copy()

    def calculate_indicators_for_all_timeframes(self) -> dict[Timeframe, dict[str, Any]]:
        """Calculate technical indicators for all synchronized timeframes"""
        results = {}

        for timeframe in self.timeframes:
            if self.sync_status[timeframe].is_synchronized:
                data = self.buffers[timeframe].get_data()
                if len(data) >= 200:  # Minimum data for indicators
                    indicators = self.indicator_engine.calculate_all_indicators(data)
                    results[timeframe] = indicators
                else:
                    logger.warning(f"Insufficient data for indicators on {timeframe}: {len(data)}")

        return results

    async def fetch_historical_data(self, days: int = 30):
        """Fetch historical data for all timeframes"""
        logger.info(f"Fetching {days} days of historical data for {self.symbol}")

        for adapter in self.adapters:
            for timeframe in self.timeframes:
                try:
                    # Calculate required data points
                    timeframe_minutes = {
                        Timeframe.M15: 15,
                        Timeframe.H1: 60,
                        Timeframe.H4: 240,
                        Timeframe.D1: 1440
                    }

                    minutes_per_day = 1440
                    points_per_day = minutes_per_day // timeframe_minutes.get(timeframe, 60)
                    limit = min(1000, points_per_day * days)  # API limits

                    historical_data = await adapter.fetch_historical(timeframe, limit)

                    # Add to buffers
                    for ohlcv in historical_data:
                        self.buffers[timeframe].add_data(ohlcv)

                    logger.info(f"Loaded {len(historical_data)} historical bars for {timeframe}")

                except Exception as e:
                    logger.error(f"Error fetching historical data for {timeframe}: {e}")

    def get_quality_metrics(self) -> dict[str, Any]:
        """Get overall data quality metrics"""
        adapter_metrics = [adapter.quality_metrics for adapter in self.adapters]

        if not adapter_metrics:
            return {}

        # Aggregate metrics
        total_messages = sum(m.total_messages for m in adapter_metrics)
        parsed_messages = sum(m.parsed_messages for m in adapter_metrics)
        failed_messages = sum(m.failed_messages for m in adapter_metrics)

        return {
            'total_messages': total_messages,
            'parsed_messages': parsed_messages,
            'failed_messages': failed_messages,
            'parse_success_rate': parsed_messages / total_messages if total_messages > 0 else 0.0,
            'timeframe_sync_status': {tf.value: status.is_synchronized
                                    for tf, status in self.sync_status.items()},
            'average_sync_latency_ms': sum(s.sync_latency_ms for s in self.sync_status.values()) / len(self.sync_status),
            'last_sync_time': self.last_sync_time.isoformat()
        }
