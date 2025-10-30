#!/usr/bin/env python3
"""
Demo script for confluence scoring and signal generation system.

This script demonstrates the complete confluence scoring workflow including:
- Market regime detection
- Multi-timeframe analysis
- Pattern integration
- LLM analysis integration
- Signal generation with confidence calibration
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np

from libs.trading_models.confluence_scoring import (
    ConfidenceCalibrator,
    ConfluenceScorer,
    ConfluenceWeights,
    MarketRegimeDetector,
    SignalGenerator,
)
from libs.trading_models.enums import PatternType, Timeframe
from libs.trading_models.market_data import MarketBar
from libs.trading_models.patterns import PatternCollection, PatternHit
from libs.trading_models.signals import LLMAnalysis


def create_sample_market_data(symbol: str, timeframe: Timeframe, bars: int = 200, trend: str = "bull") -> list[MarketBar]:
    """Create realistic sample market data with specified trend."""
    data = []
    base_price = 50000.0  # Starting price (e.g., BTC)

    # Trend parameters
    if trend == "bull":
        trend_factor = 0.002  # 0.2% average increase per bar
        volatility = 0.015    # 1.5% volatility
    elif trend == "bear":
        trend_factor = -0.002  # 0.2% average decrease per bar
        volatility = 0.020     # 2% volatility (higher in bear markets)
    else:  # sideways
        trend_factor = 0.0001  # Minimal trend
        volatility = 0.010     # 1% volatility

    current_price = base_price

    for i in range(bars):
        # Add trend and random walk
        price_change = trend_factor + np.random.normal(0, volatility)
        current_price *= (1 + price_change)
        current_price = max(1.0, current_price)  # Ensure positive price

        # Create OHLC with realistic relationships
        open_price = current_price * (1 + np.random.normal(0, 0.002))
        close_price = current_price * (1 + np.random.normal(0, 0.002))

        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))

        # Volume with some correlation to price movement
        base_volume = 1000 + np.random.randint(0, 500)
        price_move = abs(close_price - open_price) / open_price
        volume_multiplier = 1 + price_move * 2  # Higher volume on bigger moves
        volume = base_volume * volume_multiplier

        bar = MarketBar(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now() - timedelta(hours=bars-i),
            open=Decimal(str(round(open_price, 2))),
            high=Decimal(str(round(high_price, 2))),
            low=Decimal(str(round(low_price, 2))),
            close=Decimal(str(round(close_price, 2))),
            volume=Decimal(str(round(volume, 0)))
        )

        data.append(bar)
        current_price = close_price

    return data


def create_sample_patterns(symbol: str, timeframes: list[Timeframe], scenario: str = "bullish") -> dict[Timeframe, PatternCollection]:
    """Create sample pattern collections for different scenarios."""
    patterns = {}

    for tf in timeframes:
        collection = PatternCollection(
            symbol=symbol,
            timeframe=tf,
            timestamp=datetime.now()
        )

        if scenario == "bullish":
            # Strong bullish breakout pattern
            breakout_pattern = PatternHit(
                pattern_id=f"bullish_breakout_{tf.value}",
                pattern_type=PatternType.BREAKOUT,
                symbol=symbol,
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.85,
                strength=8.2,
                bars_analyzed=25,
                lookback_period=25,
                historical_win_rate=0.72,
                entry_price=Decimal("51200"),
                stop_loss=Decimal("49800"),
                take_profit=Decimal("54000")
            )
            collection.add_pattern(breakout_pattern)

            # Support level hold
            support_pattern = PatternHit(
                pattern_id=f"support_hold_{tf.value}",
                pattern_type=PatternType.SUPPORT_RESISTANCE,
                symbol=symbol,
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.78,
                strength=7.5,
                bars_analyzed=30,
                lookback_period=30,
                historical_win_rate=0.68
            )
            collection.add_pattern(support_pattern)

        elif scenario == "bearish":
            # Bearish breakdown pattern
            breakdown_pattern = PatternHit(
                pattern_id=f"bearish_breakdown_{tf.value}",
                pattern_type=PatternType.BREAKOUT,
                symbol=symbol,
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.80,
                strength=7.8,
                bars_analyzed=20,
                lookback_period=20,
                historical_win_rate=0.70,
                entry_price=Decimal("49000"),
                stop_loss=Decimal("50500"),
                take_profit=Decimal("46000")
            )
            collection.add_pattern(breakdown_pattern)

        else:  # mixed/sideways
            # Weak patterns
            weak_pattern = PatternHit(
                pattern_id=f"weak_signal_{tf.value}",
                pattern_type=PatternType.DOJI,
                symbol=symbol,
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.45,
                strength=4.2,
                bars_analyzed=15,
                lookback_period=15,
                historical_win_rate=0.52
            )
            collection.add_pattern(weak_pattern)

        patterns[tf] = collection

    return patterns


def create_sample_llm_analysis(scenario: str = "bullish") -> LLMAnalysis:
    """Create sample LLM analysis for different scenarios."""

    if scenario == "bullish":
        return LLMAnalysis(
            model_id="claude-3-sonnet",
            timestamp=datetime.now(),
            market_sentiment="Strong bullish momentum with technical confirmation",
            key_insights=[
                "Multiple timeframe breakout above key resistance levels",
                "Volume expansion confirms institutional accumulation",
                "RSI showing healthy pullback from overbought levels",
                "EMA alignment supports continued upward momentum"
            ],
            risk_factors=[
                "Approaching major psychological resistance at $55,000",
                "Market volatility elevated due to macro uncertainty",
                "Potential for profit-taking at current levels"
            ],
            bullish_score=8.2,
            bearish_score=2.8,
            confidence=0.87,
            tokens_used=245,
            latency_ms=1350,
            cost_usd=0.0035
        )

    elif scenario == "bearish":
        return LLMAnalysis(
            model_id="gpt-4-turbo",
            timestamp=datetime.now(),
            market_sentiment="Bearish pressure building with technical breakdown",
            key_insights=[
                "Break below critical support suggests further downside",
                "Volume spike on breakdown confirms selling pressure",
                "Multiple bearish divergences across timeframes",
                "Risk-off sentiment affecting broader crypto market"
            ],
            risk_factors=[
                "Potential for oversold bounce at support levels",
                "Central bank policy changes could reverse sentiment",
                "High correlation with traditional risk assets"
            ],
            bullish_score=3.1,
            bearish_score=7.9,
            confidence=0.82,
            tokens_used=198,
            latency_ms=1120,
            cost_usd=0.0028
        )

    else:  # neutral/mixed
        return LLMAnalysis(
            model_id="gemini-pro",
            timestamp=datetime.now(),
            market_sentiment="Mixed signals with no clear directional bias",
            key_insights=[
                "Consolidation pattern suggests indecision",
                "Volume declining indicating lack of conviction",
                "Technical indicators showing conflicting signals"
            ],
            risk_factors=[
                "Low volume environment increases volatility risk",
                "Lack of clear catalyst for directional move",
                "Range-bound trading increases whipsaw risk"
            ],
            bullish_score=5.2,
            bearish_score=4.8,
            confidence=0.65,
            tokens_used=156,
            latency_ms=980,
            cost_usd=0.0021
        )


def demonstrate_market_regime_detection():
    """Demonstrate market regime detection capabilities."""
    print("🔍 Market Regime Detection Demo")
    print("=" * 50)

    detector = MarketRegimeDetector()

    # Test different market scenarios
    scenarios = [
        ("Strong Bull Market", "bull"),
        ("Bear Market", "bear"),
        ("Sideways Market", "sideways")
    ]

    for scenario_name, trend in scenarios:
        print(f"\n📊 {scenario_name}:")

        # Create sample data
        data = create_sample_market_data("BTCUSDT", Timeframe.H1, 100, trend)

        # Create simple indicators (mock)
        indicators = {
            'ema_20': [type('EMA', (), {'value': 50000 + i * (10 if trend == "bull" else -5)})() for i in range(50)],
            'ema_50': [type('EMA', (), {'value': 50000 + i * (8 if trend == "bull" else -3)})() for i in range(50)],
            'ema_200': [type('EMA', (), {'value': 50000 + i * (5 if trend == "bull" else -1)})() for i in range(50)],
            'atr': [type('ATR', (), {'value': 800 + i})() for i in range(50)]
        }

        # Detect regime
        regime_data = detector.detect_regime(data, indicators)

        print(f"  Detected Regime: {regime_data.regime.value.upper()}")
        print(f"  Confidence: {regime_data.confidence:.2f}")
        print(f"  Trend Strength: {regime_data.trend_strength:.2f}")
        print(f"  Volatility Level: {regime_data.volatility_level:.2f}")
        print(f"  EMA Alignment: {regime_data.ema_alignment:.2f}")
        print(f"  Price Momentum: {regime_data.price_momentum:.2f}")


def demonstrate_confluence_scoring():
    """Demonstrate confluence scoring across different scenarios."""
    print("\n\n⚖️ Confluence Scoring Demo")
    print("=" * 50)

    # Create custom weights for demonstration
    custom_weights = ConfluenceWeights(
        trend_weight=0.30,      # Higher weight on trend
        momentum_weight=0.25,   # High weight on momentum
        volatility_weight=0.15,
        volume_weight=0.10,
        pattern_weight=0.15,
        llm_weight=0.05         # Lower weight on LLM for this demo
    )

    scorer = ConfluenceScorer(custom_weights)

    # Test scenarios
    scenarios = [
        ("Strong Bullish Setup", "bull", "bullish"),
        ("Bearish Breakdown", "bear", "bearish"),
        ("Mixed Signals", "sideways", "mixed")
    ]

    for scenario_name, market_trend, pattern_scenario in scenarios:
        print(f"\n📈 {scenario_name}:")

        # Create multi-timeframe data
        timeframes = [Timeframe.M15, Timeframe.H1, Timeframe.H4]
        timeframe_data = {}

        for tf in timeframes:
            data = create_sample_market_data("BTCUSDT", tf, 200, market_trend)
            timeframe_data[tf] = data

        # Create patterns
        patterns = create_sample_patterns("BTCUSDT", timeframes, pattern_scenario)

        # Create LLM analysis
        llm_analysis = create_sample_llm_analysis(pattern_scenario)

        # Calculate confluence score
        confluence_score = scorer.calculate_confluence_score(
            "BTCUSDT",
            timeframe_data,
            patterns,
            llm_analysis
        )

        print(f"  Total Confluence Score: {confluence_score.total_score:.1f}/100")
        print(f"  Direction: {confluence_score.direction.value.upper()}")
        print(f"  Confidence: {confluence_score.confidence:.2f}")
        print(f"  Regime Multiplier: {confluence_score.regime_multiplier:.2f}")

        print("\n  Component Scores:")
        print(f"    Trend: {confluence_score.trend_score:.1f}")
        print(f"    Momentum: {confluence_score.momentum_score:.1f}")
        print(f"    Volatility: {confluence_score.volatility_score:.1f}")
        print(f"    Volume: {confluence_score.volume_score:.1f}")
        print(f"    Pattern: {confluence_score.pattern_score:.1f}")
        print(f"    LLM: {confluence_score.llm_score:.1f}")

        print("\n  Timeframe Weights:")
        for tf, weight in confluence_score.timeframe_weights.items():
            print(f"    {tf.value}: {weight:.2f}")

        print("\n  Key Factors:")
        for factor in confluence_score.key_factors[:3]:
            print(f"    • {factor}")

        if confluence_score.risk_factors:
            print("\n  Risk Factors:")
            for risk in confluence_score.risk_factors[:2]:
                print(f"    ⚠️ {risk}")


def demonstrate_signal_generation():
    """Demonstrate complete signal generation workflow."""
    print("\n\n🎯 Signal Generation Demo")
    print("=" * 50)

    signal_generator = SignalGenerator()

    # Create a strong bullish setup
    print("\n📊 Generating Signal for Strong Bullish Setup:")

    # Multi-timeframe data
    timeframes = [Timeframe.H1, Timeframe.H4, Timeframe.D1]
    timeframe_data = {}

    for tf in timeframes:
        data = create_sample_market_data("BTCUSDT", tf, 200, "bull")
        timeframe_data[tf] = data

    # Strong patterns
    patterns = create_sample_patterns("BTCUSDT", timeframes, "bullish")

    # Bullish LLM analysis
    llm_analysis = create_sample_llm_analysis("bullish")

    # Generate signal
    signal = signal_generator.generate_signal(
        "BTCUSDT",
        timeframe_data,
        patterns,
        llm_analysis
    )

    if signal:
        print("\n✅ Signal Generated Successfully!")
        print(f"  Signal ID: {signal.signal_id}")
        print(f"  Symbol: {signal.symbol}")
        print(f"  Direction: {signal.direction.value.upper()}")
        print(f"  Confluence Score: {signal.confluence_score:.1f}/100")
        print(f"  Confidence: {signal.confidence:.2f}")
        print(f"  Market Regime: {signal.market_regime.value.upper()}")
        print(f"  Primary Timeframe: {signal.primary_timeframe.value}")

        if signal.entry_price:
            print("\n  Price Targets:")
            print(f"    Entry: ${signal.entry_price:,.2f}")
            if signal.stop_loss:
                print(f"    Stop Loss: ${signal.stop_loss:,.2f}")
            if signal.take_profit:
                print(f"    Take Profit: ${signal.take_profit:,.2f}")

            if signal.stop_loss and signal.take_profit:
                risk = abs(float(signal.entry_price - signal.stop_loss))
                reward = abs(float(signal.take_profit - signal.entry_price))
                if risk > 0:
                    rr_ratio = reward / risk
                    print(f"    Risk/Reward: 1:{rr_ratio:.2f}")

        print("\n  Timeframe Analysis:")
        for tf, analysis in signal.timeframe_analysis.items():
            print(f"    {tf.value}: Weight={analysis.timeframe_weight:.2f}, "
                  f"Patterns={analysis.pattern_count}, "
                  f"Confidence={analysis.strongest_pattern_confidence:.2f}")

        print("\n  Signal Reasoning:")
        print(f"    {signal.reasoning}")

        print("\n  Key Supporting Factors:")
        for factor in signal.key_factors[:3]:
            print(f"    • {factor}")

        print(f"\n  Expires: {signal.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

    else:
        print("❌ Signal was filtered (low confidence or insufficient data)")


def demonstrate_confidence_calibration():
    """Demonstrate confidence calibration system."""
    print("\n\n🎯 Confidence Calibration Demo")
    print("=" * 50)

    calibrator = ConfidenceCalibrator()

    print("\n📊 Training Calibrator with Historical Data:")

    # Simulate historical predictions and outcomes
    np.random.seed(42)  # For reproducible results

    for i in range(100):
        # Create realistic confidence-outcome relationship
        raw_confidence = np.random.uniform(0.3, 0.95)

        # Outcomes are correlated with confidence but with some noise
        success_probability = 0.3 + (raw_confidence - 0.3) * 0.8  # Scale to 0.3-0.82
        actual_outcome = np.random.random() < success_probability

        calibrator.add_prediction(raw_confidence, actual_outcome)

        if i % 20 == 19:  # Show progress every 20 predictions
            print(f"  Added {i+1} predictions...")

    print("\n✅ Calibrator trained with 100 historical predictions")

    # Test calibration on different confidence levels
    print("\n📈 Calibration Results:")
    test_confidences = [0.5, 0.6, 0.7, 0.8, 0.9]

    for raw_conf in test_confidences:
        calibrated_conf = calibrator.calibrate_confidence(raw_conf)
        adjustment = calibrated_conf - raw_conf
        direction = "↑" if adjustment > 0 else "↓" if adjustment < 0 else "→"

        print(f"  Raw: {raw_conf:.2f} → Calibrated: {calibrated_conf:.2f} "
              f"({direction} {abs(adjustment):.3f})")


def main():
    """Run all confluence scoring demonstrations."""
    print("🚀 Confluence Scoring and Signal Generation System Demo")
    print("=" * 60)
    print("This demo showcases the complete confluence scoring system including:")
    print("• Market regime detection with multiple indicators")
    print("• Multi-timeframe confluence scoring")
    print("• Pattern recognition integration")
    print("• LLM analysis incorporation")
    print("• Dynamic timeframe weighting")
    print("• Confidence calibration")
    print("• Complete signal generation workflow")

    try:
        # Run all demonstrations
        demonstrate_market_regime_detection()
        demonstrate_confluence_scoring()
        demonstrate_signal_generation()
        demonstrate_confidence_calibration()

        print("\n\n🎉 Demo Complete!")
        print("=" * 60)
        print("The confluence scoring system successfully demonstrated:")
        print("✅ Market regime detection across different market conditions")
        print("✅ Multi-component scoring with weighted confluence calculation")
        print("✅ Dynamic timeframe weighting based on market volatility")
        print("✅ Pattern and LLM analysis integration")
        print("✅ Complete signal generation with price targets")
        print("✅ Confidence calibration using historical performance")
        print("\nThe system is ready for integration with the trading pipeline!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
