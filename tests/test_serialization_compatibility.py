"""Test serialization compatibility between Python and Rust models."""

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
    PatternHit,
    PatternType,
    Signal,
    Timeframe,
    TimeframeAnalysis,
)


class TestPythonRustCompatibility:
    """Test that Python models serialize to formats compatible with Rust."""

    def test_market_bar_serialization(self):
        """Test MarketBar serialization format."""
        bar = MarketBar(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49500.00"),
            close=Decimal("50500.00"),
            volume=Decimal("100.5"),
            quote_volume=Decimal("5025000.00"),
            trades_count=1250,
            taker_buy_volume=Decimal("60.3"),
        )

        # Serialize to JSON
        json_data = json.loads(bar.to_json())

        # Verify structure matches Rust expectations
        expected_fields = {
            "symbol", "timeframe", "timestamp", "open", "high",
            "low", "close", "volume", "quote_volume", "trades_count",
            "taker_buy_volume"
        }
        assert set(json_data.keys()) == expected_fields

        # Verify data types and values
        assert json_data["symbol"] == "BTCUSDT"
        assert json_data["timeframe"] == "1h"
        assert json_data["open"] == "50000.00"  # Decimal serialized as string
        assert json_data["high"] == "51000.00"
        assert json_data["low"] == "49500.00"
        assert json_data["close"] == "50500.00"
        assert json_data["volume"] == "100.5"
        assert json_data["quote_volume"] == "5025000.00"
        assert json_data["trades_count"] == 1250
        assert json_data["taker_buy_volume"] == "60.3"

        # Verify timestamp format (ISO 8601)
        assert "2024-01-15T12:00:00Z" in json_data["timestamp"]

        # Test round-trip
        restored_bar = MarketBar.from_json(bar.to_json())
        assert restored_bar.symbol == bar.symbol
        assert restored_bar.timeframe == bar.timeframe
        assert restored_bar.open == bar.open
        assert restored_bar.high == bar.high
        assert restored_bar.low == bar.low
        assert restored_bar.close == bar.close
        assert restored_bar.volume == bar.volume

    def test_indicator_snapshot_serialization(self):
        """Test IndicatorSnapshot serialization format."""
        snapshot = IndicatorSnapshot(
            symbol="BTCUSDT",
            timeframe=Timeframe.H4,
            timestamp=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),
            rsi=65.5,
            ema_20=Decimal("50000.00"),
            ema_50=Decimal("49800.00"),
            ema_200=Decimal("48500.00"),
            macd_line=150.5,
            macd_signal=120.3,
            macd_histogram=30.2,
            bb_upper=Decimal("52000.00"),
            bb_middle=Decimal("50000.00"),
            bb_lower=Decimal("48000.00"),
            bb_width=0.08,
            atr=Decimal("500.00"),
            volume_sma=Decimal("1000.0"),
            stoch_k=75.2,
            stoch_d=72.8,
            cci=125.5,
            mfi=68.3,
        )

        json_data = json.loads(snapshot.to_json())

        # Verify critical fields
        assert json_data["symbol"] == "BTCUSDT"
        assert json_data["timeframe"] == "4h"
        assert json_data["rsi"] == 65.5
        assert json_data["ema_20"] == "50000.00"
        assert json_data["macd_line"] == 150.5
        assert json_data["bb_upper"] == "52000.00"
        assert json_data["bb_middle"] == "50000.00"
        assert json_data["bb_lower"] == "48000.00"
        assert json_data["atr"] == "500.00"

        # Test round-trip
        restored = IndicatorSnapshot.from_json(snapshot.to_json())
        assert restored.symbol == snapshot.symbol
        assert restored.rsi == snapshot.rsi
        assert restored.ema_20 == snapshot.ema_20

    def test_pattern_hit_serialization(self):
        """Test PatternHit serialization format."""
        pattern = PatternHit(
            pattern_id="breakout_001",
            pattern_type=PatternType.BREAKOUT,
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC),
            confidence=0.85,
            strength=7.5,
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            support_levels=[Decimal("48000.00"), Decimal("49000.00")],
            resistance_levels=[Decimal("51000.00"), Decimal("52000.00")],
            pattern_data={"breakout_volume": 1.5, "breakout_strength": "strong"},
            bars_analyzed=100,
            lookback_period=50,
            historical_win_rate=0.65,
            avg_return=0.15,
        )

        json_data = json.loads(pattern.to_json())

        # Verify structure
        assert json_data["pattern_id"] == "breakout_001"
        assert json_data["pattern_type"] == "breakout"
        assert json_data["symbol"] == "BTCUSDT"
        assert json_data["timeframe"] == "1h"
        assert json_data["confidence"] == 0.85
        assert json_data["strength"] == 7.5
        assert json_data["entry_price"] == "50000.00"
        assert json_data["stop_loss"] == "49000.00"
        assert json_data["take_profit"] == "52000.00"
        assert json_data["support_levels"] == ["48000.00", "49000.00"]
        assert json_data["resistance_levels"] == ["51000.00", "52000.00"]
        assert json_data["bars_analyzed"] == 100
        assert json_data["lookback_period"] == 50
        assert json_data["historical_win_rate"] == 0.65
        assert json_data["avg_return"] == 0.15

        # Verify pattern_data structure
        assert json_data["pattern_data"]["breakout_volume"] == 1.5
        assert json_data["pattern_data"]["breakout_strength"] == "strong"

        # Test round-trip
        restored = PatternHit.from_json(pattern.to_json())
        assert restored.pattern_id == pattern.pattern_id
        assert restored.pattern_type == pattern.pattern_type
        assert restored.confidence == pattern.confidence
        assert restored.support_levels == pattern.support_levels

    def test_signal_serialization(self):
        """Test Signal serialization format."""
        # Create timeframe analysis
        tf_analysis = TimeframeAnalysis(
            timeframe=Timeframe.H1,
            timestamp=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            trend_score=5.0,
            momentum_score=3.0,
            volatility_score=2.0,
            volume_score=4.0,
            pattern_count=2,
            strongest_pattern_confidence=0.85,
            bullish_indicators=7,
            bearish_indicators=2,
            neutral_indicators=1,
            timeframe_weight=0.6,
        )

        # Create LLM analysis
        llm_analysis = LLMAnalysis(
            model_id="gpt-4-turbo",
            timestamp=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            market_sentiment="Bullish momentum building with strong breakout pattern",
            key_insights=["Strong volume confirmation", "Multiple timeframe alignment"],
            risk_factors=["Potential resistance at 52k level"],
            bullish_score=7.5,
            bearish_score=2.5,
            confidence=0.85,
            tokens_used=150,
            latency_ms=2500,
            cost_usd=0.003,
        )

        signal = Signal(
            signal_id="signal_001",
            symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            direction=Direction.LONG,
            confluence_score=85.5,
            confidence=0.85,
            market_regime=MarketRegime.BULL,
            primary_timeframe=Timeframe.H1,
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_reward_ratio=2.0,
            max_risk_pct=2.0,
            reasoning="Strong bullish breakout with multiple confirmations",
            key_factors=["Volume breakout", "Multiple timeframe alignment", "Strong momentum"],
            priority=3,
            llm_analysis=llm_analysis,
        )

        # Add timeframe analysis
        signal.add_timeframe_analysis(tf_analysis)

        json_data = json.loads(signal.to_json())

        # Verify main signal structure
        assert json_data["signal_id"] == "signal_001"
        assert json_data["symbol"] == "BTCUSDT"
        assert json_data["direction"] == "long"
        assert json_data["confluence_score"] == 85.5
        assert json_data["confidence"] == 0.85
        assert json_data["market_regime"] == "bull"
        assert json_data["primary_timeframe"] == "1h"
        assert json_data["entry_price"] == "50000.00"
        assert json_data["stop_loss"] == "49000.00"
        assert json_data["take_profit"] == "52000.00"
        assert json_data["risk_reward_ratio"] == 2.0
        assert json_data["priority"] == 3

        # Verify timeframe analysis structure
        assert "timeframe_analysis" in json_data
        assert "1h" in json_data["timeframe_analysis"]
        tf_data = json_data["timeframe_analysis"]["1h"]
        assert tf_data["trend_score"] == 5.0
        assert tf_data["momentum_score"] == 3.0
        assert tf_data["timeframe_weight"] == 0.6

        # Verify LLM analysis structure
        assert "llm_analysis" in json_data
        llm_data = json_data["llm_analysis"]
        assert llm_data["model_id"] == "gpt-4-turbo"
        assert llm_data["bullish_score"] == 7.5
        assert llm_data["bearish_score"] == 2.5
        assert llm_data["tokens_used"] == 150
        assert llm_data["cost_usd"] == 0.003

        # Test round-trip
        restored = Signal.from_json(signal.to_json())
        assert restored.signal_id == signal.signal_id
        assert restored.direction == signal.direction
        assert restored.confluence_score == signal.confluence_score
        assert len(restored.timeframe_analysis) == 1
        assert restored.llm_analysis is not None
        assert restored.llm_analysis.model_id == "gpt-4-turbo"

    def test_order_decision_serialization(self):
        """Test OrderDecision serialization format."""
        decision = OrderDecision(
            signal_id="signal_001",
            symbol="BTCUSDT",
            direction=Direction.LONG,
            order_type=OrderType.LIMIT,
            base_quantity=Decimal("1.0"),
            risk_adjusted_quantity=Decimal("0.8"),
            max_position_value=Decimal("40000.00"),
            entry_price=Decimal("50000.00"),
            stop_loss=Decimal("49000.00"),
            take_profit=Decimal("52000.00"),
            risk_amount=Decimal("800.00"),
            risk_percentage=2.0,
            leverage=2.0,
            portfolio_value=Decimal("100000.00"),
            available_margin=Decimal("50000.00"),
            current_exposure=0.1,
            confidence_score=0.85,
            confluence_score=85.5,
            risk_reward_ratio=2.5,
            slippage_tolerance=0.001,
            max_execution_time=300,
            partial_fill_acceptable=True,
            decision_reason="Strong bullish signal with good risk/reward",
            risk_factors=["Market volatility", "Resistance level nearby"],
            supporting_factors=["Strong volume", "Multiple confirmations"],
            timeframe_context=Timeframe.H1,
            market_conditions={"volatility": "medium", "trend": "bullish"},
        )

        json_data = json.loads(decision.to_json())

        # Verify structure
        assert json_data["signal_id"] == "signal_001"
        assert json_data["symbol"] == "BTCUSDT"
        assert json_data["direction"] == "long"
        assert json_data["order_type"] == "limit"
        assert json_data["base_quantity"] == "1.0"
        assert json_data["risk_adjusted_quantity"] == "0.8"
        assert json_data["entry_price"] == "50000.00"
        assert json_data["stop_loss"] == "49000.00"
        assert json_data["take_profit"] == "52000.00"
        assert json_data["risk_percentage"] == 2.0
        assert json_data["leverage"] == 2.0
        assert json_data["confidence_score"] == 0.85
        assert json_data["risk_reward_ratio"] == 2.5
        assert json_data["timeframe_context"] == "1h"

        # Verify arrays
        assert json_data["risk_factors"] == ["Market volatility", "Resistance level nearby"]
        assert json_data["supporting_factors"] == ["Strong volume", "Multiple confirmations"]

        # Verify nested object
        assert json_data["market_conditions"]["volatility"] == "medium"
        assert json_data["market_conditions"]["trend"] == "bullish"

        # Test round-trip
        restored = OrderDecision.from_json(decision.to_json())
        assert restored.signal_id == decision.signal_id
        assert restored.direction == decision.direction
        assert restored.base_quantity == decision.base_quantity
        assert restored.risk_factors == decision.risk_factors

    def test_execution_result_serialization(self):
        """Test ExecutionResult serialization format."""
        result = ExecutionResult(
            decision_id="decision_001",
            order_id="order_12345",
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.8"),
            average_price=Decimal("50100.00"),
            submitted_at=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            filled_at=datetime(2024, 1, 15, 14, 0, 30, tzinfo=UTC),
            commission=Decimal("5.0"),
            slippage=0.002,
            execution_time_ms=1500,
            partial_fills=[
                {"quantity": "0.3", "price": "50050.00", "timestamp": "2024-01-15T14:00:15Z"},
                {"quantity": "0.5", "price": "50120.00", "timestamp": "2024-01-15T14:00:30Z"},
            ],
            retry_count=1,
        )

        json_data = json.loads(result.to_json())

        # Verify structure
        assert json_data["decision_id"] == "decision_001"
        assert json_data["order_id"] == "order_12345"
        assert json_data["status"] == "filled"
        assert json_data["filled_quantity"] == "0.8"
        assert json_data["average_price"] == "50100.00"
        assert json_data["commission"] == "5.0"
        assert json_data["slippage"] == 0.002
        assert json_data["execution_time_ms"] == 1500
        assert json_data["retry_count"] == 1

        # Verify partial fills array
        assert len(json_data["partial_fills"]) == 2
        assert json_data["partial_fills"][0]["quantity"] == "0.3"
        assert json_data["partial_fills"][1]["price"] == "50120.00"

        # Test round-trip
        restored = ExecutionResult.from_json(result.to_json())
        assert restored.decision_id == result.decision_id
        assert restored.status == result.status
        assert restored.filled_quantity == result.filled_quantity
        assert len(restored.partial_fills) == 2


class TestEnumSerialization:
    """Test enum serialization compatibility."""

    def test_timeframe_enum_values(self):
        """Test Timeframe enum serialization."""
        test_cases = [
            (Timeframe.M15, "15m"),
            (Timeframe.H1, "1h"),
            (Timeframe.H4, "4h"),
            (Timeframe.D1, "1d"),
        ]

        for enum_val, expected_str in test_cases:
            # Test direct enum serialization
            bar = MarketBar(
                symbol="TEST",
                timeframe=enum_val,
                timestamp=datetime.now(UTC),
                open=Decimal("1.0"),
                high=Decimal("1.0"),
                low=Decimal("1.0"),
                close=Decimal("1.0"),
                volume=Decimal("1.0"),
            )

            json_data = json.loads(bar.to_json())
            assert json_data["timeframe"] == expected_str

    def test_direction_enum_values(self):
        """Test Direction enum serialization."""
        test_cases = [
            (Direction.LONG, "long"),
            (Direction.SHORT, "short"),
        ]

        for enum_val, expected_str in test_cases:
            signal = Signal(
                signal_id="test",
                symbol="TEST",
                timestamp=datetime.now(UTC),
                direction=enum_val,
                confluence_score=50.0,
                confidence=0.5,
                market_regime=MarketRegime.SIDEWAYS,
                primary_timeframe=Timeframe.H1,
                reasoning="Test",
            )

            json_data = json.loads(signal.to_json())
            assert json_data["direction"] == expected_str

    def test_all_enum_consistency(self):
        """Test that all enums serialize consistently."""
        # Create a comprehensive model with all enums
        decision = OrderDecision(
            signal_id="test",
            symbol="TEST",
            direction=Direction.SHORT,
            order_type=OrderType.STOP_LIMIT,
            base_quantity=Decimal("1.0"),
            risk_adjusted_quantity=Decimal("0.8"),
            max_position_value=Decimal("1000.00"),
            entry_price=Decimal("100.00"),
            stop_loss=Decimal("110.00"),
            risk_amount=Decimal("80.00"),
            risk_percentage=2.0,
            leverage=1.0,
            portfolio_value=Decimal("10000.00"),
            available_margin=Decimal("5000.00"),
            current_exposure=0.1,
            confidence_score=0.7,
            confluence_score=70.0,
            risk_reward_ratio=1.5,
            decision_reason="Test all enums",
            timeframe_context=Timeframe.D1,
        )

        json_data = json.loads(decision.to_json())

        # Verify all enum serializations
        assert json_data["direction"] == "short"
        assert json_data["order_type"] == "stop_limit"
        assert json_data["timeframe_context"] == "1d"


class TestDataTypeCompatibility:
    """Test data type compatibility between Python and Rust."""

    def test_decimal_serialization(self):
        """Test that Decimal fields serialize as strings for Rust compatibility."""
        bar = MarketBar(
            symbol="TEST",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("12345.67890"),
            high=Decimal("12400.12345"),
            low=Decimal("12300.98765"),
            close=Decimal("12350.55555"),
            volume=Decimal("1000.123456789"),
        )

        json_data = json.loads(bar.to_json())

        # Verify Decimal fields are serialized as strings
        assert isinstance(json_data["open"], str)
        assert isinstance(json_data["high"], str)
        assert isinstance(json_data["low"], str)
        assert isinstance(json_data["close"], str)
        assert isinstance(json_data["volume"], str)

        # Verify precision is maintained
        assert json_data["open"] == "12345.67890"
        assert json_data["volume"] == "1000.123456789"

    def test_datetime_serialization(self):
        """Test datetime serialization format."""
        test_time = datetime(2024, 1, 15, 14, 30, 45, 123456, tzinfo=UTC)

        bar = MarketBar(
            symbol="TEST",
            timeframe=Timeframe.H1,
            timestamp=test_time,
            open=Decimal("1.0"),
            high=Decimal("1.0"),
            low=Decimal("1.0"),
            close=Decimal("1.0"),
            volume=Decimal("1.0"),
        )

        json_data = json.loads(bar.to_json())

        # Verify ISO 8601 format with UTC timezone
        timestamp_str = json_data["timestamp"]
        assert "2024-01-15T14:30:45" in timestamp_str
        assert timestamp_str.endswith("Z") or "+00:00" in timestamp_str

    def test_optional_fields(self):
        """Test optional field serialization."""
        # Test with minimal required fields
        bar = MarketBar(
            symbol="TEST",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("1.0"),
            high=Decimal("1.0"),
            low=Decimal("1.0"),
            close=Decimal("1.0"),
            volume=Decimal("1.0"),
        )

        json_data = json.loads(bar.to_json())

        # Verify optional fields are null/None when not provided
        assert json_data["quote_volume"] is None
        assert json_data["trades_count"] is None
        assert json_data["taker_buy_volume"] is None

        # Test with optional fields provided
        bar_with_optional = MarketBar(
            symbol="TEST",
            timeframe=Timeframe.H1,
            timestamp=datetime.now(UTC),
            open=Decimal("1.0"),
            high=Decimal("1.0"),
            low=Decimal("1.0"),
            close=Decimal("1.0"),
            volume=Decimal("1.0"),
            quote_volume=Decimal("100.0"),
            trades_count=50,
            taker_buy_volume=Decimal("60.0"),
        )

        json_data_with_optional = json.loads(bar_with_optional.to_json())

        # Verify optional fields are included when provided
        assert json_data_with_optional["quote_volume"] == "100.0"
        assert json_data_with_optional["trades_count"] == 50
        assert json_data_with_optional["taker_buy_volume"] == "60.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
