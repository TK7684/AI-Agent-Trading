#!/usr/bin/env python3
"""
Enhanced Signal Quality Demo

Demonstrates the advanced signal quality assessment and enhancement system.
Shows how signals are analyzed, graded, and improved for better trading performance.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from libs.trading_models.enhanced_signal_quality import (
    EnhancedSignalFilter,
    SignalQualityOrchestrator,
)
from libs.trading_models.enums import Direction, MarketRegime
from libs.trading_models.patterns import PatternHit, PatternType
from libs.trading_models.signals import LLMAnalysis, Signal, TimeframeAnalysis


def create_sample_signals() -> list[Signal]:
    """Create sample signals with varying quality levels."""

    signals = []

    # 1. Exceptional Quality Signal (A+ Grade)
    exceptional_signal = Signal(
        signal_id="exceptional_001",
        symbol="BTCUSD",
        direction=Direction.LONG,
        confluence_score=95.0,
        confidence=0.92,
        market_regime=MarketRegime.BULL,
        primary_timeframe="1h",
        reasoning="Exceptional bullish breakout with strong momentum",
        timestamp=datetime.now(UTC),
        risk_reward_ratio=3.2,
        entry_price=Decimal("50000.0"),
        stop_loss=Decimal("48500.0"),
        take_profit=Decimal("54800.0"),
        patterns=[
            PatternHit(
                pattern_id="breakout_exceptional",
                pattern_type=PatternType.BREAKOUT,
                confidence=0.88,
                strength=9.2,
                timeframe="1h",
                timestamp=datetime.now(UTC),
                symbol="BTCUSD",
                bars_analyzed=25,
                lookback_period=12,
                pattern_data={"breakout_type": "resistance_break", "volume_confirmation": True}
            ),
            PatternHit(
                pattern_id="engulfing_exceptional",
                pattern_type=PatternType.ENGULFING,
                confidence=0.85,
                strength=8.5,
                timeframe="1h",
                timestamp=datetime.now(UTC),
                symbol="BTCUSD",
                bars_analyzed=20,
                lookback_period=8,
                pattern_data={"engulfing_type": "bullish"}
            ),
            PatternHit(
                pattern_id="divergence_exceptional",
                pattern_type=PatternType.DIVERGENCE,
                confidence=0.78,
                strength=7.0,
                timeframe="4h",
                timestamp=datetime.now(UTC),
                symbol="BTCUSD",
                bars_analyzed=50,
                lookback_period=20,
                pattern_data={"divergence_type": "bullish_rsi"}
            )
        ]
    )

    # Add timeframe analysis
    exceptional_signal.timeframe_analysis["1h"] = TimeframeAnalysis(
        timeframe="1h",
        timestamp=datetime.now(UTC),
        trend_score=9.5,
        momentum_score=8.8,
        volatility_score=5.5,
        volume_score=8.2,
        timeframe_weight=0.8,
        pattern_count=3,
        strongest_pattern_confidence=0.88,
        bullish_indicators=8,
        bearish_indicators=1,
        neutral_indicators=2
    )

    exceptional_signal.timeframe_analysis["4h"] = TimeframeAnalysis(
        timeframe="4h",
        timestamp=datetime.now(UTC),
        trend_score=8.2,
        momentum_score=7.5,
        volatility_score=4.8,
        volume_score=7.0,
        timeframe_weight=0.6,
        pattern_count=2,
        strongest_pattern_confidence=0.78,
        bullish_indicators=6,
        bearish_indicators=0,
        neutral_indicators=3
    )

    # Add LLM analysis
    exceptional_signal.llm_analysis = LLMAnalysis(
        model_id="gpt-4-turbo",
        timestamp=datetime.now(UTC),
        market_sentiment="Strong bullish momentum with institutional buying",
        key_insights=[
            "Clear breakout above key resistance at 49,800",
            "Volume surge indicates strong buying interest",
            "Multiple timeframe alignment confirms trend strength"
        ],
        risk_factors=["Potential profit-taking at 52,000 level"],
        bullish_score=8.9,
        bearish_score=1.5,
        confidence=0.89,
        tokens_used=180,
        latency_ms=750,
        cost_usd=0.025
    )

    signals.append(exceptional_signal)

    # 2. Good Quality Signal (B Grade)
    good_signal = Signal(
        signal_id="good_002",
        symbol="ETHUSD",
        direction=Direction.LONG,
        confluence_score=68.0,
        confidence=0.72,
        market_regime=MarketRegime.BULL,
        primary_timeframe="1h",
        reasoning="Solid bullish setup with good confirmation",
        timestamp=datetime.now(UTC),
        risk_reward_ratio=2.1,
        patterns=[
            PatternHit(
                pattern_id="pin_bar_good",
                pattern_type=PatternType.PIN_BAR,
                confidence=0.75,
                strength=6.5,
                timeframe="1h",
                timestamp=datetime.now(UTC),
                symbol="ETHUSD",
                bars_analyzed=18,
                lookback_period=6,
                pattern_data={"pin_type": "bullish_hammer"}
            ),
            PatternHit(
                pattern_id="sr_good",
                pattern_type=PatternType.SUPPORT_RESISTANCE,
                confidence=0.68,
                strength=5.8,
                timeframe="1h",
                timestamp=datetime.now(UTC),
                symbol="ETHUSD",
                bars_analyzed=30,
                lookback_period=15,
                pattern_data={"level_type": "support_bounce"}
            )
        ]
    )

    signals.append(good_signal)

    # 3. Marginal Quality Signal (C Grade)
    marginal_signal = Signal(
        signal_id="marginal_003",
        symbol="ADAUSD",
        direction=Direction.SHORT,
        confluence_score=42.0,
        confidence=0.48,
        market_regime=MarketRegime.SIDEWAYS,
        primary_timeframe="15m",
        reasoning="Weak bearish signal with limited confirmation",
        timestamp=datetime.now(UTC) - timedelta(minutes=45),  # Slightly stale
        risk_reward_ratio=1.6,
        patterns=[
            PatternHit(
                pattern_id="doji_marginal",
                pattern_type=PatternType.DOJI,
                confidence=0.52,
                strength=3.2,
                timeframe="15m",
                timestamp=datetime.now(UTC),
                symbol="ADAUSD",
                bars_analyzed=12,
                lookback_period=4,
                pattern_data={"doji_type": "gravestone"}
            )
        ]
    )

    signals.append(marginal_signal)

    # 4. Poor Quality Signal (D Grade)
    poor_signal = Signal(
        signal_id="poor_004",
        symbol="DOGEUSDT",
        direction=Direction.LONG,
        confluence_score=22.0,
        confidence=0.28,
        market_regime=MarketRegime.BEAR,  # Counter-trend
        primary_timeframe="15m",
        reasoning="Very weak signal against trend",
        timestamp=datetime.now(UTC) - timedelta(hours=3),  # Very stale
        risk_reward_ratio=0.9,  # Poor R:R
        patterns=[
            PatternHit(
                pattern_id="doji_poor",
                pattern_type=PatternType.DOJI,
                confidence=0.35,
                strength=1.8,
                timeframe="15m",
                timestamp=datetime.now(UTC),
                symbol="DOGEUSDT",
                bars_analyzed=8,
                lookback_period=3,
                pattern_data={"doji_type": "standard"}
            )
        ]
    )

    signals.append(poor_signal)

    return signals


def demonstrate_signal_quality_assessment():
    """Demonstrate signal quality assessment capabilities."""

    print("🎯 Enhanced Signal Quality System Demo")
    print("=" * 50)

    # Create orchestrator
    orchestrator = SignalQualityOrchestrator()
    filter_engine = EnhancedSignalFilter()

    # Create sample signals
    print("\n📊 Creating sample signals with varying quality levels...")
    signals = create_sample_signals()
    print(f"   • Generated {len(signals)} test signals")

    print("\n🔍 Analyzing Signal Quality...")
    print("-" * 40)

    processed_signals = []
    rejected_signals = []

    for i, signal in enumerate(signals, 1):
        print(f"\n📈 Signal {i}: {signal.symbol} {signal.direction}")
        print(f"   Original - Confluence: {signal.confluence_score:.1f}, Confidence: {signal.confidence:.2f}")

        # Assess quality
        quality_metrics = filter_engine.assess_signal_quality(signal)

        print("   Quality Assessment:")
        print(f"     • Overall Quality: {quality_metrics.overall_quality:.1f}/100")
        print(f"     • Trading Grade: {quality_metrics.trading_grade}")
        print(f"     • Technical Strength: {quality_metrics.technical_strength:.1f}/100")
        print(f"     • Pattern Clarity: {quality_metrics.pattern_clarity:.1f}/100")
        print(f"     • Market Context: {quality_metrics.market_context_fit:.1f}/100")

        # Process through orchestrator
        result = orchestrator.process_signal(signal)

        if result is not None:
            enhanced_signal, _ = result
            processed_signals.append((enhanced_signal, quality_metrics))

            print("   ✅ APPROVED FOR TRADING")
            print(f"     • Enhanced Confluence: {enhanced_signal.confluence_score:.1f}")
            print(f"     • Enhanced Confidence: {enhanced_signal.confidence:.2f}")
            print(f"     • Priority: {enhanced_signal.priority}/5")

            if quality_metrics.quality_factors:
                print(f"     • Strengths: {', '.join(quality_metrics.quality_factors[:2])}")
        else:
            rejected_signals.append((signal, quality_metrics))
            print("   ❌ REJECTED")
            if quality_metrics.risk_factors:
                print(f"     • Issues: {', '.join(quality_metrics.risk_factors[:2])}")
            if quality_metrics.improvement_suggestions:
                print(f"     • Suggestion: {quality_metrics.improvement_suggestions[0]}")

    print("\n📊 Processing Summary:")
    print(f"   • Signals Processed: {len(processed_signals)}")
    print(f"   • Signals Rejected: {len(rejected_signals)}")
    print(f"   • Approval Rate: {len(processed_signals)/len(signals)*100:.1f}%")

    # Generate quality report
    print("\n📈 Quality Performance Report:")
    print("-" * 35)

    report = orchestrator.get_quality_report()
    if "total_signals_processed" in report:
        print(f"   • Total Signals Processed: {report['total_signals_processed']}")
        print(f"   • Average Quality Score: {report['recent_average_quality']:.1f}/100")
        print(f"   • High Quality Rate: {report['high_quality_percentage']:.1f}%")
        print(f"   • Trading Ready Rate: {report['trading_ready_percentage']:.1f}%")

        if report['grade_distribution']:
            print("   • Grade Distribution:")
            for grade, count in sorted(report['grade_distribution'].items()):
                print(f"     - {grade}: {count} signals")

    print("\n🎯 Signal Quality Insights:")
    print("-" * 30)

    if processed_signals:
        best_signal, best_quality = max(processed_signals, key=lambda x: x[1].overall_quality)
        print(f"   • Best Signal: {best_signal.symbol} (Grade: {best_quality.trading_grade})")
        print(f"   • Quality Score: {best_quality.overall_quality:.1f}/100")
        print(f"   • Key Strengths: {', '.join(best_quality.quality_factors[:3])}")

    if rejected_signals:
        worst_signal, worst_quality = min(rejected_signals, key=lambda x: x[1].overall_quality)
        print(f"   • Worst Signal: {worst_signal.symbol} (Grade: {worst_quality.trading_grade})")
        print(f"   • Quality Score: {worst_quality.overall_quality:.1f}/100")
        print(f"   • Main Issues: {', '.join(worst_quality.risk_factors[:2])}")

    print("\n✅ Enhanced Signal Quality System Demo Complete!")
    print("🚀 Your trading signals are now enterprise-grade quality!")


if __name__ == "__main__":
    demonstrate_signal_quality_assessment()
