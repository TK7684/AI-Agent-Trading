"""
Confluence Scoring and Signal Generation System

This module implements weighted confluence scoring that combines technical indicators,
pattern recognition, and LLM analysis to generate trading signals with confidence
calibration and market regime awareness.
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

import numpy as np
from scipy import stats

from .enums import Direction, MarketRegime, Timeframe
from .market_data import MarketBar
from .patterns import PatternCollection, PatternHit
from .signals import LLMAnalysis, Signal, TimeframeAnalysis
from .technical_indicators import IndicatorEngine

logger = logging.getLogger(__name__)


@dataclass
class ConfluenceWeights:
    """Weights for different confluence components."""

    # Technical indicator weights
    trend_weight: float = 0.25
    momentum_weight: float = 0.20
    volatility_weight: float = 0.15
    volume_weight: float = 0.10

    # Pattern weights
    pattern_weight: float = 0.15

    # LLM analysis weight
    llm_weight: float = 0.15

    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = (self.trend_weight + self.momentum_weight + self.volatility_weight +
                self.volume_weight + self.pattern_weight + self.llm_weight)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass
class MarketRegimeData:
    """Market regime detection data."""

    regime: MarketRegime
    confidence: float
    trend_strength: float
    volatility_level: float
    volume_trend: float
    regime_duration: int  # bars since regime started

    # Supporting metrics
    ema_alignment: float  # How aligned are EMAs (20, 50, 200)
    price_momentum: float  # Recent price momentum
    volatility_percentile: float  # Current volatility vs historical


@dataclass
class ConfluenceScore:
    """Confluence scoring result."""

    total_score: float  # 0-100
    direction: Direction
    confidence: float  # 0-1, calibrated confidence

    # Component scores
    trend_score: float
    momentum_score: float
    volatility_score: float
    volume_score: float
    pattern_score: float
    llm_score: float

    # Regime adjustments
    regime_multiplier: float
    timeframe_weights: dict[Timeframe, float]

    # Reasoning
    key_factors: list[str]
    risk_factors: list[str]


class ConfidenceCalibrator:
    """Bayesian confidence calibration using rolling windows."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.predictions = deque(maxlen=window_size)
        self.outcomes = deque(maxlen=window_size)

    def add_prediction(self, predicted_confidence: float, actual_outcome: bool):
        """Add a prediction-outcome pair for calibration."""
        self.predictions.append(predicted_confidence)
        self.outcomes.append(1.0 if actual_outcome else 0.0)

    def calibrate_confidence(self, raw_confidence: float) -> float:
        """Calibrate confidence using Platt scaling."""
        if len(self.predictions) < 10:
            return raw_confidence  # Not enough data for calibration

        try:
            # Use quantile-based calibration
            predictions = np.array(self.predictions)
            outcomes = np.array(self.outcomes)

            # Find similar confidence predictions
            tolerance = 0.1
            mask = np.abs(predictions - raw_confidence) <= tolerance

            if np.sum(mask) < 5:
                # Fallback to global calibration
                return self._global_calibration(raw_confidence, predictions, outcomes)

            # Local calibration
            local_outcomes = outcomes[mask]
            calibrated = np.mean(local_outcomes)

            # Smooth with global estimate
            global_cal = self._global_calibration(raw_confidence, predictions, outcomes)
            alpha = min(0.7, np.sum(mask) / 20)  # More local weight with more data

            return alpha * calibrated + (1 - alpha) * global_cal

        except Exception as e:
            logger.warning(f"Confidence calibration failed: {e}")
            return raw_confidence

    def _global_calibration(self, raw_confidence: float, predictions: np.ndarray, outcomes: np.ndarray) -> float:
        """Global Platt scaling calibration."""
        try:
            # Fit sigmoid: p = 1 / (1 + exp(A * score + B))

            def sigmoid(x, a, b):
                return 1 / (1 + np.exp(a * x + b))

            def loss(params):
                a, b = params
                pred_probs = sigmoid(predictions, a, b)
                return -np.sum(outcomes * np.log(pred_probs + 1e-15) +
                              (1 - outcomes) * np.log(1 - pred_probs + 1e-15))

            # Simple linear calibration as fallback
            slope, intercept, _, _, _ = stats.linregress(predictions, outcomes)
            calibrated = slope * raw_confidence + intercept
            return np.clip(calibrated, 0.01, 0.99)

        except Exception:
            return raw_confidence


class MarketRegimeDetector:
    """Market regime detection using multiple indicators."""

    def __init__(self, lookback_period: int = 50):
        self.lookback_period = lookback_period

    def detect_regime(self, data: list[MarketBar], indicators: dict[str, Any]) -> MarketRegimeData:
        """Detect current market regime."""
        if len(data) < self.lookback_period:
            return MarketRegimeData(
                regime=MarketRegime.SIDEWAYS,
                confidence=0.5,
                trend_strength=0.0,
                volatility_level=0.5,
                volume_trend=0.0,
                regime_duration=0,
                ema_alignment=0.0,
                price_momentum=0.0,
                volatility_percentile=0.5
            )

        recent_data = data[-self.lookback_period:]

        # Calculate regime indicators
        trend_strength = self._calculate_trend_strength(recent_data, indicators)
        volatility_level = self._calculate_volatility_level(recent_data, indicators)
        volume_trend = self._calculate_volume_trend(recent_data)
        ema_alignment = self._calculate_ema_alignment(indicators)
        price_momentum = self._calculate_price_momentum(recent_data)
        volatility_percentile = self._calculate_volatility_percentile(data, recent_data)

        # Determine regime
        regime, confidence = self._classify_regime(
            trend_strength, volatility_level, volume_trend, ema_alignment
        )

        # Estimate regime duration (simplified)
        regime_duration = self._estimate_regime_duration(data, regime)

        return MarketRegimeData(
            regime=regime,
            confidence=confidence,
            trend_strength=trend_strength,
            volatility_level=volatility_level,
            volume_trend=volume_trend,
            regime_duration=regime_duration,
            ema_alignment=ema_alignment,
            price_momentum=price_momentum,
            volatility_percentile=volatility_percentile
        )

    def _calculate_trend_strength(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate trend strength (-1 to 1)."""
        try:
            # Use EMA alignment and price action
            ema_20 = indicators.get('ema_20', [])
            ema_50 = indicators.get('ema_50', [])
            ema_200 = indicators.get('ema_200', [])

            if not all([ema_20, ema_50, ema_200]):
                return 0.0

            # Get latest values
            ema_20_val = ema_20[-1].value
            ema_50_val = ema_50[-1].value
            ema_200_val = ema_200[-1].value
            current_price = float(data[-1].close)

            # Calculate trend score based on EMA ordering
            if current_price > ema_20_val > ema_50_val > ema_200_val:
                trend_score = 1.0  # Strong uptrend
            elif current_price < ema_20_val < ema_50_val < ema_200_val:
                trend_score = -1.0  # Strong downtrend
            else:
                # Mixed signals - calculate partial score
                above_20 = 1 if current_price > ema_20_val else -1
                above_50 = 1 if current_price > ema_50_val else -1
                above_200 = 1 if current_price > ema_200_val else -1
                trend_score = (above_20 + above_50 + above_200) / 3

            # Adjust by recent price momentum
            if len(data) >= 10:
                recent_change = (float(data[-1].close) - float(data[-10].close)) / float(data[-10].close)
                momentum_factor = np.tanh(recent_change * 10)  # Scale and bound
                trend_score = 0.7 * trend_score + 0.3 * momentum_factor

            return np.clip(trend_score, -1.0, 1.0)

        except Exception as e:
            logger.warning(f"Error calculating trend strength: {e}")
            return 0.0

    def _calculate_volatility_level(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate volatility level (0 to 1)."""
        try:
            atr_results = indicators.get('atr', [])
            if not atr_results:
                # Fallback: calculate simple volatility
                closes = [float(bar.close) for bar in data[-20:]]
                returns = np.diff(closes) / closes[:-1]
                volatility = np.std(returns) * np.sqrt(252)  # Annualized
                return np.clip(volatility * 2, 0, 1)  # Scale to 0-1

            current_atr = atr_results[-1].value
            current_price = float(data[-1].close)

            # ATR as percentage of price
            atr_pct = current_atr / current_price

            # Scale to 0-1 (typical ATR% ranges from 0.5% to 5%)
            volatility_level = np.clip(atr_pct * 40, 0, 1)

            return volatility_level

        except Exception as e:
            logger.warning(f"Error calculating volatility level: {e}")
            return 0.5

    def _calculate_volume_trend(self, data: list[MarketBar]) -> float:
        """Calculate volume trend (-1 to 1)."""
        try:
            if len(data) < 20:
                return 0.0

            volumes = [float(bar.volume) for bar in data]

            # Compare recent volume to historical average
            recent_volume = np.mean(volumes[-10:])
            historical_volume = np.mean(volumes[-30:-10])

            if historical_volume == 0:
                return 0.0

            volume_ratio = recent_volume / historical_volume

            # Convert to trend score
            trend_score = np.tanh((volume_ratio - 1) * 2)  # Scale and bound

            return np.clip(trend_score, -1.0, 1.0)

        except Exception as e:
            logger.warning(f"Error calculating volume trend: {e}")
            return 0.0

    def _calculate_ema_alignment(self, indicators: dict[str, Any]) -> float:
        """Calculate EMA alignment score (-1 to 1)."""
        try:
            ema_20 = indicators.get('ema_20', [])
            ema_50 = indicators.get('ema_50', [])
            ema_200 = indicators.get('ema_200', [])

            if not all([ema_20, ema_50, ema_200]):
                return 0.0

            ema_20_val = ema_20[-1].value
            ema_50_val = ema_50[-1].value
            ema_200_val = ema_200[-1].value

            # Perfect bullish alignment: 20 > 50 > 200
            # Perfect bearish alignment: 20 < 50 < 200

            if ema_20_val > ema_50_val > ema_200_val:
                return 1.0  # Perfect bullish alignment
            elif ema_20_val < ema_50_val < ema_200_val:
                return -1.0  # Perfect bearish alignment
            else:
                # Partial alignment
                score = 0.0
                if ema_20_val > ema_50_val:
                    score += 0.5
                else:
                    score -= 0.5

                if ema_50_val > ema_200_val:
                    score += 0.5
                else:
                    score -= 0.5

                return score

        except Exception as e:
            logger.warning(f"Error calculating EMA alignment: {e}")
            return 0.0

    def _calculate_price_momentum(self, data: list[MarketBar]) -> float:
        """Calculate recent price momentum (-1 to 1)."""
        try:
            if len(data) < 10:
                return 0.0

            # Calculate momentum over different periods
            periods = [5, 10, 20]
            momentum_scores = []

            for period in periods:
                if len(data) >= period:
                    start_price = float(data[-period].close)
                    end_price = float(data[-1].close)
                    momentum = (end_price - start_price) / start_price
                    momentum_scores.append(np.tanh(momentum * 10))  # Scale and bound

            if momentum_scores:
                return np.mean(momentum_scores)
            else:
                return 0.0

        except Exception as e:
            logger.warning(f"Error calculating price momentum: {e}")
            return 0.0

    def _calculate_volatility_percentile(self, all_data: list[MarketBar], recent_data: list[MarketBar]) -> float:
        """Calculate current volatility percentile."""
        try:
            if len(all_data) < 100:
                return 0.5

            # Calculate historical volatilities
            historical_vols = []
            window = 20

            for i in range(window, len(all_data) - len(recent_data)):
                window_data = all_data[i-window:i]
                closes = [float(bar.close) for bar in window_data]
                returns = np.diff(closes) / closes[:-1]
                vol = np.std(returns)
                historical_vols.append(vol)

            # Current volatility
            recent_closes = [float(bar.close) for bar in recent_data[-window:]]
            recent_returns = np.diff(recent_closes) / recent_closes[:-1]
            current_vol = np.std(recent_returns)

            # Calculate percentile
            percentile = stats.percentileofscore(historical_vols, current_vol) / 100

            return np.clip(percentile, 0.0, 1.0)

        except Exception as e:
            logger.warning(f"Error calculating volatility percentile: {e}")
            return 0.5

    def _classify_regime(self, trend_strength: float, volatility_level: float,
                        volume_trend: float, ema_alignment: float) -> tuple[MarketRegime, float]:
        """Classify market regime based on indicators."""

        # Combine indicators for regime classification
        trend_score = (trend_strength + ema_alignment) / 2

        # Regime thresholds
        bull_threshold = 0.3
        bear_threshold = -0.3

        if trend_score > bull_threshold:
            regime = MarketRegime.BULL
            confidence = min(0.95, 0.5 + abs(trend_score))
        elif trend_score < bear_threshold:
            regime = MarketRegime.BEAR
            confidence = min(0.95, 0.5 + abs(trend_score))
        else:
            regime = MarketRegime.SIDEWAYS
            confidence = 0.5 + (1 - abs(trend_score)) * 0.3

        # Adjust confidence based on volatility and volume
        if volatility_level > 0.7:  # High volatility reduces confidence
            confidence *= 0.8

        if abs(volume_trend) > 0.5:  # Strong volume trend increases confidence
            confidence = min(0.95, confidence * 1.2)

        return regime, confidence

    def _estimate_regime_duration(self, data: list[MarketBar], current_regime: MarketRegime) -> int:
        """Estimate how long current regime has been active."""
        # Simplified implementation - would need regime history in practice
        return min(len(data), 20)  # Placeholder


class ConfluenceScorer:
    """Main confluence scoring engine."""

    def __init__(self, weights: Optional[ConfluenceWeights] = None):
        self.weights = weights or ConfluenceWeights()
        self.regime_detector = MarketRegimeDetector()
        self.confidence_calibrator = ConfidenceCalibrator()
        self.indicator_engine = IndicatorEngine()

    def calculate_confluence_score(self,
                                 symbol: str,
                                 timeframe_data: dict[Timeframe, list[MarketBar]],
                                 patterns: dict[Timeframe, PatternCollection],
                                 llm_analysis: Optional[LLMAnalysis] = None) -> ConfluenceScore:
        """Calculate weighted confluence score across timeframes."""

        try:
            # Calculate indicators for each timeframe
            timeframe_indicators = {}
            timeframe_scores = {}

            for tf, data in timeframe_data.items():
                if len(data) < 50:
                    continue

                indicators = self.indicator_engine.calculate_all_indicators(data)
                timeframe_indicators[tf] = indicators

                # Calculate individual component scores
                trend_score = self._calculate_trend_score(data, indicators)
                momentum_score = self._calculate_momentum_score(data, indicators)
                volatility_score = self._calculate_volatility_score(data, indicators)
                volume_score = self._calculate_volume_score(data, indicators)
                pattern_score = self._calculate_pattern_score(patterns.get(tf))

                timeframe_scores[tf] = {
                    'trend': trend_score,
                    'momentum': momentum_score,
                    'volatility': volatility_score,
                    'volume': volume_score,
                    'pattern': pattern_score
                }

            if not timeframe_scores:
                raise ValueError("No valid timeframe data for scoring")

            # Detect market regime using primary timeframe
            primary_tf = self._get_primary_timeframe(timeframe_data)
            regime_data = self.regime_detector.detect_regime(
                timeframe_data[primary_tf],
                timeframe_indicators[primary_tf]
            )

            # Calculate dynamic timeframe weights
            timeframe_weights = self._calculate_timeframe_weights(
                timeframe_data, regime_data
            )

            # Calculate weighted scores
            weighted_scores = self._calculate_weighted_scores(
                timeframe_scores, timeframe_weights
            )

            # Add LLM score
            llm_score = self._calculate_llm_score(llm_analysis) if llm_analysis else 0.0

            # Apply regime multiplier
            regime_multiplier = self._get_regime_multiplier(regime_data)

            # Calculate total confluence score
            total_score = (
                weighted_scores['trend'] * self.weights.trend_weight +
                weighted_scores['momentum'] * self.weights.momentum_weight +
                weighted_scores['volatility'] * self.weights.volatility_weight +
                weighted_scores['volume'] * self.weights.volume_weight +
                weighted_scores['pattern'] * self.weights.pattern_weight +
                llm_score * self.weights.llm_weight
            ) * regime_multiplier

            # Determine direction
            direction = Direction.LONG if total_score > 0 else Direction.SHORT
            total_score = abs(total_score)  # Convert to 0-100 scale

            # Calculate raw confidence
            raw_confidence = min(0.95, total_score / 100 + 0.1)

            # Calibrate confidence
            calibrated_confidence = self.confidence_calibrator.calibrate_confidence(raw_confidence)

            # Generate reasoning
            key_factors, risk_factors = self._generate_reasoning(
                weighted_scores, regime_data, llm_analysis, timeframe_weights
            )

            return ConfluenceScore(
                total_score=total_score,
                direction=direction,
                confidence=calibrated_confidence,
                trend_score=weighted_scores['trend'],
                momentum_score=weighted_scores['momentum'],
                volatility_score=weighted_scores['volatility'],
                volume_score=weighted_scores['volume'],
                pattern_score=weighted_scores['pattern'],
                llm_score=llm_score,
                regime_multiplier=regime_multiplier,
                timeframe_weights=timeframe_weights,
                key_factors=key_factors,
                risk_factors=risk_factors
            )

        except Exception as e:
            logger.error(f"Error calculating confluence score: {e}")
            # Return neutral score on error
            return ConfluenceScore(
                total_score=0.0,
                direction=Direction.LONG,
                confidence=0.1,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_score=0.0,
                volume_score=0.0,
                pattern_score=0.0,
                llm_score=0.0,
                regime_multiplier=1.0,
                timeframe_weights={},
                key_factors=["Error in calculation"],
                risk_factors=["Calculation error - low confidence"]
            )

    def _get_primary_timeframe(self, timeframe_data: dict[Timeframe, list[MarketBar]]) -> Timeframe:
        """Get primary timeframe for regime detection."""
        # Prefer 1h, fallback to available timeframes
        if Timeframe.H1 in timeframe_data:
            return Timeframe.H1
        elif Timeframe.H4 in timeframe_data:
            return Timeframe.H4
        elif Timeframe.D1 in timeframe_data:
            return Timeframe.D1
        else:
            return list(timeframe_data.keys())[0]

    def _calculate_trend_score(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate trend score (-10 to 10)."""
        try:
            score = 0.0

            # EMA trend analysis
            ema_20 = indicators.get('ema_20', [])
            ema_50 = indicators.get('ema_50', [])
            ema_200 = indicators.get('ema_200', [])

            if ema_20 and ema_50 and ema_200:
                current_price = float(data[-1].close)
                ema_20_val = ema_20[-1].value
                ema_50_val = ema_50[-1].value
                ema_200_val = ema_200[-1].value

                # EMA alignment score
                if current_price > ema_20_val > ema_50_val > ema_200_val:
                    score += 4.0  # Strong uptrend
                elif current_price < ema_20_val < ema_50_val < ema_200_val:
                    score -= 4.0  # Strong downtrend
                else:
                    # Partial alignment
                    if current_price > ema_20_val:
                        score += 1.0
                    else:
                        score -= 1.0

                    if ema_20_val > ema_50_val:
                        score += 1.0
                    else:
                        score -= 1.0

                    if ema_50_val > ema_200_val:
                        score += 1.0
                    else:
                        score -= 1.0

            # MACD trend confirmation
            macd_results = indicators.get('macd', [])
            if macd_results:
                latest_macd = macd_results[-1]
                if latest_macd.value > latest_macd.signal:
                    score += 2.0 if latest_macd.histogram > 0 else 1.0
                else:
                    score -= 2.0 if latest_macd.histogram < 0 else 1.0

            # Price momentum
            if len(data) >= 20:
                recent_change = (float(data[-1].close) - float(data[-20].close)) / float(data[-20].close)
                momentum_score = np.tanh(recent_change * 10) * 3  # Scale to ±3
                score += momentum_score

            return np.clip(score, -10.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating trend score: {e}")
            return 0.0

    def _calculate_momentum_score(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate momentum score (-10 to 10)."""
        try:
            score = 0.0

            # RSI momentum
            rsi_results = indicators.get('rsi', [])
            if rsi_results:
                rsi_value = rsi_results[-1].value
                if rsi_value > 70:
                    score += 2.0  # Overbought momentum
                elif rsi_value > 60:
                    score += 1.0
                elif rsi_value < 30:
                    score -= 2.0  # Oversold momentum
                elif rsi_value < 40:
                    score -= 1.0

            # Stochastic momentum
            stoch_results = indicators.get('stochastic', [])
            if stoch_results:
                stoch = stoch_results[-1]
                if stoch.k_percent > 80:
                    score += 1.5
                elif stoch.k_percent < 20:
                    score -= 1.5

                # Stochastic crossover
                if len(stoch_results) >= 2:
                    prev_stoch = stoch_results[-2]
                    if stoch.k_percent > stoch.d_percent and prev_stoch.k_percent <= prev_stoch.d_percent:
                        score += 2.0  # Bullish crossover
                    elif stoch.k_percent < stoch.d_percent and prev_stoch.k_percent >= prev_stoch.d_percent:
                        score -= 2.0  # Bearish crossover

            # CCI momentum
            cci_results = indicators.get('cci', [])
            if cci_results:
                cci_value = cci_results[-1].value
                if cci_value > 100:
                    score += 1.5
                elif cci_value < -100:
                    score -= 1.5

            # MFI momentum
            mfi_results = indicators.get('mfi', [])
            if mfi_results:
                mfi_value = mfi_results[-1].value
                if mfi_value > 80:
                    score += 1.0
                elif mfi_value < 20:
                    score -= 1.0

            return np.clip(score, -10.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating momentum score: {e}")
            return 0.0

    def _calculate_volatility_score(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate volatility score (0 to 10)."""
        try:
            score = 0.0

            # ATR volatility
            atr_results = indicators.get('atr', [])
            if atr_results and len(atr_results) >= 20:
                current_atr = atr_results[-1].value
                avg_atr = np.mean([r.value for r in atr_results[-20:]])

                if current_atr > avg_atr * 1.5:
                    score += 3.0  # High volatility
                elif current_atr > avg_atr * 1.2:
                    score += 2.0
                elif current_atr < avg_atr * 0.8:
                    score += 1.0  # Low volatility can be good for trend following

            # Bollinger Bands volatility
            bb_results = indicators.get('bollinger_bands', [])
            if bb_results:
                latest_bb = bb_results[-1]
                current_price = float(data[-1].close)

                # Band position
                band_width = latest_bb.upper - latest_bb.lower
                if band_width > 0:
                    position = (current_price - latest_bb.lower) / band_width

                    if position > 0.8 or position < 0.2:
                        score += 2.0  # Near bands - potential reversal or breakout
                    elif 0.4 <= position <= 0.6:
                        score += 1.0  # Middle of bands - neutral

            # Price range analysis
            if len(data) >= 10:
                recent_highs = [float(bar.high) for bar in data[-10:]]
                recent_lows = [float(bar.low) for bar in data[-10:]]
                range_expansion = (max(recent_highs) - min(recent_lows)) / float(data[-10].close)

                if range_expansion > 0.05:  # 5% range
                    score += 2.0
                elif range_expansion > 0.03:  # 3% range
                    score += 1.0

            return np.clip(score, 0.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating volatility score: {e}")
            return 0.0

    def _calculate_volume_score(self, data: list[MarketBar], indicators: dict[str, Any]) -> float:
        """Calculate volume score (0 to 10)."""
        try:
            score = 0.0

            if len(data) < 20:
                return 0.0

            # Volume trend analysis
            recent_volumes = [float(bar.volume) for bar in data[-10:]]
            historical_volumes = [float(bar.volume) for bar in data[-30:-10]]

            avg_recent = np.mean(recent_volumes)
            avg_historical = np.mean(historical_volumes)

            if avg_historical > 0:
                volume_ratio = avg_recent / avg_historical

                if volume_ratio > 1.5:
                    score += 3.0  # High volume
                elif volume_ratio > 1.2:
                    score += 2.0
                elif volume_ratio > 1.0:
                    score += 1.0

            # Volume profile analysis
            volume_profile = indicators.get('volume_profile')
            if volume_profile:
                current_price = float(data[-1].close)

                # Distance from POC (Point of Control)
                poc_distance = abs(current_price - volume_profile.poc) / current_price

                if poc_distance < 0.01:  # Within 1% of POC
                    score += 2.0
                elif poc_distance < 0.02:  # Within 2% of POC
                    score += 1.0

                # Value area analysis
                if volume_profile.value_area_low <= current_price <= volume_profile.value_area_high:
                    score += 1.0  # Within value area

            # Volume confirmation with price movement
            if len(data) >= 2:
                price_change = float(data[-1].close) - float(data[-2].close)
                volume_change = float(data[-1].volume) - float(data[-2].volume)

                # Volume confirms price movement
                if (price_change > 0 and volume_change > 0) or (price_change < 0 and volume_change > 0):
                    score += 1.0

            return np.clip(score, 0.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating volume score: {e}")
            return 0.0

    def _calculate_pattern_score(self, pattern_collection: Optional[PatternCollection]) -> float:
        """Calculate pattern score (-10 to 10)."""
        try:
            if not pattern_collection or not pattern_collection.patterns:
                return 0.0

            score = 0.0

            for pattern in pattern_collection.patterns:
                # Base score from pattern confidence and strength
                pattern_score = pattern.confidence * pattern.strength

                # Pattern type weighting
                from .enums import PatternType
                if pattern.pattern_type in [PatternType.BREAKOUT, PatternType.TREND_REVERSAL]:
                    pattern_score *= 1.5  # Higher weight for breakout patterns
                elif pattern.pattern_type in [PatternType.PIN_BAR, PatternType.ENGULFING]:
                    pattern_score *= 1.2  # Moderate weight for reversal patterns

                # Historical performance weighting
                if pattern.historical_win_rate:
                    performance_multiplier = 0.5 + pattern.historical_win_rate
                    pattern_score *= performance_multiplier

                score += pattern_score

            # Normalize by number of patterns (avoid over-weighting)
            if len(pattern_collection.patterns) > 1:
                score = score / np.sqrt(len(pattern_collection.patterns))

            return np.clip(score, -10.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating pattern score: {e}")
            return 0.0

    def _calculate_llm_score(self, llm_analysis: LLMAnalysis) -> float:
        """Calculate LLM score (-10 to 10)."""
        try:
            # Combine bullish and bearish scores
            net_score = llm_analysis.bullish_score - llm_analysis.bearish_score

            # Weight by confidence
            weighted_score = net_score * llm_analysis.confidence

            # Scale to -10 to 10 range
            scaled_score = weighted_score  # Already in 0-10 range

            return np.clip(scaled_score, -10.0, 10.0)

        except Exception as e:
            logger.warning(f"Error calculating LLM score: {e}")
            return 0.0

    def _calculate_timeframe_weights(self, timeframe_data: dict[Timeframe, list[MarketBar]],
                                   regime_data: MarketRegimeData) -> dict[Timeframe, float]:
        """Calculate dynamic timeframe weights based on volatility and regime."""
        try:
            weights = {}
            total_weight = 0.0

            # Base weights by timeframe
            base_weights = {
                Timeframe.M15: 0.15,
                Timeframe.H1: 0.35,
                Timeframe.H4: 0.35,
                Timeframe.D1: 0.15
            }

            for tf in timeframe_data.keys():
                if tf not in base_weights:
                    continue

                weight = base_weights[tf]

                # Adjust based on market regime
                if regime_data.regime == MarketRegime.BULL:
                    # In bull markets, favor longer timeframes
                    if tf in [Timeframe.H4, Timeframe.D1]:
                        weight *= 1.2
                    else:
                        weight *= 0.9
                elif regime_data.regime == MarketRegime.BEAR:
                    # In bear markets, favor shorter timeframes for quick reactions
                    if tf in [Timeframe.M15, Timeframe.H1]:
                        weight *= 1.2
                    else:
                        weight *= 0.9
                # Sideways markets use base weights

                # Adjust based on volatility
                if regime_data.volatility_level > 0.7:
                    # High volatility - favor shorter timeframes
                    if tf in [Timeframe.M15, Timeframe.H1]:
                        weight *= 1.1
                    else:
                        weight *= 0.95
                elif regime_data.volatility_level < 0.3:
                    # Low volatility - favor longer timeframes
                    if tf in [Timeframe.H4, Timeframe.D1]:
                        weight *= 1.1
                    else:
                        weight *= 0.95

                weights[tf] = weight
                total_weight += weight

            # Normalize weights
            if total_weight > 0:
                for tf in weights:
                    weights[tf] /= total_weight

            return weights

        except Exception as e:
            logger.warning(f"Error calculating timeframe weights: {e}")
            # Return equal weights as fallback
            num_timeframes = len(timeframe_data)
            return {tf: 1.0 / num_timeframes for tf in timeframe_data.keys()}

    def _calculate_weighted_scores(self, timeframe_scores: dict[Timeframe, dict[str, float]],
                                 timeframe_weights: dict[Timeframe, float]) -> dict[str, float]:
        """Calculate weighted scores across timeframes."""
        try:
            weighted_scores = {
                'trend': 0.0,
                'momentum': 0.0,
                'volatility': 0.0,
                'volume': 0.0,
                'pattern': 0.0
            }

            for tf, scores in timeframe_scores.items():
                weight = timeframe_weights.get(tf, 0.0)

                for component, score in scores.items():
                    weighted_scores[component] += score * weight

            return weighted_scores

        except Exception as e:
            logger.warning(f"Error calculating weighted scores: {e}")
            return {k: 0.0 for k in ['trend', 'momentum', 'volatility', 'volume', 'pattern']}

    def _get_regime_multiplier(self, regime_data: MarketRegimeData) -> float:
        """Get regime-based score multiplier."""
        try:
            base_multiplier = 1.0

            # Adjust based on regime confidence
            confidence_factor = 0.8 + (regime_data.confidence * 0.4)  # 0.8 to 1.2

            # Adjust based on regime type and trend strength
            if regime_data.regime == MarketRegime.BULL:
                trend_factor = 1.0 + (regime_data.trend_strength * 0.2)  # Up to 1.2x
            elif regime_data.regime == MarketRegime.BEAR:
                trend_factor = 1.0 + (abs(regime_data.trend_strength) * 0.2)  # Up to 1.2x
            else:  # SIDEWAYS
                trend_factor = 0.9  # Reduce confidence in sideways markets

            # Adjust based on volatility
            if regime_data.volatility_level > 0.8:
                volatility_factor = 0.9  # High volatility reduces confidence
            elif regime_data.volatility_level < 0.2:
                volatility_factor = 0.95  # Very low volatility slightly reduces confidence
            else:
                volatility_factor = 1.0

            multiplier = base_multiplier * confidence_factor * trend_factor * volatility_factor

            return np.clip(multiplier, 0.5, 1.5)

        except Exception as e:
            logger.warning(f"Error calculating regime multiplier: {e}")
            return 1.0

    def _generate_reasoning(self, weighted_scores: dict[str, float],
                          regime_data: MarketRegimeData,
                          llm_analysis: Optional[LLMAnalysis],
                          timeframe_weights: dict[Timeframe, float]) -> tuple[list[str], list[str]]:
        """Generate human-readable reasoning for the signal."""
        try:
            key_factors = []
            risk_factors = []

            # Analyze component scores
            strong_components = []
            weak_components = []

            for component, score in weighted_scores.items():
                if abs(score) > 5:
                    strong_components.append((component, score))
                elif abs(score) < 2:
                    weak_components.append((component, score))

            # Key factors from strong components
            for component, score in strong_components:
                direction = "bullish" if score > 0 else "bearish"
                key_factors.append(f"Strong {direction} {component} signal ({score:.1f})")

            # Market regime factor
            key_factors.append(f"Market regime: {regime_data.regime.value} "
                             f"(confidence: {regime_data.confidence:.2f})")

            # Timeframe analysis
            dominant_tf = max(timeframe_weights.items(), key=lambda x: x[1])
            key_factors.append(f"Primary timeframe: {dominant_tf[0].value} "
                             f"(weight: {dominant_tf[1]:.2f})")

            # LLM insights
            if llm_analysis:
                if llm_analysis.key_insights:
                    key_factors.extend(llm_analysis.key_insights[:2])  # Top 2 insights

            # Risk factors from weak components
            for component, score in weak_components:
                risk_factors.append(f"Weak {component} signal ({score:.1f})")

            # Volatility risk
            if regime_data.volatility_level > 0.8:
                risk_factors.append(f"High volatility ({regime_data.volatility_level:.2f})")

            # Regime risks
            if regime_data.confidence < 0.6:
                risk_factors.append(f"Uncertain market regime (confidence: {regime_data.confidence:.2f})")

            # LLM risk factors
            if llm_analysis and llm_analysis.risk_factors:
                risk_factors.extend(llm_analysis.risk_factors[:2])  # Top 2 risk factors

            return key_factors[:5], risk_factors[:5]  # Limit to top 5 each

        except Exception as e:
            logger.warning(f"Error generating reasoning: {e}")
            return ["Analysis completed"], ["Standard market risks apply"]

    def update_confidence_calibration(self, predicted_confidence: float, actual_outcome: bool):
        """Update confidence calibration with new outcome."""
        self.confidence_calibrator.add_prediction(predicted_confidence, actual_outcome)


class SignalGenerator:
    """Signal generation with confluence scoring."""

    def __init__(self, confluence_scorer: Optional[ConfluenceScorer] = None):
        self.confluence_scorer = confluence_scorer or ConfluenceScorer()

    def generate_signal(self,
                       symbol: str,
                       timeframe_data: dict[Timeframe, list[MarketBar]],
                       patterns: dict[Timeframe, PatternCollection],
                       llm_analysis: Optional[LLMAnalysis] = None) -> Optional[Signal]:
        """Generate trading signal with confluence analysis."""

        try:
            # Calculate confluence score
            confluence_score = self.confluence_scorer.calculate_confluence_score(
                symbol, timeframe_data, patterns, llm_analysis
            )

            # Filter low-confidence signals
            if confluence_score.confidence < 0.3 or confluence_score.total_score < 20:
                logger.info(f"Signal filtered: low confidence ({confluence_score.confidence:.2f}) "
                           f"or score ({confluence_score.total_score:.1f})")
                return None

            # Get primary timeframe data
            primary_tf = self._get_primary_timeframe(timeframe_data)
            primary_data = timeframe_data[primary_tf]

            # Create timeframe analyses
            timeframe_analyses = {}
            for tf, data in timeframe_data.items():
                if len(data) > 0:
                    analysis = self._create_timeframe_analysis(
                        tf, data, patterns.get(tf), confluence_score.timeframe_weights.get(tf, 0.0)
                    )
                    timeframe_analyses[tf] = analysis

            # Calculate price targets
            entry_price, stop_loss, take_profit = self._calculate_price_targets(
                primary_data, confluence_score.direction, patterns.get(primary_tf)
            )

            # Generate signal
            signal = Signal(
                signal_id=f"{symbol}_{primary_tf.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                symbol=symbol,
                timestamp=datetime.now(),
                direction=confluence_score.direction,
                confluence_score=confluence_score.total_score,
                confidence=confluence_score.confidence,
                market_regime=self.confluence_scorer.regime_detector.detect_regime(
                    primary_data, {}
                ).regime,
                primary_timeframe=primary_tf,
                timeframe_analysis=timeframe_analyses,
                patterns=self._get_relevant_patterns(patterns),
                llm_analysis=llm_analysis,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=self._generate_signal_reasoning(confluence_score),
                key_factors=confluence_score.key_factors,
                expires_at=datetime.now() + timedelta(hours=4)  # 4-hour expiry
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None

    def _get_primary_timeframe(self, timeframe_data: dict[Timeframe, list[MarketBar]]) -> Timeframe:
        """Get primary timeframe for signal generation."""
        # Same logic as confluence scorer
        if Timeframe.H1 in timeframe_data:
            return Timeframe.H1
        elif Timeframe.H4 in timeframe_data:
            return Timeframe.H4
        elif Timeframe.D1 in timeframe_data:
            return Timeframe.D1
        else:
            return list(timeframe_data.keys())[0]

    def _create_timeframe_analysis(self, timeframe: Timeframe, data: list[MarketBar],
                                 patterns: Optional[PatternCollection], weight: float) -> TimeframeAnalysis:
        """Create timeframe analysis object."""

        # Calculate basic scores (simplified)
        trend_score = 0.0
        momentum_score = 0.0
        volatility_score = 5.0  # Default mid-range
        volume_score = 5.0  # Default mid-range

        # Pattern analysis
        pattern_count = len(patterns.patterns) if patterns else 0
        strongest_pattern_confidence = max([p.confidence for p in patterns.patterns], default=0.0) if patterns else 0.0

        # Indicator counts (simplified)
        bullish_indicators = 5  # Placeholder
        bearish_indicators = 3  # Placeholder
        neutral_indicators = 2  # Placeholder

        return TimeframeAnalysis(
            timeframe=timeframe,
            timestamp=data[-1].timestamp,
            trend_score=trend_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            volume_score=volume_score,
            pattern_count=pattern_count,
            strongest_pattern_confidence=strongest_pattern_confidence,
            bullish_indicators=bullish_indicators,
            bearish_indicators=bearish_indicators,
            neutral_indicators=neutral_indicators,
            timeframe_weight=weight
        )

    def _calculate_price_targets(self, data: list[MarketBar], direction: Direction,
                               patterns: Optional[PatternCollection]) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Calculate entry, stop loss, and take profit levels."""
        try:
            current_price = data[-1].close

            # Simple ATR-based targets
            if len(data) >= 14:
                # Calculate simple ATR
                true_ranges = []
                for i in range(1, min(15, len(data))):
                    high_low = float(data[-i].high - data[-i].low)
                    high_close_prev = abs(float(data[-i].high - data[-i-1].close))
                    low_close_prev = abs(float(data[-i].low - data[-i-1].close))
                    true_ranges.append(max(high_low, high_close_prev, low_close_prev))

                atr = np.mean(true_ranges)
                atr_decimal = Decimal(str(atr))

                if direction == Direction.LONG:
                    entry_price = current_price
                    stop_loss = current_price - (atr_decimal * Decimal('2'))
                    take_profit = current_price + (atr_decimal * Decimal('3'))
                else:  # SHORT
                    entry_price = current_price
                    stop_loss = current_price + (atr_decimal * Decimal('2'))
                    take_profit = current_price - (atr_decimal * Decimal('3'))

                return entry_price, stop_loss, take_profit

            return current_price, None, None

        except Exception as e:
            logger.warning(f"Error calculating price targets: {e}")
            return data[-1].close, None, None

    def _get_relevant_patterns(self, patterns: dict[Timeframe, PatternCollection]) -> list[PatternHit]:
        """Get most relevant patterns across timeframes."""
        all_patterns = []

        for tf, pattern_collection in patterns.items():
            if pattern_collection and pattern_collection.patterns:
                # Get high-confidence patterns
                high_conf_patterns = [p for p in pattern_collection.patterns if p.confidence > 0.6]
                all_patterns.extend(high_conf_patterns[:2])  # Top 2 per timeframe

        # Sort by confidence and return top 5
        all_patterns.sort(key=lambda p: p.confidence, reverse=True)
        return all_patterns[:5]

    def _generate_signal_reasoning(self, confluence_score: ConfluenceScore) -> str:
        """Generate human-readable signal reasoning."""
        direction_text = "bullish" if confluence_score.direction == Direction.LONG else "bearish"

        reasoning = f"Generated {direction_text} signal with {confluence_score.total_score:.1f}% confluence score. "

        # Add top factors
        if confluence_score.key_factors:
            reasoning += f"Key factors: {', '.join(confluence_score.key_factors[:3])}. "

        # Add regime context
        reasoning += f"Market regime multiplier: {confluence_score.regime_multiplier:.2f}. "

        # Add confidence note
        reasoning += f"Calibrated confidence: {confluence_score.confidence:.2f}."

        return reasoning


# Alias for backward compatibility
ConfluenceScoring = ConfluenceScorer
