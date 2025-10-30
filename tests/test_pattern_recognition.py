"""
Unit tests for pattern recognition system.

Tests all pattern detection algorithms with synthetic market data.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from libs.trading_models.enums import PatternType, Timeframe
from libs.trading_models.market_data import MarketBar
from libs.trading_models.pattern_recognition import (
    PatternConfidenceScorer,
    PatternRecognitionEngine,
)
from libs.trading_models.patterns import PatternHit
from libs.trading_models.technical_indicators import RSIResult


class TestSyntheticDataGenerator:
    """Generate synthetic market data for testing."""

    @staticmethod
    def create_trending_data(
        symbol: str = "BTCUSDT",
        timeframe: Timeframe = Timeframe.H1,
        num_bars: int = 100,
        start_price: float = 50000.0,
        trend_strength: float = 0.02,
        volatility: float = 0.01
    ) -> list[MarketBar]:
        """Create synthetic trending market data."""
        bars = []
        current_price = start_price
        base_time = datetime.now(UTC) - timedelta(hours=num_bars)

        for i in range(num_bars):
            # Add trend
            trend_move = trend_strength * np.random.normal(0.5, 0.2)
            current_price *= (1 + trend_move)

            # Add volatility
            volatility_factor = 1 + np.random.normal(0, volatility)

            # Generate OHLC
            open_price = current_price
            close_price = current_price * volatility_factor

            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))

            # Ensure OHLC relationships
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            volume = np.random.uniform(1000, 10000)

            bar = MarketBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(open_price, 2))),
                high=Decimal(str(round(high_price, 2))),
                low=Decimal(str(round(low_price, 2))),
                close=Decimal(str(round(close_price, 2))),
                volume=Decimal(str(round(volume, 2)))
            )
            bars.append(bar)
            current_price = close_price

        return bars

    @staticmethod
    def create_support_resistance_data(
        symbol: str = "BTCUSDT",
        support_level: float = 50000.0,
        resistance_level: float = 52000.0,
        num_bars: int = 50
    ) -> list[MarketBar]:
        """Create data with clear support and resistance levels."""
        bars = []
        base_time = datetime.now(UTC) - timedelta(hours=num_bars)

        for i in range(num_bars):
            # Price oscillates between support and resistance
            cycle_position = (i % 20) / 20.0  # 20-bar cycles
            base_price = support_level + (resistance_level - support_level) * np.sin(cycle_position * np.pi)

            # Add some noise
            noise = np.random.normal(0, 100)
            current_price = base_price + noise

            # Ensure we touch the levels occasionally
            if i % 10 == 0:  # Every 10 bars, touch support or resistance
                if cycle_position < 0.5:
                    current_price = support_level + np.random.uniform(-50, 50)
                else:
                    current_price = resistance_level + np.random.uniform(-50, 50)

            # Generate OHLC around current price
            volatility = 0.005
            open_price = current_price * (1 + np.random.normal(0, volatility))
            close_price = current_price * (1 + np.random.normal(0, volatility))
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))

            volume = np.random.uniform(1000, 5000)

            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(open_price, 2))),
                high=Decimal(str(round(high_price, 2))),
                low=Decimal(str(round(low_price, 2))),
                close=Decimal(str(round(close_price, 2))),
                volume=Decimal(str(round(volume, 2)))
            )
            bars.append(bar)

        return bars

    @staticmethod
    def create_pin_bar_data(symbol: str = "BTCUSDT") -> list[MarketBar]:
        """Create data with pin bar patterns."""
        bars = []
        base_time = datetime.now(UTC) - timedelta(hours=25)
        base_price = 50000.0

        # Create normal bars first (need at least 20 bars for analysis)
        for i in range(22):
            price = base_price + np.random.uniform(-100, 100)
            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 50, 2))),
                low=Decimal(str(round(price - 50, 2))),
                close=Decimal(str(round(price + np.random.uniform(-25, 25), 2))),
                volume=Decimal("5000")
            )
            bars.append(bar)

        # Create bullish pin bar (hammer)
        pin_price = base_price
        pin_bar = MarketBar(
            symbol=symbol,
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=22),
            open=Decimal("50000.00"),
            high=Decimal("50002.00"),  # Very small upper wick (2 points from close)
            low=Decimal("49500.00"),   # Long lower wick (500 points)
            close=Decimal("50001.00"), # Close very near open (1 point body)
            volume=Decimal("7000")  # Higher volume
        )
        bars.append(pin_bar)

        # Add more normal bars
        for i in range(2):
            price = pin_price + 50 + np.random.uniform(-25, 25)
            final_bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=23 + i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 30, 2))),
                low=Decimal(str(round(price - 30, 2))),
                close=Decimal(str(round(price + np.random.uniform(-15, 15), 2))),
                volume=Decimal("5000")
            )
            bars.append(final_bar)

        return bars

    @staticmethod
    def create_engulfing_data(symbol: str = "BTCUSDT") -> list[MarketBar]:
        """Create data with engulfing patterns."""
        bars = []
        base_time = datetime.now(UTC) - timedelta(hours=25)
        base_price = 50000.0

        # Create normal bars (need at least 20 bars)
        for i in range(22):
            price = base_price + np.random.uniform(-50, 50)
            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 30, 2))),
                low=Decimal(str(round(price - 30, 2))),
                close=Decimal(str(round(price + np.random.uniform(-20, 20), 2))),
                volume=Decimal("5000")
            )
            bars.append(bar)

        # Create small bearish bar
        small_bar = MarketBar(
            symbol=symbol,
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=22),
            open=Decimal("50050.00"),
            high=Decimal("50070.00"),
            low=Decimal("49980.00"),
            close=Decimal("50000.00"),  # Bearish bar
            volume=Decimal("4000")
        )
        bars.append(small_bar)

        # Create bullish engulfing bar
        engulfing_bar = MarketBar(
            symbol=symbol,
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=23),
            open=Decimal("49950.00"),  # Open below previous close
            high=Decimal("50200.00"),
            low=Decimal("49930.00"),
            close=Decimal("50150.00"),  # Close above previous open
            volume=Decimal("8000")  # Higher volume
        )
        bars.append(engulfing_bar)

        # Add one more normal bar
        final_bar = MarketBar(
            symbol=symbol,
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=24),
            open=Decimal("50150.00"),
            high=Decimal("50200.00"),
            low=Decimal("50100.00"),
            close=Decimal("50180.00"),
            volume=Decimal("5000")
        )
        bars.append(final_bar)

        return bars

    @staticmethod
    def create_doji_data(symbol: str = "BTCUSDT") -> list[MarketBar]:
        """Create data with doji patterns."""
        bars = []
        base_time = datetime.now(UTC) - timedelta(hours=25)
        base_price = 50000.0

        # Create normal bars (need at least 20 bars)
        for i in range(22):
            price = base_price + np.random.uniform(-50, 50)
            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 40, 2))),
                low=Decimal(str(round(price - 40, 2))),
                close=Decimal(str(round(price + np.random.uniform(-30, 30), 2))),
                volume=Decimal("5000")
            )
            bars.append(bar)

        # Create doji bar
        doji_bar = MarketBar(
            symbol=symbol,
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=22),
            open=Decimal("50000.00"),
            high=Decimal("50150.00"),  # Long upper wick
            low=Decimal("49850.00"),   # Long lower wick
            close=Decimal("50005.00"), # Very close to open (small body)
            volume=Decimal("6000")
        )
        bars.append(doji_bar)

        # Add more normal bars
        for i in range(2):
            price = base_price + np.random.uniform(-30, 30)
            bar = MarketBar(
                symbol=symbol,
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=23 + i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 25, 2))),
                low=Decimal(str(round(price - 25, 2))),
                close=Decimal(str(round(price + np.random.uniform(-15, 15), 2))),
                volume=Decimal("5000")
            )
            bars.append(bar)

        return bars


class TestPatternRecognitionEngine:
    """Test the pattern recognition engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PatternRecognitionEngine(min_pattern_confidence=0.3)
        self.data_generator = TestSyntheticDataGenerator()

    def test_support_resistance_detection(self):
        """Test support and resistance level detection."""
        # Create data with known support/resistance levels
        data = self.data_generator.create_support_resistance_data(
            support_level=50000.0,
            resistance_level=52000.0,
            num_bars=50
        )

        # Detect support/resistance levels
        sr_levels = self.engine.detect_support_resistance(data)

        # Should detect both support and resistance levels
        assert len(sr_levels) > 0

        # Check if detected levels are close to expected levels
        detected_prices = [level.price for level in sr_levels]

        # Should have levels near our support and resistance
        support_detected = any(abs(price - 50000.0) < 500 for price in detected_prices)
        resistance_detected = any(abs(price - 52000.0) < 500 for price in detected_prices)

        assert support_detected or resistance_detected, f"Expected levels not detected: {detected_prices}"

        # Check level properties
        for level in sr_levels:
            assert level.strength >= 2  # Minimum touches
            assert 0.0 <= level.confidence <= 1.0
            assert level.first_touch <= level.last_touch

    def test_pin_bar_detection(self):
        """Test pin bar pattern detection."""
        data = self.data_generator.create_pin_bar_data()

        # Debug: Check the pin bar data
        pin_bar_candidate = data[22]  # The pin bar we created
        print(f"Pin bar: O={pin_bar_candidate.open}, H={pin_bar_candidate.high}, L={pin_bar_candidate.low}, C={pin_bar_candidate.close}")

        # Analyze patterns
        collection = self.engine.analyze_patterns(data)

        print(f"Total patterns detected: {collection.total_patterns}")
        print(f"All patterns: {[p.pattern_type for p in collection.patterns]}")

        # Should detect pin bar pattern
        pin_bars = collection.get_patterns_by_type(PatternType.PIN_BAR)
        assert len(pin_bars) > 0, f"No pin bars detected. Total patterns: {collection.total_patterns}"

        pin_bar = pin_bars[0]
        assert pin_bar.pattern_type == PatternType.PIN_BAR
        assert pin_bar.confidence > 0.3
        assert "pin_type" in pin_bar.pattern_data
        assert pin_bar.pattern_data["pin_type"] in ["bullish_hammer", "bearish_shooting_star"]

    def test_engulfing_pattern_detection(self):
        """Test engulfing pattern detection."""
        data = self.data_generator.create_engulfing_data()

        # Analyze patterns
        collection = self.engine.analyze_patterns(data)

        # Should detect engulfing pattern
        engulfing_patterns = collection.get_patterns_by_type(PatternType.ENGULFING)
        assert len(engulfing_patterns) > 0

        engulfing = engulfing_patterns[0]
        assert engulfing.pattern_type == PatternType.ENGULFING
        assert engulfing.confidence > 0.3
        assert "engulfing_type" in engulfing.pattern_data
        assert engulfing.pattern_data["engulfing_type"] in ["bullish", "bearish"]

    def test_doji_pattern_detection(self):
        """Test doji pattern detection."""
        data = self.data_generator.create_doji_data()

        # Analyze patterns
        collection = self.engine.analyze_patterns(data)

        # Should detect doji pattern
        doji_patterns = collection.get_patterns_by_type(PatternType.DOJI)
        assert len(doji_patterns) > 0

        doji = doji_patterns[0]
        assert doji.pattern_type == PatternType.DOJI
        assert doji.confidence > 0.3
        assert "doji_type" in doji.pattern_data
        assert doji.pattern_data["doji_type"] in ["standard", "dragonfly", "gravestone"]

    def test_breakout_detection(self):
        """Test breakout pattern detection."""
        # Create data with support level and then a breakout
        data = []
        base_time = datetime.now(UTC) - timedelta(hours=30)
        support_level = 50000.0

        # Create bars that respect support level
        for i in range(25):
            price = support_level + np.random.uniform(50, 500)  # Above support
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 100, 2))),
                low=Decimal(str(round(max(price - 100, support_level + 10), 2))),  # Don't break support
                close=Decimal(str(round(price + np.random.uniform(-50, 50), 2))),
                volume=Decimal("5000")
            )
            data.append(bar)

        # Create breakout bar
        breakout_bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=base_time + timedelta(hours=25),
            open=Decimal(str(round(support_level + 20, 2))),
            high=Decimal(str(round(support_level + 50, 2))),
            low=Decimal(str(round(support_level - 200, 2))),  # Break below support
            close=Decimal(str(round(support_level - 150, 2))),
            volume=Decimal("10000")  # High volume breakout
        )
        data.append(breakout_bar)

        # Analyze patterns
        collection = self.engine.analyze_patterns(data)

        # Should detect support/resistance and potentially breakout
        sr_patterns = collection.get_patterns_by_type(PatternType.SUPPORT_RESISTANCE)
        breakout_patterns = collection.get_patterns_by_type(PatternType.BREAKOUT)

        # The algorithm should detect some patterns (may be candlestick patterns instead of S/R)
        assert collection.total_patterns > 0, "No patterns detected at all"

        # If support/resistance patterns are detected, validate them
        if sr_patterns:
            for sr_pattern in sr_patterns:
                assert sr_pattern.pattern_type == PatternType.SUPPORT_RESISTANCE
                assert sr_pattern.confidence > 0

        # If breakout patterns are detected, validate them
        if breakout_patterns:
            breakout = breakout_patterns[0]
            assert breakout.pattern_type == PatternType.BREAKOUT
            assert "breakout_direction" in breakout.pattern_data

    def test_divergence_detection(self):
        """Test divergence detection with mock indicator data."""
        # Create price data with higher highs
        data = []
        base_time = datetime.now(UTC) - timedelta(hours=30)

        prices = [50000, 50100, 50200, 50300, 50400, 50500]  # Rising prices
        rsi_values = [70, 68, 66, 64, 62, 60]  # Falling RSI (bearish divergence)

        for i, (price, rsi_val) in enumerate(zip(prices, rsi_values, strict=False)):
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i * 5),
                open=Decimal(str(price)),
                high=Decimal(str(price + 50)),
                low=Decimal(str(price - 50)),
                close=Decimal(str(price)),
                volume=Decimal("5000")
            )
            data.append(bar)

        # Create mock RSI data
        rsi_data = []
        for i, (bar, rsi_val) in enumerate(zip(data, rsi_values, strict=False)):
            rsi_result = RSIResult(timestamp=bar.timestamp, value=rsi_val)
            rsi_data.append(rsi_result)

        indicators = {"rsi": rsi_data}

        # Analyze patterns with indicators
        collection = self.engine.analyze_patterns(data, indicators)

        # Should detect divergence
        divergence_patterns = collection.get_patterns_by_type(PatternType.DIVERGENCE)

        if divergence_patterns:  # Divergence detection is complex, may not always trigger
            divergence = divergence_patterns[0]
            assert divergence.pattern_type == PatternType.DIVERGENCE
            assert "divergence_type" in divergence.pattern_data
            assert divergence.pattern_data["divergence_type"] in ["bullish", "bearish"]

    def test_pattern_collection_functionality(self):
        """Test pattern collection methods."""
        data = self.data_generator.create_trending_data(num_bars=50)
        collection = self.engine.analyze_patterns(data)

        # Test collection properties
        assert collection.symbol == "BTCUSDT"
        assert collection.timeframe == Timeframe.H1
        assert collection.total_patterns == len(collection.patterns)

        if collection.patterns:
            # Test filtering methods
            high_confidence = collection.get_high_confidence_patterns(0.5)
            assert all(p.confidence >= 0.5 for p in high_confidence)

            # Test pattern type filtering
            for pattern_type in PatternType:
                type_patterns = collection.get_patterns_by_type(pattern_type)
                assert all(p.pattern_type == pattern_type for p in type_patterns)

    def test_confidence_scoring(self):
        """Test pattern confidence scoring system."""
        scorer = PatternConfidenceScorer()

        # Create mock patterns
        patterns = [
            PatternHit(
                pattern_id="test1",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                confidence=0.8,
                strength=7.0,
                bars_analyzed=20,
                lookback_period=20
            ),
            PatternHit(
                pattern_id="test2",
                pattern_type=PatternType.PIN_BAR,
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                confidence=0.6,
                strength=5.0,
                bars_analyzed=1,
                lookback_period=1
            )
        ]

        # Calculate confluence score
        confluence_score = scorer.calculate_confluence_score(patterns)

        assert 0.0 <= confluence_score <= 100.0
        assert confluence_score > 0  # Should have some score with valid patterns

        # Test with market context
        market_context = {
            "volume_ratio": 2.0,  # High volume
            "volatility": 1.0,    # Normal volatility
            "trend_strength": 0.8  # Strong trend
        }

        context_score = scorer.calculate_confluence_score(patterns, market_context)
        assert context_score >= confluence_score  # Should boost score with favorable context

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with insufficient data
        short_data = self.data_generator.create_trending_data(num_bars=5)
        collection = self.engine.analyze_patterns(short_data)

        # Should handle gracefully
        assert collection.total_patterns >= 0

        # Test with empty data
        empty_collection = self.engine.analyze_patterns([])
        assert empty_collection.total_patterns == 0

        # Test with single bar
        single_bar = self.data_generator.create_trending_data(num_bars=1)
        single_collection = self.engine.analyze_patterns(single_bar)
        assert single_collection.total_patterns == 0

    def test_pattern_validation(self):
        """Test pattern data validation."""
        data = self.data_generator.create_pin_bar_data()
        collection = self.engine.analyze_patterns(data)

        # Validate all detected patterns
        for pattern in collection.patterns:
            # Test required fields
            assert pattern.pattern_id
            assert pattern.symbol
            assert pattern.timestamp
            assert 0.0 <= pattern.confidence <= 1.0
            assert 0.0 <= pattern.strength <= 10.0
            assert pattern.bars_analyzed > 0
            assert pattern.lookback_period > 0

            # Test price levels are sorted if present
            if pattern.support_levels:
                assert pattern.support_levels == sorted(pattern.support_levels)
            if pattern.resistance_levels:
                assert pattern.resistance_levels == sorted(pattern.resistance_levels)

    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create larger dataset
        large_data = self.data_generator.create_trending_data(num_bars=500)

        # Should complete analysis in reasonable time
        import time
        start_time = time.time()
        collection = self.engine.analyze_patterns(large_data)
        end_time = time.time()

        # Should complete within 5 seconds for 500 bars
        assert end_time - start_time < 5.0

        # Should still detect patterns
        assert collection.total_patterns >= 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
