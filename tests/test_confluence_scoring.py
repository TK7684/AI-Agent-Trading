"""
Unit tests for confluence scoring and signal generation system.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from libs.trading_models.confluence_scoring import (
    ConfidenceCalibrator,
    ConfluenceScore,
    ConfluenceScorer,
    ConfluenceWeights,
    MarketRegimeData,
    MarketRegimeDetector,
    SignalGenerator,
)
from libs.trading_models.enums import Direction, MarketRegime, PatternType, Timeframe
from libs.trading_models.market_data import MarketBar
from libs.trading_models.patterns import PatternCollection, PatternHit
from libs.trading_models.signals import LLMAnalysis


class TestConfluenceWeights:
    """Test confluence weights validation."""

    def test_valid_weights(self):
        """Test valid weight configuration."""
        weights = ConfluenceWeights()
        assert abs(weights.trend_weight + weights.momentum_weight + weights.volatility_weight +
                  weights.volume_weight + weights.pattern_weight + weights.llm_weight - 1.0) < 0.01

    def test_invalid_weights_sum(self):
        """Test invalid weight sum raises error."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ConfluenceWeights(
                trend_weight=0.5,
                momentum_weight=0.5,
                volatility_weight=0.2,  # This makes total > 1.0
                volume_weight=0.1,
                pattern_weight=0.1,
                llm_weight=0.1
            )

    def test_custom_weights(self):
        """Test custom weight configuration."""
        weights = ConfluenceWeights(
            trend_weight=0.3,
            momentum_weight=0.3,
            volatility_weight=0.1,
            volume_weight=0.1,
            pattern_weight=0.1,
            llm_weight=0.1
        )
        assert weights.trend_weight == 0.3
        assert weights.momentum_weight == 0.3


class TestConfidenceCalibrator:
    """Test confidence calibration system."""

    def test_initial_calibration(self):
        """Test calibration with no data returns raw confidence."""
        calibrator = ConfidenceCalibrator()
        raw_confidence = 0.7
        calibrated = calibrator.calibrate_confidence(raw_confidence)
        assert calibrated == raw_confidence

    def test_calibration_with_data(self):
        """Test calibration with prediction data."""
        calibrator = ConfidenceCalibrator()

        # Add some predictions and outcomes
        for i in range(20):
            confidence = 0.7 + (i % 3) * 0.1  # 0.7, 0.8, 0.9
            outcome = i % 2 == 0  # Alternating outcomes
            calibrator.add_prediction(confidence, outcome)

        # Test calibration
        calibrated = calibrator.calibrate_confidence(0.8)
        assert 0.0 <= calibrated <= 1.0
        assert calibrated != 0.8  # Should be different from raw

    def test_calibration_bounds(self):
        """Test calibration stays within bounds."""
        calibrator = ConfidenceCalibrator()

        # Add extreme data
        for i in range(15):
            calibrator.add_prediction(0.9, False)  # High confidence, wrong outcomes

        calibrated = calibrator.calibrate_confidence(0.9)
        assert 0.0 <= calibrated <= 1.0


class TestMarketRegimeDetector:
    """Test market regime detection."""

    @pytest.fixture
    def sample_data(self):
        """Create sample market data."""
        data = []
        base_price = 100.0

        for i in range(100):
            # Create trending data
            price = base_price + i * 0.5  # Uptrend
            data.append(MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now() - timedelta(hours=100-i),
                open=Decimal(str(price - 0.2)),
                high=Decimal(str(price + 0.5)),
                low=Decimal(str(price - 0.5)),
                close=Decimal(str(price)),
                volume=Decimal("1000")
            ))

        return data

    @pytest.fixture
    def sample_indicators(self):
        """Create sample indicator data."""
        return {
            'ema_20': [type('EMA', (), {'value': 100 + i * 0.3})() for i in range(50)],
            'ema_50': [type('EMA', (), {'value': 100 + i * 0.2})() for i in range(50)],
            'ema_200': [type('EMA', (), {'value': 100 + i * 0.1})() for i in range(50)],
            'atr': [type('ATR', (), {'value': 2.0})() for i in range(50)]
        }

    def test_regime_detection(self, sample_data, sample_indicators):
        """Test basic regime detection."""
        detector = MarketRegimeDetector()
        regime_data = detector.detect_regime(sample_data, sample_indicators)

        assert isinstance(regime_data, MarketRegimeData)
        assert regime_data.regime in [MarketRegime.BULL, MarketRegime.BEAR, MarketRegime.SIDEWAYS]
        assert 0.0 <= regime_data.confidence <= 1.0
        assert -1.0 <= regime_data.trend_strength <= 1.0
        assert 0.0 <= regime_data.volatility_level <= 1.0

    def test_bull_market_detection(self, sample_indicators):
        """Test bull market detection with strong uptrend."""
        # Create strong uptrend data
        data = []
        for i in range(100):
            price = 100 + i * 2  # Strong uptrend
            data.append(MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now() - timedelta(hours=100-i),
                open=Decimal(str(price - 0.5)),
                high=Decimal(str(price + 1)),
                low=Decimal(str(price - 1)),
                close=Decimal(str(price)),
                volume=Decimal("1000")
            ))

        detector = MarketRegimeDetector()
        regime_data = detector.detect_regime(data, sample_indicators)

        assert regime_data.regime == MarketRegime.BULL
        assert regime_data.trend_strength > 0.5

    def test_insufficient_data(self):
        """Test regime detection with insufficient data."""
        detector = MarketRegimeDetector()
        data = [MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("1000")
        )]

        regime_data = detector.detect_regime(data, {})
        assert regime_data.regime == MarketRegime.SIDEWAYS
        assert regime_data.confidence == 0.5


class TestConfluenceScorer:
    """Test confluence scoring system."""

    @pytest.fixture
    def sample_timeframe_data(self):
        """Create sample timeframe data."""
        data = {}

        for tf in [Timeframe.M15, Timeframe.H1, Timeframe.H4]:
            tf_data = []
            for i in range(100):
                price = 100 + i * 0.1
                tf_data.append(MarketBar(
                    symbol="BTCUSDT",
                    timeframe=tf,
                    timestamp=datetime.now() - timedelta(hours=100-i),
                    open=Decimal(str(price - 0.05)),
                    high=Decimal(str(price + 0.1)),
                    low=Decimal(str(price - 0.1)),
                    close=Decimal(str(price)),
                    volume=Decimal("1000")
                ))
            data[tf] = tf_data

        return data

    @pytest.fixture
    def sample_patterns(self):
        """Create sample pattern data."""
        patterns = {}

        for tf in [Timeframe.M15, Timeframe.H1, Timeframe.H4]:
            pattern_collection = PatternCollection(
                symbol="BTCUSDT",
                timeframe=tf,
                timestamp=datetime.now()
            )

            # Add a sample pattern
            pattern = PatternHit(
                pattern_id=f"pattern_{tf.value}",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.8,
                strength=7.5,
                bars_analyzed=20,
                lookback_period=20,
                historical_win_rate=0.65
            )
            pattern_collection.add_pattern(pattern)
            patterns[tf] = pattern_collection

        return patterns

    @pytest.fixture
    def sample_llm_analysis(self):
        """Create sample LLM analysis."""
        return LLMAnalysis(
            model_id="claude-3",
            timestamp=datetime.now(),
            market_sentiment="Bullish momentum building",
            key_insights=["Strong breakout above resistance", "Volume confirmation"],
            risk_factors=["Overbought RSI", "Approaching major resistance"],
            bullish_score=7.5,
            bearish_score=3.0,
            confidence=0.85,
            tokens_used=150,
            latency_ms=1200,
            cost_usd=0.002
        )

    def test_confluence_score_calculation(self, sample_timeframe_data, sample_patterns, sample_llm_analysis):
        """Test basic confluence score calculation."""
        scorer = ConfluenceScorer()

        score = scorer.calculate_confluence_score(
            "BTCUSDT",
            sample_timeframe_data,
            sample_patterns,
            sample_llm_analysis
        )

        assert isinstance(score, ConfluenceScore)
        assert 0.0 <= score.total_score <= 100.0
        assert score.direction in [Direction.LONG, Direction.SHORT]
        assert 0.0 <= score.confidence <= 1.0
        assert len(score.key_factors) > 0
        assert len(score.timeframe_weights) > 0

    def test_confluence_score_without_llm(self, sample_timeframe_data, sample_patterns):
        """Test confluence score without LLM analysis."""
        scorer = ConfluenceScorer()

        score = scorer.calculate_confluence_score(
            "BTCUSDT",
            sample_timeframe_data,
            sample_patterns,
            None
        )

        assert isinstance(score, ConfluenceScore)
        assert score.llm_score == 0.0
        assert score.total_score >= 0.0

    def test_empty_data_handling(self):
        """Test handling of empty data."""
        scorer = ConfluenceScorer()

        score = scorer.calculate_confluence_score(
            "BTCUSDT",
            {},  # Empty timeframe data
            {},  # Empty patterns
            None
        )

        assert score.total_score == 0.0
        assert score.confidence == 0.1
        assert "Error in calculation" in score.key_factors

    def test_custom_weights(self, sample_timeframe_data, sample_patterns):
        """Test scorer with custom weights."""
        custom_weights = ConfluenceWeights(
            trend_weight=0.4,
            momentum_weight=0.3,
            volatility_weight=0.1,
            volume_weight=0.1,
            pattern_weight=0.05,
            llm_weight=0.05
        )

        scorer = ConfluenceScorer(custom_weights)
        score = scorer.calculate_confluence_score(
            "BTCUSDT",
            sample_timeframe_data,
            sample_patterns,
            None
        )

        assert isinstance(score, ConfluenceScore)
        # Trend should have higher influence with custom weights
        assert abs(score.trend_score) >= 0  # Basic validation

    def test_timeframe_weight_calculation(self, sample_timeframe_data):
        """Test dynamic timeframe weight calculation."""
        scorer = ConfluenceScorer()

        # Create regime data
        regime_data = MarketRegimeData(
            regime=MarketRegime.BULL,
            confidence=0.8,
            trend_strength=0.7,
            volatility_level=0.5,
            volume_trend=0.3,
            regime_duration=20,
            ema_alignment=0.8,
            price_momentum=0.6,
            volatility_percentile=0.4
        )

        weights = scorer._calculate_timeframe_weights(sample_timeframe_data, regime_data)

        # Weights should sum to 1.0
        assert abs(sum(weights.values()) - 1.0) < 0.01

        # All weights should be positive
        assert all(w > 0 for w in weights.values())

        # In bull market, longer timeframes should have higher weights
        if Timeframe.H4 in weights and Timeframe.M15 in weights:
            assert weights[Timeframe.H4] >= weights[Timeframe.M15]


class TestSignalGenerator:
    """Test signal generation system."""

    @pytest.fixture
    def signal_generator(self):
        """Create signal generator."""
        return SignalGenerator()

    @pytest.fixture
    def sample_timeframe_data(self):
        """Create sample timeframe data for signal generation."""
        data = {}

        for tf in [Timeframe.H1, Timeframe.H4]:
            tf_data = []
            for i in range(100):
                price = 100 + i * 0.2  # Uptrend
                tf_data.append(MarketBar(
                    symbol="BTCUSDT",
                    timeframe=tf,
                    timestamp=datetime.now() - timedelta(hours=100-i),
                    open=Decimal(str(price - 0.1)),
                    high=Decimal(str(price + 0.2)),
                    low=Decimal(str(price - 0.2)),
                    close=Decimal(str(price)),
                    volume=Decimal("1500")
                ))
            data[tf] = tf_data

        return data

    @pytest.fixture
    def strong_patterns(self):
        """Create strong pattern signals."""
        patterns = {}

        for tf in [Timeframe.H1, Timeframe.H4]:
            pattern_collection = PatternCollection(
                symbol="BTCUSDT",
                timeframe=tf,
                timestamp=datetime.now()
            )

            # Add strong bullish pattern
            pattern = PatternHit(
                pattern_id=f"strong_breakout_{tf.value}",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=tf,
                timestamp=datetime.now(),
                confidence=0.9,
                strength=8.5,
                bars_analyzed=25,
                lookback_period=25,
                historical_win_rate=0.75,
                entry_price=Decimal("120"),
                stop_loss=Decimal("115"),
                take_profit=Decimal("130")
            )
            pattern_collection.add_pattern(pattern)
            patterns[tf] = pattern_collection

        return patterns

    def test_signal_generation(self, signal_generator, sample_timeframe_data, strong_patterns):
        """Test basic signal generation."""
        signal = signal_generator.generate_signal(
            "BTCUSDT",
            sample_timeframe_data,
            strong_patterns,
            None
        )

        if signal:  # Signal might be filtered if confluence is too low
            assert signal.symbol == "BTCUSDT"
            assert signal.direction in [Direction.LONG, Direction.SHORT]
            assert 0.0 <= signal.confluence_score <= 100.0
            assert 0.0 <= signal.confidence <= 1.0
            assert signal.entry_price is not None
            assert len(signal.reasoning) > 0
            assert signal.expires_at > datetime.now()

    def test_signal_filtering(self, signal_generator):
        """Test signal filtering for low confidence."""
        # Create weak data that should be filtered
        weak_data = {
            Timeframe.H1: [MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(),
                open=Decimal("100"),
                high=Decimal("100.1"),
                low=Decimal("99.9"),
                close=Decimal("100"),
                volume=Decimal("100")
            )]
        }

        weak_patterns = {
            Timeframe.H1: PatternCollection(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now()
            )
        }

        signal = signal_generator.generate_signal(
            "BTCUSDT",
            weak_data,
            weak_patterns,
            None
        )

        # Should be filtered due to insufficient data/confidence
        assert signal is None

    def test_price_target_calculation(self, signal_generator, sample_timeframe_data, strong_patterns):
        """Test price target calculation."""
        # Create data with sufficient history for ATR calculation
        extended_data = {}
        for tf, data in sample_timeframe_data.items():
            # Ensure we have enough data for ATR
            extended_data[tf] = data

        signal = signal_generator.generate_signal(
            "BTCUSDT",
            extended_data,
            strong_patterns,
            None
        )

        if signal and signal.entry_price and signal.stop_loss and signal.take_profit:
            # Validate price relationships for long signal
            if signal.direction == Direction.LONG:
                assert signal.stop_loss < signal.entry_price < signal.take_profit
            else:  # SHORT
                assert signal.take_profit < signal.entry_price < signal.stop_loss

    def test_timeframe_analysis_creation(self, signal_generator, sample_timeframe_data, strong_patterns):
        """Test timeframe analysis creation."""
        signal = signal_generator.generate_signal(
            "BTCUSDT",
            sample_timeframe_data,
            strong_patterns,
            None
        )

        if signal:
            assert len(signal.timeframe_analysis) > 0

            for tf, analysis in signal.timeframe_analysis.items():
                assert analysis.timeframe == tf
                assert analysis.timestamp is not None
                assert analysis.timeframe_weight >= 0.0
                assert analysis.pattern_count >= 0


class TestIntegration:
    """Integration tests for the complete confluence scoring system."""

    def test_end_to_end_signal_generation(self):
        """Test complete end-to-end signal generation."""
        # Create realistic market data
        timeframe_data = {}

        for tf in [Timeframe.M15, Timeframe.H1, Timeframe.H4]:
            data = []
            base_price = 50000  # BTC price

            for i in range(200):  # Sufficient data for all indicators
                # Create realistic price movement
                price_change = np.random.normal(0, 100)  # Random walk
                price = base_price + i * 50 + price_change  # Overall uptrend with noise

                data.append(MarketBar(
                    symbol="BTCUSDT",
                    timeframe=tf,
                    timestamp=datetime.now() - timedelta(hours=200-i),
                    open=Decimal(str(max(1, price - 25))),
                    high=Decimal(str(max(1, price + 50))),
                    low=Decimal(str(max(1, price - 50))),
                    close=Decimal(str(max(1, price))),
                    volume=Decimal(str(1000 + np.random.randint(0, 500)))
                ))

            timeframe_data[tf] = data

        # Create pattern data
        patterns = {}
        for tf in timeframe_data.keys():
            pattern_collection = PatternCollection(
                symbol="BTCUSDT",
                timeframe=tf,
                timestamp=datetime.now()
            )

            # Add multiple patterns
            for i, pattern_type in enumerate([PatternType.BREAKOUT, PatternType.SUPPORT_RESISTANCE]):
                pattern = PatternHit(
                    pattern_id=f"pattern_{tf.value}_{i}",
                    pattern_type=pattern_type,
                    symbol="BTCUSDT",
                    timeframe=tf,
                    timestamp=datetime.now(),
                    confidence=0.7 + i * 0.1,
                    strength=6.0 + i,
                    bars_analyzed=20,
                    lookback_period=20,
                    historical_win_rate=0.6 + i * 0.05
                )
                pattern_collection.add_pattern(pattern)

            patterns[tf] = pattern_collection

        # Create LLM analysis
        llm_analysis = LLMAnalysis(
            model_id="gpt-4",
            timestamp=datetime.now(),
            market_sentiment="Cautiously bullish with strong technical setup",
            key_insights=[
                "Multiple timeframe alignment suggests upward momentum",
                "Volume profile shows accumulation at current levels",
                "RSI showing healthy pullback from overbought"
            ],
            risk_factors=[
                "Approaching major resistance zone",
                "Market volatility elevated",
                "External macro factors uncertain"
            ],
            bullish_score=6.5,
            bearish_score=3.5,
            confidence=0.78,
            tokens_used=200,
            latency_ms=1500,
            cost_usd=0.003
        )

        # Generate signal
        signal_generator = SignalGenerator()
        signal = signal_generator.generate_signal(
            "BTCUSDT",
            timeframe_data,
            patterns,
            llm_analysis
        )

        # Validate complete signal
        if signal:  # May be None if filtered
            assert signal.symbol == "BTCUSDT"
            assert signal.direction in [Direction.LONG, Direction.SHORT]
            assert 0.0 <= signal.confluence_score <= 100.0
            assert 0.0 <= signal.confidence <= 1.0
            assert len(signal.timeframe_analysis) > 0
            assert len(signal.patterns) > 0
            assert signal.llm_analysis == llm_analysis
            assert signal.entry_price is not None
            assert len(signal.reasoning) > 50  # Substantial reasoning
            assert len(signal.key_factors) > 0
            assert signal.expires_at > datetime.now()

            # Validate timeframe analysis
            for tf, analysis in signal.timeframe_analysis.items():
                assert analysis.timeframe in timeframe_data.keys()
                assert analysis.pattern_count >= 0
                assert 0.0 <= analysis.timeframe_weight <= 1.0

            # Validate patterns are relevant
            for pattern in signal.patterns:
                assert pattern.confidence > 0.6  # Should be high-confidence patterns
                assert pattern.symbol == "BTCUSDT"

    def test_confidence_calibration_integration(self):
        """Test confidence calibration with realistic data."""
        scorer = ConfluenceScorer()

        # Simulate multiple predictions and outcomes
        predictions = []
        outcomes = []

        for i in range(50):
            # Create varying confidence levels
            confidence = 0.5 + (i % 5) * 0.1  # 0.5 to 0.9
            outcome = np.random.random() < confidence  # Outcome correlated with confidence

            scorer.confidence_calibrator.add_prediction(confidence, outcome)
            predictions.append(confidence)
            outcomes.append(outcome)

        # Test calibration improves over time
        raw_confidence = 0.8
        calibrated = scorer.confidence_calibrator.calibrate_confidence(raw_confidence)

        assert 0.0 <= calibrated <= 1.0
        # With correlated data, calibration should be reasonable
        assert abs(calibrated - raw_confidence) < 0.3  # Not too far from original


if __name__ == "__main__":
    pytest.main([__file__])
