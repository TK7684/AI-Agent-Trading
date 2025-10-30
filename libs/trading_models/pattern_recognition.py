"""
Pattern Recognition Engine

This module implements comprehensive pattern recognition algorithms for the
autonomous trading system, including support/resistance levels, breakouts,
candlestick patterns, and divergence detection.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

import numpy as np

from .enums import PatternType, Timeframe
from .market_data import MarketBar
from .patterns import PatternCollection, PatternHit
from .technical_indicators import MACDResult, RSIResult

logger = logging.getLogger(__name__)


@dataclass
class SupportResistanceLevel:
    """Support or resistance level with strength metrics."""
    price: float
    strength: int  # Number of touches
    first_touch: datetime
    last_touch: datetime
    is_support: bool
    confidence: float


@dataclass
class DivergenceSignal:
    """Divergence between price and indicator."""
    start_idx: int
    end_idx: int
    price_direction: str  # "higher_high", "lower_low", etc.
    indicator_direction: str
    strength: float
    confidence: float


class PatternRecognitionEngine:
    """Main pattern recognition engine."""

    def __init__(self, min_pattern_confidence: float = 0.3):
        self.min_pattern_confidence = min_pattern_confidence
        self.logger = logging.getLogger(__name__)

    def analyze_patterns(
        self,
        data: list[MarketBar],
        indicators: Optional[dict[str, Any]] = None,
        timeframe: Timeframe = Timeframe.H1
    ) -> PatternCollection:
        """Analyze all patterns for given market data."""
        if len(data) < 5:  # Reduced minimum for candlestick patterns
            self.logger.warning(f"Insufficient data for pattern analysis: {len(data)} bars")
            return PatternCollection(
                symbol=data[0].symbol if data else "UNKNOWN",
                timeframe=timeframe,
                timestamp=datetime.now(UTC)
            )

        collection = PatternCollection(
            symbol=data[0].symbol,
            timeframe=timeframe,
            timestamp=datetime.now(UTC)
        )

        try:
            # Detect candlestick patterns (works with fewer bars)
            candlestick_patterns = self.detect_candlestick_patterns(data)
            for pattern in candlestick_patterns:
                if pattern.confidence >= self.min_pattern_confidence:
                    collection.add_pattern(pattern)

            # Only run complex patterns if we have enough data
            if len(data) >= 20:
                # Detect support/resistance levels
                sr_levels = self.detect_support_resistance(data)
                for level in sr_levels:
                    pattern = self._create_sr_pattern(data[0].symbol, timeframe, level)
                    if pattern.confidence >= self.min_pattern_confidence:
                        collection.add_pattern(pattern)

                # Detect breakout patterns
                breakout_patterns = self.detect_breakouts(data, sr_levels)
                for pattern in breakout_patterns:
                    if pattern.confidence >= self.min_pattern_confidence:
                        collection.add_pattern(pattern)

                # Detect divergences if indicators are provided
                if indicators:
                    divergence_patterns = self.detect_divergences(data, indicators)
                    for pattern in divergence_patterns:
                        if pattern.confidence >= self.min_pattern_confidence:
                            collection.add_pattern(pattern)

            self.logger.info(f"Detected {collection.total_patterns} patterns for {data[0].symbol}")

        except Exception as e:
            self.logger.error(f"Error in pattern analysis: {e}")

        return collection

    def detect_support_resistance(
        self,
        data: list[MarketBar],
        lookback_period: int = 50,
        min_touches: int = 2,
        touch_tolerance: float = 0.01  # 1% tolerance - more lenient
    ) -> list[SupportResistanceLevel]:
        """Detect support and resistance levels."""
        if len(data) < lookback_period:
            return []

        levels = []

        # Extract price data
        highs = np.array([float(bar.high) for bar in data])
        lows = np.array([float(bar.low) for bar in data])
        closes = np.array([float(bar.close) for bar in data])

        # Find local peaks and troughs
        resistance_candidates = self._find_local_extrema(highs, window=5, find_peaks=True)
        support_candidates = self._find_local_extrema(lows, window=5, find_peaks=False)

        # Analyze resistance levels
        for peak_idx in resistance_candidates:
            if peak_idx < len(data) - 5:  # More lenient - don't use very recent peaks
                level = self._analyze_level(
                    data, highs, peak_idx, True, min_touches, touch_tolerance
                )
                if level:
                    levels.append(level)

        # Analyze support levels
        for trough_idx in support_candidates:
            if trough_idx < len(data) - 5:  # More lenient - don't use very recent troughs
                level = self._analyze_level(
                    data, lows, trough_idx, False, min_touches, touch_tolerance
                )
                if level:
                    levels.append(level)

        # Sort by strength and return top levels
        levels.sort(key=lambda x: x.strength, reverse=True)
        return levels[:10]  # Return top 10 levels

    def _find_local_extrema(
        self,
        prices: np.ndarray,
        window: int = 5,
        find_peaks: bool = True
    ) -> list[int]:
        """Find local peaks or troughs in price data."""
        extrema = []

        for i in range(window, len(prices) - window):
            window_data = prices[i - window:i + window + 1]
            center_idx = window

            if find_peaks:
                # Find peaks
                if prices[i] == np.max(window_data) and prices[i] > np.mean(window_data):
                    extrema.append(i)
            else:
                # Find troughs
                if prices[i] == np.min(window_data) and prices[i] < np.mean(window_data):
                    extrema.append(i)

        return extrema

    def _analyze_level(
        self,
        data: list[MarketBar],
        prices: np.ndarray,
        level_idx: int,
        is_resistance: bool,
        min_touches: int,
        tolerance: float
    ) -> Optional[SupportResistanceLevel]:
        """Analyze a potential support/resistance level."""
        level_price = prices[level_idx]
        touches = []

        # Find all touches of this level
        for i, price in enumerate(prices):
            if abs(price - level_price) / level_price <= tolerance:
                touches.append((i, data[i].timestamp))

        if len(touches) < min_touches:
            return None

        # Calculate confidence based on touches and time span
        strength = len(touches)
        time_span = (touches[-1][1] - touches[0][1]).days

        # Higher confidence for more touches over longer time periods
        confidence = min(0.9, (strength - 1) * 0.2 + min(0.3, time_span / 100))

        return SupportResistanceLevel(
            price=level_price,
            strength=strength,
            first_touch=touches[0][1],
            last_touch=touches[-1][1],
            is_support=not is_resistance,
            confidence=confidence
        )

    def detect_breakouts(
        self,
        data: list[MarketBar],
        sr_levels: list[SupportResistanceLevel],
        min_volume_ratio: float = 1.5
    ) -> list[PatternHit]:
        """Detect breakout patterns."""
        if len(data) < 10 or not sr_levels:
            return []

        patterns = []
        recent_data = data[-20:]  # Look at recent 20 bars

        for i in range(5, len(recent_data)):
            current_bar = recent_data[i]
            prev_bars = recent_data[i-5:i]

            # Check for breakouts through support/resistance levels
            for level in sr_levels:
                breakout_pattern = self._check_level_breakout(
                    current_bar, prev_bars, level, min_volume_ratio
                )
                if breakout_pattern:
                    patterns.append(breakout_pattern)

        return patterns

    def _check_level_breakout(
        self,
        current_bar: MarketBar,
        prev_bars: list[MarketBar],
        level: SupportResistanceLevel,
        min_volume_ratio: float
    ) -> Optional[PatternHit]:
        """Check if current bar breaks through a support/resistance level."""
        current_close = float(current_bar.close)
        level_price = level.price
        tolerance = 0.005  # 0.5% tolerance for breakout confirmation - more lenient

        # Check if price has broken through the level
        if level.is_support:
            # Support breakout (bearish)
            if current_close < level_price * (1 - tolerance):
                # Confirm previous bars were above support
                if all(float(bar.low) > level_price * (1 - tolerance) for bar in prev_bars[-3:]):
                    return self._create_breakout_pattern(
                        current_bar, level, False, min_volume_ratio
                    )
        else:
            # Resistance breakout (bullish)
            if current_close > level_price * (1 + tolerance):
                # Confirm previous bars were below resistance
                if all(float(bar.high) < level_price * (1 + tolerance) for bar in prev_bars[-3:]):
                    return self._create_breakout_pattern(
                        current_bar, level, True, min_volume_ratio
                    )

        return None

    def _create_breakout_pattern(
        self,
        breakout_bar: MarketBar,
        level: SupportResistanceLevel,
        is_bullish: bool,
        min_volume_ratio: float
    ) -> PatternHit:
        """Create a breakout pattern hit."""
        # Calculate volume confirmation
        avg_volume = np.mean([float(bar.volume) for bar in [breakout_bar]])  # Simplified
        volume_ratio = float(breakout_bar.volume) / max(avg_volume, 1)

        # Calculate confidence based on level strength and volume
        base_confidence = level.confidence * 0.7
        volume_boost = min(0.3, (volume_ratio - 1) * 0.1) if volume_ratio > min_volume_ratio else 0
        confidence = min(0.95, base_confidence + volume_boost)

        # Calculate strength
        strength = level.strength + (2 if volume_ratio > min_volume_ratio else 0)

        return PatternHit(
            pattern_id=f"breakout_{breakout_bar.symbol}_{breakout_bar.timestamp.isoformat()}",
            pattern_type=PatternType.BREAKOUT,
            symbol=breakout_bar.symbol,
            timeframe=breakout_bar.timeframe,
            timestamp=breakout_bar.timestamp,
            confidence=confidence,
            strength=min(10.0, strength),
            entry_price=Decimal(str(breakout_bar.close)),
            support_levels=[Decimal(str(level.price))] if level.is_support else [],
            resistance_levels=[Decimal(str(level.price))] if not level.is_support else [],
            pattern_data={
                "breakout_direction": "bullish" if is_bullish else "bearish",
                "level_strength": level.strength,
                "volume_ratio": volume_ratio,
                "level_price": level.price
            },
            bars_analyzed=20,
            lookback_period=50
        )

    def detect_candlestick_patterns(self, data: list[MarketBar]) -> list[PatternHit]:
        """Detect candlestick patterns."""
        if len(data) < 5:
            return []

        patterns = []

        # Analyze recent bars for patterns
        for i in range(2, len(data)):
            current = data[i]
            prev1 = data[i-1]
            prev2 = data[i-2] if i >= 2 else None

            # Pin Bar detection
            pin_bar = self._detect_pin_bar(current)
            if pin_bar:
                patterns.append(pin_bar)

            # Engulfing pattern detection
            if prev1:
                engulfing = self._detect_engulfing(prev1, current)
                if engulfing:
                    patterns.append(engulfing)

            # Doji detection
            doji = self._detect_doji(current)
            if doji:
                patterns.append(doji)

        return patterns

    def _detect_pin_bar(self, bar: MarketBar) -> Optional[PatternHit]:
        """Detect Pin Bar (Hammer/Shooting Star) pattern."""
        o, h, l, c = float(bar.open), float(bar.high), float(bar.low), float(bar.close)

        # Calculate body and wick sizes
        body_size = abs(c - o)
        total_range = h - l

        if total_range == 0:
            return None

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # Pin bar criteria
        body_ratio = body_size / total_range

        # Bullish Pin Bar (Hammer) - long lower wick, small body, small upper wick
        if (lower_wick > body_size * 2 and
            upper_wick < lower_wick * 0.3 and  # Upper wick should be much smaller than lower wick
            body_ratio < 0.3):

            confidence = min(0.8, 0.4 + (lower_wick / total_range) * 0.4)

            return PatternHit(
                pattern_id=f"pin_bar_{bar.symbol}_{bar.timestamp.isoformat()}",
                pattern_type=PatternType.PIN_BAR,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                timestamp=bar.timestamp,
                confidence=confidence,
                strength=min(10.0, (lower_wick / max(body_size, 1)) * 2),
                entry_price=Decimal(str(c)),
                pattern_data={
                    "pin_type": "bullish_hammer",
                    "body_ratio": body_ratio,
                    "lower_wick_ratio": lower_wick / total_range,
                    "upper_wick_ratio": upper_wick / total_range
                },
                bars_analyzed=1,
                lookback_period=1
            )

        # Bearish Pin Bar (Shooting Star) - long upper wick, small body, small lower wick
        elif (upper_wick > body_size * 2 and
              lower_wick < upper_wick * 0.3 and  # Lower wick should be much smaller than upper wick
              body_ratio < 0.3):

            confidence = min(0.8, 0.4 + (upper_wick / total_range) * 0.4)

            return PatternHit(
                pattern_id=f"pin_bar_{bar.symbol}_{bar.timestamp.isoformat()}",
                pattern_type=PatternType.PIN_BAR,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                timestamp=bar.timestamp,
                confidence=confidence,
                strength=min(10.0, (upper_wick / max(body_size, 1)) * 2),
                entry_price=Decimal(str(c)),
                pattern_data={
                    "pin_type": "bearish_shooting_star",
                    "body_ratio": body_ratio,
                    "lower_wick_ratio": lower_wick / total_range,
                    "upper_wick_ratio": upper_wick / total_range
                },
                bars_analyzed=1,
                lookback_period=1
            )

        return None

    def _detect_engulfing(self, prev_bar: MarketBar, current_bar: MarketBar) -> Optional[PatternHit]:
        """Detect Engulfing pattern."""
        prev_o, prev_c = float(prev_bar.open), float(prev_bar.close)
        curr_o, curr_c = float(current_bar.open), float(current_bar.close)

        prev_body = abs(prev_c - prev_o)
        curr_body = abs(curr_c - curr_o)

        # Minimum body size requirement
        if prev_body == 0 or curr_body < prev_body * 1.1:
            return None

        # Bullish Engulfing
        if (prev_c < prev_o and  # Previous bar is bearish
            curr_c > curr_o and  # Current bar is bullish
            curr_o < prev_c and  # Current open below previous close
            curr_c > prev_o):    # Current close above previous open

            confidence = min(0.85, 0.5 + (curr_body / prev_body - 1) * 0.35)

            return PatternHit(
                pattern_id=f"engulfing_{current_bar.symbol}_{current_bar.timestamp.isoformat()}",
                pattern_type=PatternType.ENGULFING,
                symbol=current_bar.symbol,
                timeframe=current_bar.timeframe,
                timestamp=current_bar.timestamp,
                confidence=confidence,
                strength=min(10.0, curr_body / prev_body * 3),
                entry_price=Decimal(str(curr_c)),
                pattern_data={
                    "engulfing_type": "bullish",
                    "body_ratio": curr_body / prev_body,
                    "prev_body_size": prev_body,
                    "curr_body_size": curr_body
                },
                bars_analyzed=2,
                lookback_period=2
            )

        # Bearish Engulfing
        elif (prev_c > prev_o and  # Previous bar is bullish
              curr_c < curr_o and  # Current bar is bearish
              curr_o > prev_c and  # Current open above previous close
              curr_c < prev_o):    # Current close below previous open

            confidence = min(0.85, 0.5 + (curr_body / prev_body - 1) * 0.35)

            return PatternHit(
                pattern_id=f"engulfing_{current_bar.symbol}_{current_bar.timestamp.isoformat()}",
                pattern_type=PatternType.ENGULFING,
                symbol=current_bar.symbol,
                timeframe=current_bar.timeframe,
                timestamp=current_bar.timestamp,
                confidence=confidence,
                strength=min(10.0, curr_body / prev_body * 3),
                entry_price=Decimal(str(curr_c)),
                pattern_data={
                    "engulfing_type": "bearish",
                    "body_ratio": curr_body / prev_body,
                    "prev_body_size": prev_body,
                    "curr_body_size": curr_body
                },
                bars_analyzed=2,
                lookback_period=2
            )

        return None

    def _detect_doji(self, bar: MarketBar) -> Optional[PatternHit]:
        """Detect Doji pattern."""
        o, h, l, c = float(bar.open), float(bar.high), float(bar.low), float(bar.close)

        body_size = abs(c - o)
        total_range = h - l

        if total_range == 0:
            return None

        # Doji criteria - very small body relative to range
        body_ratio = body_size / total_range

        if body_ratio < 0.1:  # Body is less than 10% of total range
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l

            # Calculate confidence based on how small the body is
            confidence = min(0.75, 0.3 + (0.1 - body_ratio) * 4)

            # Determine doji type
            doji_type = "standard"
            if upper_wick > lower_wick * 2:
                doji_type = "dragonfly"
            elif lower_wick > upper_wick * 2:
                doji_type = "gravestone"

            return PatternHit(
                pattern_id=f"doji_{bar.symbol}_{bar.timestamp.isoformat()}",
                pattern_type=PatternType.DOJI,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                timestamp=bar.timestamp,
                confidence=confidence,
                strength=min(10.0, (0.1 - body_ratio) * 50),
                entry_price=Decimal(str(c)),
                pattern_data={
                    "doji_type": doji_type,
                    "body_ratio": body_ratio,
                    "upper_wick_ratio": upper_wick / total_range,
                    "lower_wick_ratio": lower_wick / total_range
                },
                bars_analyzed=1,
                lookback_period=1
            )

        return None

    def detect_divergences(
        self,
        data: list[MarketBar],
        indicators: dict[str, Any],
        lookback_period: int = 20
    ) -> list[PatternHit]:
        """Detect divergences between price and indicators."""
        if len(data) < lookback_period or not indicators:
            return []

        patterns = []

        # Check RSI divergence
        if 'rsi' in indicators and indicators['rsi']:
            rsi_divergences = self._detect_rsi_divergence(data, indicators['rsi'], lookback_period)
            patterns.extend(rsi_divergences)

        # Check MACD divergence
        if 'macd' in indicators and indicators['macd']:
            macd_divergences = self._detect_macd_divergence(data, indicators['macd'], lookback_period)
            patterns.extend(macd_divergences)

        return patterns

    def _detect_rsi_divergence(
        self,
        data: list[MarketBar],
        rsi_data: list[RSIResult],
        lookback_period: int
    ) -> list[PatternHit]:
        """Detect RSI divergence patterns."""
        if len(rsi_data) < lookback_period:
            return []

        patterns = []
        recent_data = data[-lookback_period:]
        recent_rsi = rsi_data[-lookback_period:]

        # Find price peaks and troughs
        prices = np.array([float(bar.close) for bar in recent_data])
        rsi_values = np.array([rsi.value for rsi in recent_rsi])

        price_peaks = self._find_local_extrema(prices, window=3, find_peaks=True)
        price_troughs = self._find_local_extrema(prices, window=3, find_peaks=False)

        # Check for bullish divergence (price makes lower low, RSI makes higher low)
        if len(price_troughs) >= 2:
            for i in range(1, len(price_troughs)):
                curr_trough = price_troughs[i]
                prev_trough = price_troughs[i-1]

                if (prices[curr_trough] < prices[prev_trough] and
                    rsi_values[curr_trough] > rsi_values[prev_trough]):

                    divergence = self._create_divergence_pattern(
                        recent_data[curr_trough], "bullish", "RSI",
                        prices[prev_trough], prices[curr_trough],
                        rsi_values[prev_trough], rsi_values[curr_trough]
                    )
                    patterns.append(divergence)

        # Check for bearish divergence (price makes higher high, RSI makes lower high)
        if len(price_peaks) >= 2:
            for i in range(1, len(price_peaks)):
                curr_peak = price_peaks[i]
                prev_peak = price_peaks[i-1]

                if (prices[curr_peak] > prices[prev_peak] and
                    rsi_values[curr_peak] < rsi_values[prev_peak]):

                    divergence = self._create_divergence_pattern(
                        recent_data[curr_peak], "bearish", "RSI",
                        prices[prev_peak], prices[curr_peak],
                        rsi_values[prev_peak], rsi_values[curr_peak]
                    )
                    patterns.append(divergence)

        return patterns

    def _detect_macd_divergence(
        self,
        data: list[MarketBar],
        macd_data: list[MACDResult],
        lookback_period: int
    ) -> list[PatternHit]:
        """Detect MACD divergence patterns."""
        if len(macd_data) < lookback_period:
            return []

        patterns = []
        recent_data = data[-lookback_period:]
        recent_macd = macd_data[-lookback_period:]

        # Find price peaks and troughs
        prices = np.array([float(bar.close) for bar in recent_data])
        macd_values = np.array([macd.value for macd in recent_macd])

        price_peaks = self._find_local_extrema(prices, window=3, find_peaks=True)
        price_troughs = self._find_local_extrema(prices, window=3, find_peaks=False)

        # Check for bullish divergence
        if len(price_troughs) >= 2:
            for i in range(1, len(price_troughs)):
                curr_trough = price_troughs[i]
                prev_trough = price_troughs[i-1]

                if (prices[curr_trough] < prices[prev_trough] and
                    macd_values[curr_trough] > macd_values[prev_trough]):

                    divergence = self._create_divergence_pattern(
                        recent_data[curr_trough], "bullish", "MACD",
                        prices[prev_trough], prices[curr_trough],
                        macd_values[prev_trough], macd_values[curr_trough]
                    )
                    patterns.append(divergence)

        # Check for bearish divergence
        if len(price_peaks) >= 2:
            for i in range(1, len(price_peaks)):
                curr_peak = price_peaks[i]
                prev_peak = price_peaks[i-1]

                if (prices[curr_peak] > prices[prev_peak] and
                    macd_values[curr_peak] < macd_values[prev_peak]):

                    divergence = self._create_divergence_pattern(
                        recent_data[curr_peak], "bearish", "MACD",
                        prices[prev_peak], prices[curr_peak],
                        macd_values[prev_peak], macd_values[curr_peak]
                    )
                    patterns.append(divergence)

        return patterns

    def _create_divergence_pattern(
        self,
        bar: MarketBar,
        divergence_type: str,
        indicator_name: str,
        prev_price: float,
        curr_price: float,
        prev_indicator: float,
        curr_indicator: float
    ) -> PatternHit:
        """Create a divergence pattern hit."""
        # Calculate divergence strength
        price_change = abs(curr_price - prev_price) / prev_price
        indicator_change = abs(curr_indicator - prev_indicator) / abs(prev_indicator)

        # Higher strength when price and indicator move in opposite directions more strongly
        strength = min(10.0, (price_change + indicator_change) * 10)

        # Confidence based on the magnitude of divergence
        confidence = min(0.8, 0.4 + min(0.4, price_change * 5))

        return PatternHit(
            pattern_id=f"divergence_{bar.symbol}_{bar.timestamp.isoformat()}",
            pattern_type=PatternType.DIVERGENCE,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            timestamp=bar.timestamp,
            confidence=confidence,
            strength=strength,
            entry_price=Decimal(str(bar.close)),
            pattern_data={
                "divergence_type": divergence_type,
                "indicator": indicator_name,
                "price_change_pct": price_change,
                "indicator_change_pct": indicator_change,
                "prev_price": prev_price,
                "curr_price": curr_price,
                "prev_indicator": prev_indicator,
                "curr_indicator": curr_indicator
            },
            bars_analyzed=20,
            lookback_period=20
        )

    def _create_sr_pattern(
        self,
        symbol: str,
        timeframe: Timeframe,
        level: SupportResistanceLevel
    ) -> PatternHit:
        """Create a support/resistance pattern hit."""
        return PatternHit(
            pattern_id=f"sr_{symbol}_{level.price}_{level.first_touch.isoformat()}",
            pattern_type=PatternType.SUPPORT_RESISTANCE,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=level.last_touch,
            confidence=level.confidence,
            strength=min(10.0, level.strength * 2),
            entry_price=Decimal(str(level.price)),
            support_levels=[Decimal(str(level.price))] if level.is_support else [],
            resistance_levels=[Decimal(str(level.price))] if not level.is_support else [],
            pattern_data={
                "level_type": "support" if level.is_support else "resistance",
                "touches": level.strength,
                "first_touch": level.first_touch.isoformat(),
                "last_touch": level.last_touch.isoformat(),
                "time_span_days": (level.last_touch - level.first_touch).days
            },
            bars_analyzed=50,
            lookback_period=50
        )


class PatternConfidenceScorer:
    """Advanced pattern confidence scoring system."""

    def __init__(self):
        self.pattern_weights = {
            PatternType.SUPPORT_RESISTANCE: 1.0,
            PatternType.BREAKOUT: 1.2,
            PatternType.PIN_BAR: 0.8,
            PatternType.ENGULFING: 0.9,
            PatternType.DOJI: 0.6,
            PatternType.DIVERGENCE: 1.1
        }

    def calculate_confluence_score(
        self,
        patterns: list[PatternHit],
        market_context: Optional[dict[str, Any]] = None
    ) -> float:
        """Calculate confluence score from multiple patterns."""
        if not patterns:
            return 0.0

        # Weight patterns by type and confidence
        weighted_score = 0.0
        total_weight = 0.0

        for pattern in patterns:
            weight = self.pattern_weights.get(pattern.pattern_type, 1.0)
            weighted_score += pattern.confidence * pattern.strength * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        base_score = weighted_score / total_weight

        # Apply market context adjustments
        if market_context:
            base_score = self._apply_market_context(base_score, patterns, market_context)

        return min(100.0, base_score * 10)  # Scale to 0-100

    def _apply_market_context(
        self,
        base_score: float,
        patterns: list[PatternHit],
        context: dict[str, Any]
    ) -> float:
        """Apply market context adjustments to confidence score."""
        adjusted_score = base_score

        # Volume context
        if 'volume_ratio' in context:
            volume_ratio = context['volume_ratio']
            if volume_ratio > 1.5:
                adjusted_score *= 1.1  # Boost for high volume
            elif volume_ratio < 0.7:
                adjusted_score *= 0.9  # Reduce for low volume

        # Volatility context
        if 'volatility' in context:
            volatility = context['volatility']
            if volatility > 2.0:
                adjusted_score *= 0.9  # Reduce in high volatility
            elif volatility < 0.5:
                adjusted_score *= 1.05  # Slight boost in low volatility

        # Trend context
        if 'trend_strength' in context:
            trend_strength = context['trend_strength']
            # Boost breakout patterns in strong trends
            breakout_patterns = [p for p in patterns if p.pattern_type == PatternType.BREAKOUT]
            if breakout_patterns and abs(trend_strength) > 0.7:
                adjusted_score *= 1.15

        return adjusted_score


# Alias for backward compatibility
PatternRecognition = PatternRecognitionEngine
