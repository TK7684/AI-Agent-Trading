"""Unit tests for trading models."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from libs.trading_models import (
    Direction,
    ExecutionResult,
    IndicatorSnapshot,
    LLMAnalysis,
    MarketBar,
    MarketRegime,
    OrderDecision,
    OrderStatus,
    OrderType,
    PatternCollection,
    PatternHit,
    PatternType,
    Signal,
    Timeframe,
    TimeframeAnalysis,
)


class TestMarketBar:
    """Test MarketBar model."""

    def test_valid_market_bar(self):
        """Test creating a valid market bar."""
        bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49500.00"),
            close=Decimal("50500.00"),
            volume=Decimal("100.5"),
        )

        assert bar.symbol == "BTCUSDT"
        assert bar.timeframe == Timeframe.H1
        assert bar.open == Decimal("50000.00")
        assert bar.high == Decimal("51000.00")
        assert bar.low == Decimal("49500.00")
        assert bar.close == Decimal("50500.00")
        assert bar.volume == Decimal("100.5")

    def test_invalid_high_price(self):
        """Test validation of high price."""
        with pytest.raises(ValueError, match="High must be the highest price"):
            MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                open=Decimal("50000.00"),
                high=Decimal("49000.00"),  # High is lower than open
                low=Decimal("49500.00"),
                close=Decimal("50500.00"),
                volume=Decimal("100.5"),
            )

    def test_invalid_low_price(self):
        """Test validation of low price."""
        with pytest.raises(ValueError, match="Low must be the lowest price"):
            MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("50500.00"),  # Low is higher than open
                close=Decimal("50500.00"),
                volume=Decimal("100.5"),
            )

    def test_negative_price(self):
        """Test validation of negative prices."""
        with pytest.raises(ValueError):
            MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                open=Decimal("-50000.00"),  # Negative price
                high=Decimal("51000.00"),
                low=Decimal("49500.00"),
                close=Decimal("50500.00"),
                volume=Decimal("100.5"),
            )

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49500.00"),
            close=Decimal("50500.00"),
            volume=Decimal("100.5"),
        )

        # Serialize to JSON
        json_str = bar.to_json()

        # Deserialize from JSON
        bar_restored = MarketBar.from_json(json_str)

        assert bar_restored.symbol == bar.symbol
        assert bar_restored.timeframe == bar.timeframe
        assert bar_restored.open == bar.open
        assert bar_restored.high == bar.high
        assert bar_restored.low == bar.low
        assert bar_restored.close == bar.close
        assert bar_restored.volume == bar.volume


class TestIndicatorSnapshot:
    """Test IndicatorSnapshot model."""

    def test_valid_indicator_snapshot(self):
        """Test creating a valid indicator snapshot."""
        snapshot = IndicatorSnapshot(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            rsi=65.5,
            ema_20=Decimal("50000.00"),
            macd_line=150.5,
            bb_upper=Decimal("52000.00"),
            bb_middle=Decimal("50000.00"),
            bb_lower=Decimal("48000.00"),
            atr=Decimal("500.00"),
        )

        assert snapshot.symbol == "BTCUSDT"
        assert snapshot.rsi == 65.5
        assert snapshot.ema_20 == Decimal("50000.00")

    def test_invalid_rsi_range(self):
        """Test RSI validation."""
        with pytest.raises(ValueError):
            IndicatorSnapshot(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                rsi=150.0,  # RSI > 100
            )

    def test_invalid_bollinger_bands(self):
        """Test Bollinger Bands validation."""
        with pytest.raises(ValueError, match="Upper band must be greater than middle band"):
            IndicatorSnapshot(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                bb_upper=Decimal("48000.00"),  # Upper < Middle
                bb_middle=Decimal("50000.00"),
                bb_lower=Decimal("47000.00"),
            )


class TestPatternHit:
    """Test PatternHit model."""

    def test_valid_pattern_hit(self):
        """Test creating a valid pattern hit."""
        pattern = PatternHit(
            pattern_id="pattern_123",
            pattern_type=PatternType.BREAKOUT,
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            confidence=0.85,
            strength=7.5,
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            support_levels=[Decimal("48000.00"), Decimal("49000.00")],
            resistance_levels=[Decimal("51000.00"), Decimal("52000.00")],
            bars_analyzed=100,
            lookback_period=50,
        )

        assert pattern.pattern_id == "pattern_123"
        assert pattern.pattern_type == PatternType.BREAKOUT
        assert pattern.confidence == 0.85
        assert pattern.strength == 7.5

    def test_invalid_confidence_range(self):
        """Test confidence validation."""
        with pytest.raises(ValueError):
            PatternHit(
                pattern_id="pattern_123",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                confidence=1.5,  # Confidence > 1
                strength=7.5,
                bars_analyzed=100,
                lookback_period=50,
            )

    def test_unsorted_support_levels(self):
        """Test support levels sorting validation."""
        with pytest.raises(ValueError, match="Price levels must be sorted"):
            PatternHit(
                pattern_id="pattern_123",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                confidence=0.85,
                strength=7.5,
                support_levels=[Decimal("49000.00"), Decimal("48000.00")],  # Unsorted
                bars_analyzed=100,
                lookback_period=50,
            )


class TestSignal:
    """Test Signal model."""

    def test_valid_signal(self):
        """Test creating a valid signal."""
        signal = Signal(
            signal_id="signal_123",
            symbol="BTCUSDT",
            timestamp=datetime.now(UTC),
            direction=Direction.LONG,
            confluence_score=75.5,
            confidence=0.8,
            market_regime=MarketRegime.BULL,
            primary_timeframe=Timeframe.H1,
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_reward_ratio=2.0,
            reasoning="Strong bullish breakout pattern",
        )

        assert signal.signal_id == "signal_123"
        assert signal.direction == Direction.LONG
        assert signal.confluence_score == 75.5
        assert signal.confidence == 0.8

    def test_high_confluence_low_confidence(self):
        """Test validation of high confluence with low confidence."""
        with pytest.raises(ValueError, match="High confluence score requires high confidence"):
            Signal(
                signal_id="signal_123",
                symbol="BTCUSDT",
                timestamp=datetime.now(UTC),
                direction=Direction.LONG,
                confluence_score=95.0,  # High confluence
                confidence=0.5,  # Low confidence
                market_regime=MarketRegime.BULL,
                primary_timeframe=Timeframe.H1,
                reasoning="Test signal",
            )

    def test_risk_reward_calculation(self):
        """Test risk/reward ratio validation."""
        with pytest.raises(ValueError, match="Risk/reward ratio doesn't match price levels"):
            Signal(
                signal_id="signal_123",
                symbol="BTCUSDT",
                timestamp=datetime.now(UTC),
                direction=Direction.LONG,
                confluence_score=75.5,
                confidence=0.8,
                market_regime=MarketRegime.BULL,
                primary_timeframe=Timeframe.H1,
                entry_price=Decimal("50000.00"),
                stop_loss=Decimal("49000.00"),  # Risk = 1000
                take_profit=Decimal("52000.00"),  # Reward = 2000, RR = 2.0
                risk_reward_ratio=3.0,  # Incorrect RR
                reasoning="Test signal",
            )


class TestOrderDecision:
    """Test OrderDecision model."""

    def test_valid_order_decision(self):
        """Test creating a valid order decision."""
        decision = OrderDecision(
            signal_id="signal_123",
            symbol="BTCUSDT",
            direction=Direction.LONG,
            order_type=OrderType.MARKET,
            base_quantity=Decimal("1.0"),
            risk_adjusted_quantity=Decimal("0.8"),
            max_position_value=Decimal("40000.00"),
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            risk_amount=Decimal("800.00"),
            risk_percentage=2.0,
            leverage=1.0,
            portfolio_value=Decimal("100000.00"),
            available_margin=Decimal("50000.00"),
            current_exposure=0.1,
            confidence_score=0.8,
            confluence_score=75.0,
            risk_reward_ratio=2.0,
            decision_reason="Strong bullish signal",
            timeframe_context=Timeframe.H1,
        )

        assert decision.signal_id == "signal_123"
        assert decision.direction == Direction.LONG
        assert decision.risk_percentage == 2.0

    def test_excessive_risk_percentage(self):
        """Test risk percentage validation."""
        # Test field constraint validation (risk_percentage > 10)
        with pytest.raises(ValueError, match="Input should be less than or equal to 10"):
            OrderDecision(
                signal_id="signal_123",
                symbol="BTCUSDT",
                direction=Direction.LONG,
                order_type=OrderType.MARKET,
                base_quantity=Decimal("1.0"),
                risk_adjusted_quantity=Decimal("0.8"),
                max_position_value=Decimal("40000.00"),
                entry_price=Decimal("50000.00"),
                stop_loss=Decimal("49000.00"),
                risk_amount=Decimal("800.00"),
                risk_percentage=15.0,  # High risk > 10%
                leverage=1.0,
                portfolio_value=Decimal("100000.00"),
                available_margin=Decimal("50000.00"),
                current_exposure=0.1,
                confidence_score=0.8,
                confluence_score=75.0,
                risk_reward_ratio=2.0,
                decision_reason="Test",
                timeframe_context=Timeframe.H1,
            )

        # Test custom validation for total portfolio risk
        with pytest.raises(ValueError, match="Total portfolio risk would exceed 20%"):
            OrderDecision(
                signal_id="signal_123",
                symbol="BTCUSDT",
                direction=Direction.LONG,
                order_type=OrderType.MARKET,
                base_quantity=Decimal("1.0"),
                risk_adjusted_quantity=Decimal("0.8"),
                max_position_value=Decimal("40000.00"),
                entry_price=Decimal("50000.00"),
                stop_loss=Decimal("49000.00"),
                risk_amount=Decimal("800.00"),
                risk_percentage=4.0,  # Within leverage limit but total > 20%
                leverage=1.0,
                portfolio_value=Decimal("100000.00"),
                available_margin=Decimal("50000.00"),
                current_exposure=0.17,  # 17% existing + 4% = 21% > 20%
                confidence_score=0.8,
                confluence_score=75.0,
                risk_reward_ratio=2.0,
                decision_reason="Test",
                timeframe_context=Timeframe.H1,
            )

    def test_invalid_stop_loss_long(self):
        """Test stop loss validation for long positions."""
        with pytest.raises(ValueError, match="Stop loss must be below entry price for long positions"):
            OrderDecision(
                signal_id="signal_123",
                symbol="BTCUSDT",
                direction=Direction.LONG,
                order_type=OrderType.MARKET,
                base_quantity=Decimal("1.0"),
                risk_adjusted_quantity=Decimal("0.8"),
                max_position_value=Decimal("40000.00"),
                entry_price=Decimal("50000.00"),
                stop_loss=Decimal("51000.00"),  # Stop above entry for long
                risk_amount=Decimal("800.00"),
                risk_percentage=2.0,
                leverage=1.0,
                portfolio_value=Decimal("100000.00"),
                available_margin=Decimal("50000.00"),
                current_exposure=0.1,
                confidence_score=0.8,
                confluence_score=75.0,
                risk_reward_ratio=2.0,
                decision_reason="Test",
                timeframe_context=Timeframe.H1,
            )


class TestPatternCollection:
    """Test PatternCollection model."""

    def test_pattern_collection_operations(self):
        """Test pattern collection operations."""
        collection = PatternCollection(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
        )

        # Add a pattern
        pattern = PatternHit(
            pattern_id="pattern_123",
            pattern_type=PatternType.BREAKOUT,
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            confidence=0.85,
            strength=7.5,
            bars_analyzed=100,
            lookback_period=50,
        )

        collection.add_pattern(pattern)

        assert collection.total_patterns == 1
        assert collection.avg_confidence == 0.85
        assert collection.strongest_pattern == "pattern_123"

        # Test filtering
        breakout_patterns = collection.get_patterns_by_type(PatternType.BREAKOUT)
        assert len(breakout_patterns) == 1

        high_conf_patterns = collection.get_high_confidence_patterns(0.8)
        assert len(high_conf_patterns) == 1


class TestSerializationCompatibility:
    """Test Python-Rust serialization compatibility."""

    def test_market_bar_json_compatibility(self):
        """Test MarketBar JSON format matches Rust expectations."""
        bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49500.00"),
            close=Decimal("50500.00"),
            volume=Decimal("100.5"),
        )

        json_data = json.loads(bar.to_json())

        # Check required fields are present
        assert "symbol" in json_data
        assert "timeframe" in json_data
        assert "timestamp" in json_data
        assert "open" in json_data
        assert "high" in json_data
        assert "low" in json_data
        assert "close" in json_data
        assert "volume" in json_data

        # Check timeframe format
        assert json_data["timeframe"] == "1h"

    def test_signal_json_compatibility(self):
        """Test Signal JSON format matches Rust expectations."""
        signal = Signal(
            signal_id="signal_123",
            symbol="BTCUSDT",
            timestamp=datetime.now(UTC),
            direction=Direction.LONG,
            confluence_score=75.5,
            confidence=0.8,
            market_regime=MarketRegime.BULL,
            primary_timeframe=Timeframe.H1,
            reasoning="Test signal",
        )

        json_data = json.loads(signal.to_json())

        # Check enum serialization
        assert json_data["direction"] == "long"
        assert json_data["market_regime"] == "bull"
        assert json_data["primary_timeframe"] == "1h"


class TestDataValidation:
    """Test comprehensive data validation."""

    def test_invalid_data_rejection(self):
        """Test that invalid data is properly rejected."""
        # Test various invalid scenarios
        invalid_cases = [
            # Negative prices
            lambda: MarketBar(
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                open=Decimal("-1.0"),
                high=Decimal("1.0"),
                low=Decimal("0.5"),
                close=Decimal("0.8"),
                volume=Decimal("100.0"),
            ),
            # Invalid confidence
            lambda: PatternHit(
                pattern_id="test",
                pattern_type=PatternType.BREAKOUT,
                symbol="BTCUSDT",
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                confidence=2.0,  # > 1
                strength=5.0,
                bars_analyzed=100,
                lookback_period=50,
            ),
            # Invalid confluence score
            lambda: Signal(
                signal_id="test",
                symbol="BTCUSDT",
                timestamp=datetime.now(UTC),
                direction=Direction.LONG,
                confluence_score=150.0,  # > 100
                confidence=0.8,
                market_regime=MarketRegime.BULL,
                primary_timeframe=Timeframe.H1,
                reasoning="Test",
            ),
        ]

        for invalid_case in invalid_cases:
            with pytest.raises(ValueError):
                invalid_case()

    def test_edge_case_values(self):
        """Test edge case values are handled correctly."""
        # Test minimum valid values
        bar = MarketBar(
            symbol="A",
            timeframe=Timeframe.M15,
            timestamp=datetime.now(UTC),
            open=Decimal("0.01"),
            high=Decimal("0.01"),
            low=Decimal("0.01"),
            close=Decimal("0.01"),
            volume=Decimal("0.0"),
        )
        assert bar.open == Decimal("0.01")

        # Test maximum valid confidence
        pattern = PatternHit(
            pattern_id="test",
            pattern_type=PatternType.BREAKOUT,
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            confidence=1.0,  # Maximum
            strength=10.0,  # Maximum
            bars_analyzed=1,  # Minimum
            lookback_period=1,  # Minimum
        )
        assert pattern.confidence == 1.0
        assert pattern.strength == 10.0


class TestModelMethods:
    """Test model utility methods."""

    def test_base_model_methods(self):
        """Test BaseModel utility methods."""
        bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49500.00"),
            close=Decimal("50500.00"),
            volume=Decimal("100.5"),
        )

        # Test to_dict
        data_dict = bar.to_dict()
        assert isinstance(data_dict, dict)
        assert data_dict["symbol"] == "BTCUSDT"

        # Test from_dict
        bar_from_dict = MarketBar.from_dict(data_dict)
        assert bar_from_dict.symbol == bar.symbol
        assert bar_from_dict.open == bar.open

        # Test to_json
        json_str = bar.to_json()
        assert isinstance(json_str, str)

        # Test from_json
        bar_from_json = MarketBar.from_json(json_str)
        assert bar_from_json.symbol == bar.symbol
        assert bar_from_json.open == bar.open

        # Test __str__
        str_repr = str(bar)
        assert "MarketBar" in str_repr

    def test_order_decision_calculations(self):
        """Test OrderDecision calculation methods."""
        decision = OrderDecision(
            signal_id="signal_123",
            symbol="BTCUSDT",
            direction=Direction.LONG,
            order_type=OrderType.MARKET,
            base_quantity=Decimal("1.0"),
            risk_adjusted_quantity=Decimal("0.8"),
            max_position_value=Decimal("40000.00"),
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            risk_amount=Decimal("800.00"),
            risk_percentage=2.0,
            leverage=2.0,
            portfolio_value=Decimal("100000.00"),
            available_margin=Decimal("50000.00"),
            current_exposure=0.1,
            confidence_score=0.8,
            confluence_score=75.0,
            risk_reward_ratio=2.0,
            decision_reason="Test calculation methods",
            timeframe_context=Timeframe.H1,
        )

        # Test position value calculation
        position_value = decision.calculate_position_value()
        expected_value = Decimal("0.8") * Decimal("50000.00") * Decimal("2.0")
        assert position_value == expected_value

        # Test margin calculation
        margin_required = decision.calculate_margin_required()
        expected_margin = expected_value / Decimal("2.0")
        assert margin_required == expected_margin

        # Test margin validation
        assert decision.validate_margin_requirements() == True

        # Test risk metrics
        risk_metrics = decision.get_risk_metrics()
        assert "position_size_pct" in risk_metrics
        assert "risk_amount" in risk_metrics
        assert "leverage" in risk_metrics
        assert risk_metrics["leverage"] == 2.0

    def test_signal_weighted_confluence(self):
        """Test Signal weighted confluence calculation."""
        signal = Signal(
            signal_id="signal_123",
            symbol="BTCUSDT",
            timestamp=datetime.now(UTC),
            direction=Direction.LONG,
            confluence_score=75.0,
            confidence=0.8,
            market_regime=MarketRegime.BULL,
            primary_timeframe=Timeframe.H1,
            reasoning="Test weighted confluence",
        )

        # Test without timeframe analysis
        weighted_score = signal.get_weighted_confluence()
        assert weighted_score == 75.0

        # Add timeframe analyses
        tf_analysis_1 = TimeframeAnalysis(
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            trend_score=5.0,
            momentum_score=3.0,
            volatility_score=2.0,
            volume_score=4.0,
            timeframe_weight=0.6,
        )

        tf_analysis_2 = TimeframeAnalysis(
            timeframe=Timeframe.H4,
            timestamp=datetime.now(UTC),
            trend_score=2.0,
            momentum_score=4.0,
            volatility_score=3.0,
            volume_score=3.0,
            timeframe_weight=0.4,
        )

        signal.add_timeframe_analysis(tf_analysis_1)
        signal.add_timeframe_analysis(tf_analysis_2)

        # Test weighted confluence calculation
        weighted_score = signal.get_weighted_confluence()
        # Expected: ((5+3)*0.6 + (2+4)*0.4) / (0.6+0.4) = (4.8 + 2.4) / 1.0 = 7.2
        # Normalized: (7.2 + 10) * 5 = 86.0
        assert abs(weighted_score - 86.0) < 0.1

    def test_execution_result_methods(self):
        """Test ExecutionResult utility methods."""
        result = ExecutionResult(
            decision_id="decision_123",
            order_id="order_456",
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.8"),
            average_price=Decimal("50100.00"),
            submitted_at=datetime.now(UTC),
            filled_at=datetime.now(UTC),
            commission=Decimal("5.0"),
        )

        # Test status checks
        assert result.is_fully_filled() == True
        assert result.is_partially_filled() == False

        # Test fill percentage
        fill_pct = result.get_fill_percentage(Decimal("1.0"))
        assert fill_pct == 80.0

        # Test partial fill
        result.status = OrderStatus.PARTIALLY_FILLED
        assert result.is_fully_filled() == False
        assert result.is_partially_filled() == True


class TestAdvancedValidation:
    """Test advanced validation scenarios."""

    def test_cross_field_validation(self):
        """Test validation that depends on multiple fields."""
        # Test risk/reward ratio validation in Signal
        with pytest.raises(ValueError, match="Risk/reward ratio doesn't match price levels"):
            Signal(
                signal_id="test",
                symbol="BTCUSDT",
                timestamp=datetime.now(UTC),
                direction=Direction.LONG,
                confluence_score=75.0,
                confidence=0.8,
                market_regime=MarketRegime.BULL,
                primary_timeframe=Timeframe.H1,
                entry_price=Decimal("50000.00"),
                stop_loss=Decimal("49000.00"),  # Risk = 1000
                take_profit=Decimal("52000.00"),  # Reward = 2000, RR should be 2.0
                risk_reward_ratio=3.0,  # But we claim 3.0
                reasoning="Test cross-field validation",
            )

    def test_timeframe_analysis_validation(self):
        """Test TimeframeAnalysis validation."""
        # Valid analysis
        analysis = TimeframeAnalysis(
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            trend_score=5.0,
            momentum_score=-3.0,
            volatility_score=2.0,
            volume_score=4.0,
            timeframe_weight=0.6,
        )
        assert analysis.trend_score == 5.0

        # Invalid trend score
        with pytest.raises(ValueError):
            TimeframeAnalysis(
                timeframe=Timeframe.H1,
                timestamp=datetime.now(UTC),
                trend_score=15.0,  # > 10
                momentum_score=3.0,
                volatility_score=2.0,
                volume_score=4.0,
                timeframe_weight=0.6,
            )

    def test_llm_analysis_validation(self):
        """Test LLMAnalysis validation."""
        # Valid analysis
        analysis = LLMAnalysis(
            model_id="gpt-4",
            timestamp=datetime.now(UTC),
            market_sentiment="Bullish momentum building",
            key_insights=["Strong breakout pattern", "High volume confirmation"],
            risk_factors=["Potential resistance at 52k"],
            bullish_score=7.5,
            bearish_score=2.5,
            confidence=0.85,
            tokens_used=150,
            latency_ms=2500,
            cost_usd=0.003,
        )
        assert analysis.bullish_score == 7.5

        # Invalid confidence
        with pytest.raises(ValueError):
            LLMAnalysis(
                model_id="gpt-4",
                timestamp=datetime.now(UTC),
                market_sentiment="Test",
                bullish_score=7.5,
                bearish_score=2.5,
                confidence=1.5,  # > 1.0
                tokens_used=150,
                latency_ms=2500,
                cost_usd=0.003,
            )


class TestOrderEdgeCases:
    """Test edge cases for Order models to improve coverage."""

    def test_order_decision_validation_edge_cases(self):
        """Test order decision validation edge cases."""
        from decimal import Decimal

        from libs.trading_models.enums import Direction
        from libs.trading_models.orders import OrderDecision

        # Test order with minimum valid values
        order = OrderDecision(
            signal_id="test_signal",
            symbol="BTCUSD",
            direction=Direction.SHORT,  # Test SHORT direction
            order_type="stop",  # Test stop order
            base_quantity=Decimal("0.001"),  # Minimum quantity
            risk_adjusted_quantity=Decimal("0.001"),
            max_position_value=Decimal("1.0"),  # Minimum value
            entry_price=Decimal("50000.0"),  # Valid price
            stop_loss=Decimal("51000.0"),  # For SHORT: stop_loss > entry_price (2% away)
            risk_amount=Decimal("0.01"),  # Minimum risk
            risk_percentage=0.01,  # Minimum percentage
            portfolio_value=Decimal("100.0"),
            available_margin=Decimal("50.0"),
            confidence_score=0.0,  # Minimum confidence
            confluence_score=0.0,  # Minimum confluence
            risk_reward_ratio=0.1,  # Minimum ratio
            decision_reason="Test edge case",
            timeframe_context="1h"  # Valid timeframe
        )

        assert order.direction == Direction.SHORT
        assert order.order_type == "stop"

        # Test basic properties
        assert order.direction == Direction.SHORT
        assert order.order_type == "stop"

        # Test margin calculation
        margin_required = order.calculate_margin_required()
        assert margin_required > 0

    def test_execution_result_edge_cases(self):
        """Test execution result edge cases."""
        from decimal import Decimal

        from libs.trading_models.enums import OrderStatus
        from libs.trading_models.orders import ExecutionResult

        # Test partially filled order
        result = ExecutionResult(
            decision_id="test_decision",
            order_id="test_order",
            status=OrderStatus.PARTIALLY_FILLED,
            submitted_at=datetime.now(UTC),
            filled_quantity=Decimal("0.5"),
            average_price=Decimal("50000.0"),
            commission=Decimal("10.0")
        )

        assert result.is_partially_filled()
        assert not result.is_fully_filled()

        # Test fill percentage calculation
        original_qty = Decimal("1.0")
        fill_pct = result.get_fill_percentage(original_qty)
        assert fill_pct == 50.0

        # Test edge case: zero original quantity
        zero_fill_pct = result.get_fill_percentage(Decimal("0.0"))
        assert zero_fill_pct == 0.0


class TestSignalEdgeCases:
    """Test edge cases for Signal model to improve coverage."""

    def test_signal_validation_edge_cases(self):
        """Test signal validation edge cases."""
        from libs.trading_models.enums import Direction, MarketRegime
        from libs.trading_models.signals import Signal

        # Test signal with edge case values
        signal = Signal(
            signal_id="edge_test",
            symbol="BTCUSD",
            direction=Direction.LONG,
            confluence_score=0.0,  # Minimum value
            confidence=1.0,  # Maximum value
            market_regime=MarketRegime.SIDEWAYS,
            primary_timeframe="1h",  # Valid timeframe
            reasoning="Test edge case signal",  # Required field
            timestamp=datetime.now(UTC)
        )

        assert signal.confluence_score == 0.0
        assert signal.confidence == 1.0

        # Test weighted confluence calculation edge case
        weighted_confluence = signal.get_weighted_confluence()
        assert weighted_confluence == 0.0  # No timeframe analysis

    def test_signal_model_validation_errors(self):
        """Test signal model validation errors."""
        from libs.trading_models.enums import Direction, MarketRegime
        from libs.trading_models.signals import Signal

        # Test invalid confidence values
        with pytest.raises(Exception):  # Should fail validation
            Signal(
                signal_id="invalid_test",
                symbol="BTCUSD",
                direction=Direction.LONG,
                confluence_score=50.0,
                confidence=2.0,  # Invalid - should be <= 1.0
                market_regime=MarketRegime.BULL,
                primary_timeframe="1h",
                timestamp=datetime.now(UTC)
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
