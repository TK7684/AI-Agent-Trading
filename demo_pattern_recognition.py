#!/usr/bin/env python3
"""
Demo script for the Pattern Recognition System

This script demonstrates the pattern recognition capabilities including:
- Support/Resistance level detection
- Breakout pattern recognition
- Candlestick pattern detection (Pin Bar, Engulfing, Doji)
- Divergence detection
- Pattern confidence scoring
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np

from libs.trading_models.enums import PatternType, Timeframe
from libs.trading_models.market_data import MarketBar
from libs.trading_models.pattern_recognition import (
    PatternConfidenceScorer,
    PatternRecognitionEngine,
)
from libs.trading_models.technical_indicators import MACDResult, RSIResult


def create_sample_data_with_patterns() -> list[MarketBar]:
    """Create sample market data with various patterns."""
    bars = []
    base_time = datetime.now(UTC) - timedelta(hours=50)
    base_price = 50000.0

    # Create bars with support level touches
    for i in range(40):
        if i % 10 == 0:  # Touch support every 10 bars
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal("50020.00"),
                high=Decimal("50100.00"),
                low=Decimal("49995.00"),  # Touch support at ~50000
                close=Decimal("50050.00"),
                volume=Decimal("5000")
            )
        elif i == 25:  # Create a pin bar
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal("50100.00"),
                high=Decimal("50105.00"),
                low=Decimal("49800.00"),  # Long lower wick
                close=Decimal("50102.00"),  # Small body
                volume=Decimal("7000")
            )
        elif i == 30:  # Create engulfing pattern - small bearish bar
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal("50150.00"),
                high=Decimal("50170.00"),
                low=Decimal("50080.00"),
                close=Decimal("50100.00"),  # Bearish
                volume=Decimal("4000")
            )
        elif i == 31:  # Create engulfing pattern - large bullish bar
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal("50050.00"),  # Below previous close
                high=Decimal("50250.00"),
                low=Decimal("50040.00"),
                close=Decimal("50200.00"),  # Above previous open
                volume=Decimal("8000")
            )
        elif i == 35:  # Create doji
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal("50150.00"),
                high=Decimal("50250.00"),
                low=Decimal("50050.00"),
                close=Decimal("50155.00"),  # Very close to open
                volume=Decimal("6000")
            )
        else:  # Normal bars
            price = base_price + np.random.uniform(100, 300)
            bar = MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=base_time + timedelta(hours=i),
                open=Decimal(str(round(price, 2))),
                high=Decimal(str(round(price + 80, 2))),
                low=Decimal(str(round(price - 80, 2))),
                close=Decimal(str(round(price + np.random.uniform(-40, 40), 2))),
                volume=Decimal("5000")
            )
        bars.append(bar)

    return bars


def create_sample_indicators(data: list[MarketBar]) -> dict:
    """Create sample indicator data for divergence testing."""
    rsi_data = []
    macd_data = []

    # Create RSI values that diverge from price
    base_rsi = 60
    for i, bar in enumerate(data):
        # RSI decreases while price might increase (bearish divergence setup)
        rsi_val = base_rsi - (i * 0.5) + np.random.uniform(-2, 2)
        rsi_val = max(20, min(80, rsi_val))  # Keep within bounds

        rsi_result = RSIResult(timestamp=bar.timestamp, value=rsi_val)
        rsi_data.append(rsi_result)

        # MACD values
        macd_val = np.sin(i * 0.1) * 10 + np.random.uniform(-2, 2)
        macd_result = MACDResult(
            timestamp=bar.timestamp,
            value=macd_val,
            signal=macd_val - 1,
            histogram=1
        )
        macd_data.append(macd_result)

    return {
        "rsi": rsi_data,
        "macd": macd_data
    }


def main():
    """Main demo function."""
    print("🔍 Pattern Recognition System Demo")
    print("=" * 50)

    # Initialize the pattern recognition engine
    engine = PatternRecognitionEngine(min_pattern_confidence=0.3)
    scorer = PatternConfidenceScorer()

    # Create sample data
    print("\n📊 Creating sample market data with embedded patterns...")
    data = create_sample_data_with_patterns()
    indicators = create_sample_indicators(data)

    print(f"   • Generated {len(data)} market bars")
    print(f"   • Time range: {data[0].timestamp} to {data[-1].timestamp}")

    # Analyze patterns
    print("\n🔍 Analyzing patterns...")
    collection = engine.analyze_patterns(data, indicators, Timeframe.H1)

    print(f"   • Total patterns detected: {collection.total_patterns}")
    print(f"   • Average confidence: {collection.avg_confidence:.2f}")
    if collection.strongest_pattern:
        print(f"   • Strongest pattern: {collection.strongest_pattern}")

    # Display patterns by type
    print("\n📈 Pattern Analysis Results:")
    print("-" * 30)

    pattern_types = [
        PatternType.SUPPORT_RESISTANCE,
        PatternType.BREAKOUT,
        PatternType.PIN_BAR,
        PatternType.ENGULFING,
        PatternType.DOJI,
        PatternType.DIVERGENCE
    ]

    for pattern_type in pattern_types:
        patterns = collection.get_patterns_by_type(pattern_type)
        if patterns:
            print(f"\n{pattern_type.value.upper()} PATTERNS ({len(patterns)}):")
            for i, pattern in enumerate(patterns[:3], 1):  # Show top 3
                print(f"  {i}. Confidence: {pattern.confidence:.2f}, "
                      f"Strength: {pattern.strength:.1f}")
                if pattern.pattern_data:
                    key_data = {k: v for k, v in pattern.pattern_data.items()
                              if k in ['pin_type', 'engulfing_type', 'doji_type',
                                     'divergence_type', 'breakout_direction']}
                    if key_data:
                        print(f"     Details: {key_data}")

    # Calculate confluence score
    print("\n🎯 Confluence Analysis:")
    print("-" * 20)

    high_confidence_patterns = collection.get_high_confidence_patterns(0.5)
    if high_confidence_patterns:
        confluence_score = scorer.calculate_confluence_score(high_confidence_patterns)
        print(f"   • High confidence patterns: {len(high_confidence_patterns)}")
        print(f"   • Confluence score: {confluence_score:.1f}/100")

        # Test with market context
        market_context = {
            "volume_ratio": 1.8,  # High volume
            "volatility": 1.2,    # Moderate volatility
            "trend_strength": 0.6  # Moderate trend
        }

        context_score = scorer.calculate_confluence_score(
            high_confidence_patterns, market_context
        )
        print(f"   • Context-adjusted score: {context_score:.1f}/100")
    else:
        print("   • No high confidence patterns found")

    # Performance summary
    print("\n⚡ Performance Summary:")
    print("-" * 20)
    print("   • Pattern detection completed successfully")
    print(f"   • {len([p for p in collection.patterns if p.confidence > 0.6])} high-quality patterns")
    print("   • System ready for live trading analysis")

    print("\n✅ Pattern Recognition Demo Complete!")


if __name__ == "__main__":
    main()
