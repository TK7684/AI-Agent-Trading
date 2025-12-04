"""
Unit tests for market data ingestion and synchronization system.
Tests WebSocket reconnection, data quality, and multi-timeframe sync.
"""

import asyncio
import json
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.trading_models.data_synchronizer import (
    DataSynchronizer,
    SyncConfiguration,
    TimeframeBuffer,
    TimeframeSyncStatus,
)
from libs.trading_models.enums import Timeframe
from libs.trading_models.market_data import MarketBar
from libs.trading_models.market_data_ingestion import (
    ConnectionState,
    DataQualityMetrics,
    ReconnectConfig,
    RESTAdapter,
    WebSocketAdapter,
)


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self, messages: list[str], fail_after: int = None):
        self.messages = messages
        self.fail_after = fail_after
        self.message_count = 0
        self.closed = False

    async def recv(self):
        if self.closed:
            raise Exception("WebSocket closed")

        if self.fail_after and self.message_count >= self.fail_after:
            raise Exception("Simulated WebSocket failure")

        if self.message_count >= len(self.messages):
            # Simulate timeout
            await asyncio.sleep(1)
            raise asyncio.TimeoutError()

        message = self.messages[self.message_count]
        self.message_count += 1
        return message

    async def close(self):
        self.closed = True


class TestDataQualityMetrics:
    """Test data quality metrics"""

    def test_quality_metrics_initialization(self):
        """Test quality metrics initialization"""
        metrics = DataQualityMetrics()

        assert metrics.total_messages == 0
        assert metrics.parsed_messages == 0
        assert metrics.failed_messages == 0
        assert metrics.parse_success_rate == 0.0
        assert metrics.quality_score == 0.0

    def test_quality_metrics_calculation(self):
        """Test quality metrics calculations"""
        metrics = DataQualityMetrics()

        # Simulate some message processing
        metrics.total_messages = 100
        metrics.parsed_messages = 95
        metrics.failed_messages = 3
        metrics.duplicate_messages = 2

        assert metrics.parse_success_rate == 0.95

        # Quality score should account for all error types
        expected_quality = 0.95 - 0.02 - 0.03  # parse_rate - duplicate_rate - error_rate
        assert abs(metrics.quality_score - expected_quality) < 0.01


class TestWebSocketAdapter:
    """Test WebSocket adapter functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.symbol = "BTCUSDT"
        self.timeframes = [Timeframe.M15, Timeframe.H1]
        self.ws_url = "wss://test.example.com/ws"

    def test_adapter_initialization(self):
        """Test adapter initialization"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        assert adapter.symbol == self.symbol
        assert adapter.timeframes == self.timeframes
        assert adapter.ws_url == self.ws_url
        assert adapter.state == ConnectionState.DISCONNECTED
        assert len(adapter.callbacks) == 0

    def test_callback_management(self):
        """Test callback add/remove functionality"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        callback1 = Mock()
        callback2 = Mock()

        # Add callbacks
        adapter.add_callback(callback1)
        adapter.add_callback(callback2)
        assert len(adapter.callbacks) == 2

        # Remove callback
        adapter.remove_callback(callback1)
        assert len(adapter.callbacks) == 1
        assert callback2 in adapter.callbacks

    @pytest.mark.asyncio
    async def test_websocket_connection_success(self):
        """Test successful WebSocket connection"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        with patch('websockets.connect') as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            result = await adapter.connect()

            assert result is True
            assert adapter.state == ConnectionState.CONNECTED
            assert adapter.websocket == mock_ws
            mock_connect.assert_called_once_with(self.ws_url)

    @pytest.mark.asyncio
    async def test_websocket_connection_failure(self):
        """Test WebSocket connection failure"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            result = await adapter.connect()

            assert result is False
            assert adapter.state == ConnectionState.FAILED

    @pytest.mark.asyncio
    async def test_message_parsing(self):
        """Test WebSocket message parsing"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        # Test Binance-style message
        test_message = {
            "k": {
                "t": 1640995200000,  # Timestamp
                "o": "50000.00",     # Open
                "h": "50100.00",     # High
                "l": "49900.00",     # Low
                "c": "50050.00",     # Close
                "v": "1.5",          # Volume
                "i": "15m"           # Interval
            }
        }

        result = adapter._parse_ohlcv(test_message)

        assert result is not None
        market_bar = result

        assert isinstance(market_bar, MarketBar)
        assert float(market_bar.open) == 50000.00
        assert float(market_bar.high) == 50100.00
        assert float(market_bar.low) == 49900.00
        assert float(market_bar.close) == 50050.00
        assert float(market_bar.volume) == 1.5
        assert market_bar.timeframe == Timeframe("15m")

    @pytest.mark.asyncio
    async def test_message_processing_with_callbacks(self):
        """Test message processing with callbacks"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        callback = Mock()
        adapter.add_callback(callback)

        test_message = json.dumps({
            "k": {
                "t": 1640995200000,
                "o": "50000.00",
                "h": "50100.00",
                "l": "49900.00",
                "c": "50050.00",
                "v": "1.5",
                "i": "15m"
            }
        })

        await adapter._handle_message(test_message)

        # Verify callback was called
        callback.assert_called_once()
        args = callback.call_args[0]
        assert len(args) == 1
        assert isinstance(args[0], MarketBar)

        # Verify quality metrics
        assert adapter.quality_metrics.total_messages == 1
        assert adapter.quality_metrics.parsed_messages == 1

    @pytest.mark.asyncio
    async def test_duplicate_message_detection(self):
        """Test duplicate message detection"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)

        test_message = json.dumps({"k": {"t": 1640995200000, "o": "50000", "h": "50000", "l": "50000", "c": "50000", "v": "1", "i": "15m"}})

        # Process same message twice
        await adapter._handle_message(test_message)
        await adapter._handle_message(test_message)

        assert adapter.quality_metrics.total_messages == 2
        assert adapter.quality_metrics.parsed_messages == 1
        assert adapter.quality_metrics.duplicate_messages == 1

    def test_reconnect_delay_calculation(self):
        """Test reconnection delay calculation"""
        adapter = WebSocketAdapter(self.symbol, self.timeframes, self.ws_url)
        adapter.reconnect_config = ReconnectConfig(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            jitter=False
        )

        # Test exponential backoff
        adapter._reconnect_count = 0
        delay1 = adapter._calculate_reconnect_delay()
        assert delay1 == 1.0

        adapter._reconnect_count = 1
        delay2 = adapter._calculate_reconnect_delay()
        assert delay2 == 2.0

        adapter._reconnect_count = 2
        delay3 = adapter._calculate_reconnect_delay()
        assert delay3 == 4.0

        # Test max delay cap
        adapter._reconnect_count = 10
        delay_max = adapter._calculate_reconnect_delay()
        assert delay_max == 60.0


class TestRESTAdapter:
    """Test REST adapter functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.symbol = "BTCUSDT"
        self.timeframes = [Timeframe.H1]
        self.base_url = "https://api.test.com"

    @pytest.mark.asyncio
    async def test_rest_adapter_connection(self):
        """Test REST adapter connection"""
        adapter = RESTAdapter(self.symbol, self.timeframes, self.base_url)

        result = await adapter.connect()

        assert result is True
        assert adapter.state == ConnectionState.CONNECTED
        assert adapter.session is not None

        await adapter.disconnect()
        assert adapter.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_historical_data_fetch(self):
        """Test historical data fetching"""
        adapter = RESTAdapter(self.symbol, self.timeframes, self.base_url)
        await adapter.connect()

        # Mock HTTP response
        mock_response_data = [
            [1640995200000, "50000.00", "50100.00", "49900.00", "50050.00", "1.5"],
            [1640998800000, "50050.00", "50200.00", "50000.00", "50150.00", "2.0"]
        ]

        with patch.object(adapter.session, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await adapter.fetch_historical(Timeframe.H1, 100)

            assert len(result) == 2
            assert all(isinstance(market_bar, MarketBar) for market_bar in result)

            # Verify first MarketBar
            first = result[0]
            assert float(first.open) == 50000.00
            assert float(first.high) == 50100.00
            assert float(first.low) == 49900.00
            assert float(first.close) == 50050.00
            assert float(first.volume) == 1.5

        await adapter.disconnect()


class TestTimeframeBuffer:
    """Test timeframe buffer functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.timeframe = Timeframe.H1
        self.buffer = TimeframeBuffer(self.timeframe, max_size=10)

    def test_buffer_initialization(self):
        """Test buffer initialization"""
        assert self.buffer.timeframe == self.timeframe
        assert self.buffer.max_size == 10
        assert len(self.buffer.data) == 0
        assert self.buffer.last_update is None

    def test_add_data_success(self):
        """Test successful data addition"""
        market_bar1 = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 1, 10, 0),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000")
        )

        result = self.buffer.add_data(market_bar1)

        assert result is True
        assert len(self.buffer.data) == 1
        assert self.buffer.last_update is not None

    def test_add_data_out_of_order(self):
        """Test out-of-order data rejection"""
        market_bar1 = MarketBar(
            symbol="BTCUSDT", timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 1, 11, 0),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000")
        )
        market_bar2 = MarketBar(
            symbol="BTCUSDT", timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 1, 10, 0),  # Earlier timestamp
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000")
        )

        assert self.buffer.add_data(market_bar1) is True
        assert self.buffer.add_data(market_bar2) is False  # Should be rejected
        assert len(self.buffer.data) == 1

    def test_buffer_max_size(self):
        """Test buffer max size enforcement"""
        # Add more data than max size
        for i in range(15):
            # Ensure hour stays within 0-23 range by using modulo
            market_bar = MarketBar(
                symbol="BTCUSDT", timeframe=Timeframe.H1,
                timestamp=datetime(2024, 1, 1, (10 + i) % 24, 0),
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
                close=Decimal("100.5"), volume=Decimal("1000")
            )
            self.buffer.add_data(market_bar)

        # Should only keep last 10 items
        assert len(self.buffer.data) == 10
        assert self.buffer.data[0].timestamp == datetime(2024, 1, 1, 15, 0)

    def test_get_data(self):
        """Test data retrieval"""
        # Add test data
        for i in range(5):
            market_bar = MarketBar(
                symbol="BTCUSDT", timeframe=Timeframe.H1,
                timestamp=datetime(2024, 1, 1, 10 + i, 0),
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
                close=Decimal("100.5"), volume=Decimal("1000")
            )
            self.buffer.add_data(market_bar)

        # Get all data
        all_data = self.buffer.get_data()
        assert len(all_data) == 5

        # Get limited data
        limited_data = self.buffer.get_data(3)
        assert len(limited_data) == 3
        assert limited_data[-1].timestamp == datetime(2024, 1, 1, 14, 0)

    def test_clear_old_data(self):
        """Test old data cleanup"""
        # Add data with different timestamps
        timestamps = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 1, 11, 0),
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 13, 0),
        ]

        for ts in timestamps:
            market_bar = MarketBar(
                symbol="BTCUSDT", timeframe=Timeframe.H1,
                timestamp=ts,
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
                close=Decimal("100.5"), volume=Decimal("1000")
            )
            self.buffer.add_data(market_bar)

        # Clear data older than 12:00
        cutoff = datetime(2024, 1, 1, 12, 0)
        self.buffer.clear_old_data(cutoff)

        assert len(self.buffer.data) == 2
        assert self.buffer.data[0].timestamp >= cutoff


class TestDataSynchronizer:
    """Test data synchronization functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.symbol = "BTCUSDT"
        self.timeframes = [Timeframe.M15, Timeframe.H1]
        self.config = SyncConfiguration(
            max_clock_skew_ms=250,
            sync_timeout_ms=100,
            min_data_points=10  # Lower for testing
        )
        self.synchronizer = DataSynchronizer(self.symbol, self.timeframes, self.config)

    def test_synchronizer_initialization(self):
        """Test synchronizer initialization"""
        assert self.synchronizer.symbol == self.symbol
        assert self.synchronizer.timeframes == self.timeframes
        assert len(self.synchronizer.buffers) == 2
        assert len(self.synchronizer.sync_status) == 2

        for tf in self.timeframes:
            assert tf in self.synchronizer.buffers
            assert tf in self.synchronizer.sync_status
            assert isinstance(self.synchronizer.sync_status[tf], TimeframeSyncStatus)

    def test_add_adapter(self):
        """Test adapter addition"""
        mock_adapter = Mock()
        mock_adapter.add_callback = Mock()

        self.synchronizer.add_adapter(mock_adapter)

        assert mock_adapter in self.synchronizer.adapters
        mock_adapter.add_callback.assert_called_once()

    def test_market_data_callback(self):
        """Test market data callback processing"""
        market_bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.M15,
            timestamp=datetime.now(UTC),
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000")
        )

        # Test with valid timeframe
        self.synchronizer._on_market_data(market_bar)

        # Verify data was added to buffer
        buffer = self.synchronizer.buffers[Timeframe.M15]
        assert len(buffer.data) == 1
        assert buffer.data[0] == market_bar

        # Verify sync status was updated
        status = self.synchronizer.sync_status[Timeframe.M15]
        assert status.last_update is not None
        assert status.data_count == 1

    def test_clock_skew_detection(self):
        """Test clock skew detection"""
        # Create MarketBar with old timestamp (should trigger clock skew warning)
        old_timestamp = datetime.now(UTC) - timedelta(seconds=10)  # 10 seconds old
        market_bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.M15,
            timestamp=old_timestamp,
            open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
            close=Decimal("100.5"), volume=Decimal("1000")
        )

        with patch('libs.trading_models.data_synchronizer.logger') as mock_logger:
            self.synchronizer._on_market_data(market_bar)

            # Should log clock skew warning
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Clock skew detected" in warning_msg

    @pytest.mark.asyncio
    async def test_synchronization_check(self):
        """Test synchronization checking logic"""
        # Add sufficient data to both timeframes
        now = datetime.now(UTC)

        for i in range(15):  # More than min_data_points
            for tf in self.timeframes:
                market_bar = MarketBar(
                    symbol="BTCUSDT",
                    timeframe=tf,
                    timestamp=now + timedelta(minutes=i),
                    open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
                    close=Decimal("100.5"), volume=Decimal("1000")
                )
                self.synchronizer._on_market_data(market_bar)

        # Mock adapter quality metrics
        mock_adapter = Mock()
        mock_adapter.quality_metrics.quality_score = 0.98
        self.synchronizer.adapters = [mock_adapter]

        # Trigger synchronization check
        await self.synchronizer._check_synchronization()

        # Verify synchronization status
        for tf in self.timeframes:
            status = self.synchronizer.sync_status[tf]
            assert status.is_synchronized is True
            assert status.quality_score >= 0.95

    def test_get_synchronized_data(self):
        """Test synchronized data retrieval"""
        # Add data and mark as synchronized
        now = datetime.now(UTC)

        for i in range(5):
            market_bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.M15,
                timestamp=now + timedelta(minutes=i),
                open=Decimal("100"), high=Decimal("101"), low=Decimal("99"),
                close=Decimal("100.5"), volume=Decimal("1000")
            )
            self.synchronizer._on_market_data(market_bar)

        # Mark as synchronized
        self.synchronizer.sync_status[Timeframe.M15].is_synchronized = True

        sync_data = self.synchronizer.get_synchronized_data()

        assert Timeframe.M15 in sync_data
        assert len(sync_data[Timeframe.M15]) == 5
        assert Timeframe.H1 not in sync_data  # Not synchronized

    def test_quality_metrics_aggregation(self):
        """Test quality metrics aggregation"""
        # Mock adapters with different metrics
        adapter1 = Mock()
        adapter1.quality_metrics = DataQualityMetrics()
        adapter1.quality_metrics.total_messages = 100
        adapter1.quality_metrics.parsed_messages = 95
        adapter1.quality_metrics.failed_messages = 5

        adapter2 = Mock()
        adapter2.quality_metrics = DataQualityMetrics()
        adapter2.quality_metrics.total_messages = 200
        adapter2.quality_metrics.parsed_messages = 190
        adapter2.quality_metrics.failed_messages = 10

        self.synchronizer.adapters = [adapter1, adapter2]

        metrics = self.synchronizer.get_quality_metrics()

        assert metrics['total_messages'] == 300
        assert metrics['parsed_messages'] == 285
        assert metrics['failed_messages'] == 15
        assert abs(metrics['parse_success_rate'] - 0.95) < 0.01

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Test synchronizer start/stop lifecycle"""
        # Mock adapter
        mock_adapter = AsyncMock()
        self.synchronizer.adapters = [mock_adapter]

        # Test start
        await self.synchronizer.start()
        assert self.synchronizer.is_running is True
        mock_adapter.connect.assert_called_once()

        # Test stop
        await self.synchronizer.stop()
        assert self.synchronizer.is_running is False
        mock_adapter.disconnect.assert_called_once()


if __name__ == "__main__":
    # Run tests manually for debugging

    print("Running market data ingestion tests...")

    # Test data quality metrics
    test_metrics = TestDataQualityMetrics()
    test_metrics.test_quality_metrics_initialization()
    test_metrics.test_quality_metrics_calculation()
    print("✓ Data quality metrics tests passed")

    # Test WebSocket adapter
    test_ws = TestWebSocketAdapter()
    test_ws.setup_method()
    test_ws.test_adapter_initialization()
    test_ws.test_callback_management()
    test_ws.test_reconnect_delay_calculation()
    print("✓ WebSocket adapter tests passed")

    # Test timeframe buffer
    test_buffer = TestTimeframeBuffer()
    test_buffer.setup_method()
    test_buffer.test_buffer_initialization()
    test_buffer.test_add_data_success()
    test_buffer.test_add_data_out_of_order()
    test_buffer.test_buffer_max_size()
    test_buffer.test_get_data()
    test_buffer.test_clear_old_data()
    print("✓ Timeframe buffer tests passed")

    # Test data synchronizer
    test_sync = TestDataSynchronizer()
    test_sync.setup_method()
    test_sync.test_synchronizer_initialization()
    test_sync.test_add_adapter()
    test_sync.test_market_data_callback()
    test_sync.test_clock_skew_detection()
    test_sync.test_get_synchronized_data()
    test_sync.test_quality_metrics_aggregation()
    print("✓ Data synchronizer tests passed")

    print("All market data ingestion tests passed!")
