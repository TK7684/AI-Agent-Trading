"""
Enhanced Signal Quality System

This module provides advanced signal quality assessment, filtering,
and enhancement mechanisms for improved trading performance.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional

import numpy as np

from .enums import Direction, MarketRegime
from .patterns import PatternType
from .signals import Signal


@dataclass
class SignalQualityMetrics:
    """Comprehensive signal quality assessment."""

    # Core quality scores
    technical_strength: float  # 0-100: Technical indicator alignment
    pattern_clarity: float     # 0-100: Pattern definition clarity
    confluence_depth: float    # 0-100: Multi-timeframe agreement
    market_context_fit: float  # 0-100: Market regime alignment

    # Risk-adjusted quality
    risk_reward_quality: float  # 0-100: R:R ratio assessment
    volatility_adjustment: float  # 0-100: Volatility context
    timing_precision: float    # 0-100: Entry timing quality

    # Composite scores
    overall_quality: float     # 0-100: Weighted composite
    trading_grade: str        # A+, A, B+, B, C+, C, D, F

    # Supporting data
    quality_factors: list[str]  # Factors contributing to quality
    risk_factors: list[str]     # Factors reducing quality
    improvement_suggestions: list[str]  # How to improve signal


class EnhancedSignalFilter:
    """Advanced signal filtering with multiple quality layers."""

    def __init__(self):
        self.min_confluence_score = 30.0
        self.min_confidence = 0.4
        self.min_pattern_count = 2
        self.min_timeframe_agreement = 0.6
        self.max_risk_reward_ratio = 0.5  # Minimum 1:2 R:R

        # Quality thresholds
        self.quality_thresholds = {
            'A+': 90.0,  # Exceptional signals
            'A': 80.0,   # Excellent signals
            'B+': 70.0,  # Very good signals
            'B': 60.0,   # Good signals
            'C+': 50.0,  # Acceptable signals
            'C': 40.0,   # Marginal signals
            'D': 30.0,   # Poor signals
            'F': 0.0     # Failed signals
        }

    def assess_signal_quality(self, signal: Signal) -> SignalQualityMetrics:
        """Comprehensive signal quality assessment."""

        # Calculate individual quality components
        technical_strength = self._assess_technical_strength(signal)
        pattern_clarity = self._assess_pattern_clarity(signal)
        confluence_depth = self._assess_confluence_depth(signal)
        market_context_fit = self._assess_market_context(signal)
        risk_reward_quality = self._assess_risk_reward(signal)
        volatility_adjustment = self._assess_volatility_context(signal)
        timing_precision = self._assess_timing_precision(signal)

        # Calculate weighted composite score (enhanced for better quality assessment)
        weights = {
            'technical': 0.30,     # Increased weight for technical analysis
            'pattern': 0.25,       # Increased weight for pattern clarity
            'confluence': 0.20,
            'context': 0.15,
            'risk_reward': 0.07,   # Reduced weight
            'volatility': 0.02,    # Reduced weight
            'timing': 0.01         # Reduced weight
        }

        base_score = (
            technical_strength * weights['technical'] +
            pattern_clarity * weights['pattern'] +
            confluence_depth * weights['confluence'] +
            market_context_fit * weights['context'] +
            risk_reward_quality * weights['risk_reward'] +
            volatility_adjustment * weights['volatility'] +
            timing_precision * weights['timing']
        )

        # Quality enhancement bonus for high-confidence signals
        if signal.confidence >= 0.85:
            base_score *= 1.25  # 25% bonus for exceptional confidence
        elif signal.confidence >= 0.75:
            base_score *= 1.15  # 15% bonus for high confidence
        elif signal.confidence >= 0.65:
            base_score *= 1.05  # 5% bonus for good confidence

        overall_quality = min(100.0, base_score)

        # Determine trading grade
        trading_grade = self._get_trading_grade(overall_quality)

        # Generate quality factors and suggestions
        quality_factors = self._identify_quality_factors(signal, {
            'technical_strength': technical_strength,
            'pattern_clarity': pattern_clarity,
            'confluence_depth': confluence_depth,
            'market_context_fit': market_context_fit
        })

        risk_factors = self._identify_risk_factors(signal, {
            'risk_reward_quality': risk_reward_quality,
            'volatility_adjustment': volatility_adjustment,
            'timing_precision': timing_precision
        })

        improvement_suggestions = self._generate_improvement_suggestions(
            signal, overall_quality, trading_grade
        )

        return SignalQualityMetrics(
            technical_strength=technical_strength,
            pattern_clarity=pattern_clarity,
            confluence_depth=confluence_depth,
            market_context_fit=market_context_fit,
            risk_reward_quality=risk_reward_quality,
            volatility_adjustment=volatility_adjustment,
            timing_precision=timing_precision,
            overall_quality=overall_quality,
            trading_grade=trading_grade,
            quality_factors=quality_factors,
            risk_factors=risk_factors,
            improvement_suggestions=improvement_suggestions
        )

    def should_trade_signal(self, signal: Signal, quality_metrics: SignalQualityMetrics) -> bool:
        """Determine if signal meets trading quality standards."""

        # Minimum quality thresholds
        if quality_metrics.overall_quality < 50.0:  # Below C+ grade
            return False

        if quality_metrics.trading_grade in ['D', 'F']:
            return False

        # Technical requirements
        if signal.confidence < self.min_confidence:
            return False

        if signal.confluence_score < self.min_confluence_score:
            return False

        # Pattern requirements
        if len(signal.patterns) < self.min_pattern_count:
            return False

        # Risk/reward requirements
        if signal.risk_reward_ratio and signal.risk_reward_ratio < 2.0:
            return False

        return True

    def _assess_technical_strength(self, signal: Signal) -> float:
        """Assess technical indicator strength."""
        score = 0.0

        # Base confidence contribution (enhanced)
        score += signal.confidence * 60  # Increased base contribution

        # Timeframe analysis contribution (enhanced)
        if signal.timeframe_analysis:
            for tf_analysis in signal.timeframe_analysis.values():
                # Enhanced technical strength calculation
                trend_momentum = (tf_analysis.trend_score + tf_analysis.momentum_score + tf_analysis.volume_score) / 3
                score += max(0, trend_momentum) * tf_analysis.timeframe_weight * 20  # Further increased multiplier

        # Indicator alignment bonus
        total_indicators = 0
        aligned_indicators = 0

        for tf, indicators in signal.indicators.items():
            if hasattr(indicators, 'values'):
                for indicator_name, value in indicators.values.items():
                    total_indicators += 1
                    if self._is_indicator_aligned(indicator_name, value, signal.direction):
                        aligned_indicators += 1

        if total_indicators > 0:
            alignment_ratio = aligned_indicators / total_indicators
            score += alignment_ratio * 30  # Increased bonus

        return min(100.0, score)

    def _assess_pattern_clarity(self, signal: Signal) -> float:
        """Assess pattern clarity and definition."""
        if not signal.patterns:
            return 0.0

        score = 0.0
        pattern_weights = {
            PatternType.BREAKOUT: 1.5,  # Increased weight
            PatternType.DIVERGENCE: 1.3,  # Increased weight
            PatternType.SUPPORT_RESISTANCE: 1.0,
            PatternType.ENGULFING: 0.9,
            PatternType.PIN_BAR: 0.8,
            PatternType.DOJI: 0.6
        }

        total_weight = 0.0
        for pattern in signal.patterns:
            weight = pattern_weights.get(pattern.pattern_type, 1.0)
            score += pattern.confidence * pattern.strength * weight * 10
            total_weight += weight

        if total_weight > 0:
            score = score / total_weight

        # Bonus for multiple confirming patterns
        if len(signal.patterns) >= 3:
            score *= 1.1
        elif len(signal.patterns) >= 2:
            score *= 1.05

        return min(100.0, score)

    def _assess_confluence_depth(self, signal: Signal) -> float:
        """Assess multi-timeframe confluence depth."""
        if not signal.timeframe_analysis:
            return signal.confluence_score * 0.7  # Enhanced penalty for single timeframe

        # Count timeframes with strong signals (enhanced thresholds)
        strong_timeframes = 0
        total_timeframes = len(signal.timeframe_analysis)

        for tf_analysis in signal.timeframe_analysis.values():
            combined_score = (tf_analysis.trend_score + tf_analysis.momentum_score) / 2
            if combined_score > 4:  # Lowered threshold for more inclusive scoring
                strong_timeframes += 1

        if total_timeframes == 0:
            return 0.0

        agreement_ratio = strong_timeframes / total_timeframes
        base_score = signal.confluence_score * 1.2  # Enhanced base score

        # Boost for high agreement across timeframes
        if agreement_ratio >= 0.8:
            return min(100.0, base_score * 1.2)
        elif agreement_ratio >= 0.6:
            return min(100.0, base_score * 1.1)
        else:
            return base_score * 0.9

    def _assess_market_context(self, signal: Signal) -> float:
        """Assess market context alignment."""
        score = 50.0  # Base score

        # Market regime alignment
        if signal.market_regime == MarketRegime.BULL and signal.direction == Direction.LONG:
            score += 20
        elif signal.market_regime == MarketRegime.BEAR and signal.direction == Direction.SHORT:
            score += 20
        elif signal.market_regime == MarketRegime.SIDEWAYS:
            score += 5  # Neutral
        else:
            score -= 15  # Counter-trend penalty

        # LLM analysis contribution
        if signal.llm_analysis:
            if signal.llm_analysis.confidence > 0.7:
                score += 15
            elif signal.llm_analysis.confidence > 0.5:
                score += 10
            else:
                score += 5

        return min(100.0, max(0.0, score))

    def _assess_risk_reward(self, signal: Signal) -> float:
        """Assess risk/reward quality."""
        if not signal.risk_reward_ratio:
            return 30.0  # Default score when R:R not specified

        rr = signal.risk_reward_ratio

        if rr >= 3.0:
            return 100.0  # Excellent R:R
        elif rr >= 2.5:
            return 85.0   # Very good R:R
        elif rr >= 2.0:
            return 70.0   # Good R:R
        elif rr >= 1.5:
            return 50.0   # Acceptable R:R
        elif rr >= 1.0:
            return 30.0   # Poor R:R
        else:
            return 0.0    # Unacceptable R:R

    def _assess_volatility_context(self, signal: Signal) -> float:
        """Assess volatility context appropriateness."""
        score = 50.0  # Base score

        # Check if we have volatility data in timeframe analysis
        avg_volatility = 0.0
        count = 0

        for tf_analysis in signal.timeframe_analysis.values():
            if hasattr(tf_analysis, 'volatility_score'):
                avg_volatility += tf_analysis.volatility_score
                count += 1

        if count > 0:
            avg_volatility /= count

            # Optimal volatility range is 3-7
            if 3 <= avg_volatility <= 7:
                score += 30  # Optimal volatility
            elif 2 <= avg_volatility < 3 or 7 < avg_volatility <= 8:
                score += 15  # Good volatility
            elif avg_volatility < 2:
                score -= 20  # Too low volatility
            elif avg_volatility > 8:
                score -= 30  # Too high volatility

        return min(100.0, max(0.0, score))

    def _assess_timing_precision(self, signal: Signal) -> float:
        """Assess entry timing precision."""
        score = 50.0  # Base score

        # Check signal age (fresher is better)
        signal_age = datetime.now(UTC) - signal.timestamp
        age_minutes = signal_age.total_seconds() / 60

        if age_minutes <= 5:
            score += 30  # Very fresh
        elif age_minutes <= 15:
            score += 20  # Fresh
        elif age_minutes <= 60:
            score += 10  # Acceptable
        else:
            score -= 20  # Stale signal

        # Priority bonus
        if hasattr(signal, 'priority'):
            if signal.priority >= 4:
                score += 15
            elif signal.priority >= 3:
                score += 10
            elif signal.priority >= 2:
                score += 5

        return min(100.0, max(0.0, score))

    def _get_trading_grade(self, overall_quality: float) -> str:
        """Convert quality score to trading grade."""
        for grade, threshold in self.quality_thresholds.items():
            if overall_quality >= threshold:
                return grade
        return 'F'

    def _identify_quality_factors(self, signal: Signal, scores: dict[str, float]) -> list[str]:
        """Identify factors contributing to signal quality."""
        factors = []

        if scores['technical_strength'] >= 80:
            factors.append("Strong technical indicator alignment")

        if scores['pattern_clarity'] >= 75:
            factors.append("Clear and well-defined patterns")

        if scores['confluence_depth'] >= 70:
            factors.append("Strong multi-timeframe confluence")

        if signal.confidence >= 0.8:
            factors.append("High confidence signal")

        if signal.confluence_score >= 80:
            factors.append("Excellent confluence score")

        if len(signal.patterns) >= 3:
            factors.append("Multiple confirming patterns")

        if signal.risk_reward_ratio and signal.risk_reward_ratio >= 2.5:
            factors.append("Favorable risk/reward ratio")

        return factors

    def _identify_risk_factors(self, signal: Signal, scores: dict[str, float]) -> list[str]:
        """Identify factors that reduce signal quality."""
        factors = []

        if signal.confidence < 0.5:
            factors.append("Low confidence score")

        if signal.confluence_score < 40:
            factors.append("Weak confluence score")

        if len(signal.patterns) < 2:
            factors.append("Insufficient pattern confirmation")

        if scores['volatility_adjustment'] < 30:
            factors.append("Unfavorable volatility conditions")

        if scores['timing_precision'] < 40:
            factors.append("Poor entry timing")

        if signal.risk_reward_ratio and signal.risk_reward_ratio < 1.5:
            factors.append("Poor risk/reward ratio")

        return factors

    def _generate_improvement_suggestions(self, signal: Signal, quality: float, grade: str) -> list[str]:
        """Generate suggestions to improve signal quality."""
        suggestions = []

        if quality < 60:
            suggestions.append("Wait for stronger confluence before trading")

        if signal.confidence < 0.6:
            suggestions.append("Seek additional confirmation from indicators")

        if len(signal.patterns) < 3:
            suggestions.append("Look for more pattern confirmation")

        if not signal.timeframe_analysis or len(signal.timeframe_analysis) < 2:
            suggestions.append("Analyze multiple timeframes for better confluence")

        if not signal.risk_reward_ratio or signal.risk_reward_ratio < 2.0:
            suggestions.append("Improve risk/reward ratio to at least 1:2")

        if grade in ['C', 'D', 'F']:
            suggestions.append("Consider passing on this signal - quality too low")

        return suggestions

    def _is_indicator_aligned(self, indicator_name: str, value: float, direction: Direction) -> bool:
        """Check if indicator is aligned with signal direction."""
        bullish_indicators = ['rsi_oversold', 'macd_bullish', 'ema_bullish', 'bb_lower_touch']
        bearish_indicators = ['rsi_overbought', 'macd_bearish', 'ema_bearish', 'bb_upper_touch']

        if direction == Direction.LONG:
            return indicator_name.lower() in bullish_indicators or value > 50
        else:
            return indicator_name.lower() in bearish_indicators or value < 50


class AdvancedConfluenceEngine:
    """Enhanced confluence scoring with machine learning insights."""

    def __init__(self):
        self.signal_filter = EnhancedSignalFilter()
        self.pattern_weights = {
            PatternType.BREAKOUT: 1.3,
            PatternType.DIVERGENCE: 1.2,
            PatternType.SUPPORT_RESISTANCE: 1.1,
            PatternType.ENGULFING: 1.0,
            PatternType.PIN_BAR: 0.9,
            PatternType.DOJI: 0.7
        }

        # Timeframe importance weights (using string values)
        self.timeframe_weights = {
            "1d": 1.0,
            "4h": 0.8,
            "1h": 0.6,
            "15m": 0.4
        }

    def enhance_signal_quality(self, signal: Signal) -> tuple[Signal, SignalQualityMetrics]:
        """Enhance signal with advanced quality assessment."""

        # Assess current quality
        quality_metrics = self.signal_filter.assess_signal_quality(signal)

        # Create enhanced signal with quality improvements
        enhanced_signal = self._create_enhanced_signal(signal, quality_metrics)

        return enhanced_signal, quality_metrics

    def _create_enhanced_signal(self, signal: Signal, quality: SignalQualityMetrics) -> Signal:
        """Create enhanced signal with improved confluence scoring."""

        # Calculate enhanced confluence score
        enhanced_confluence = self._calculate_enhanced_confluence(signal, quality)

        # Adjust confidence based on quality assessment
        enhanced_confidence = self._calculate_enhanced_confidence(signal, quality)

        # Generate enhanced reasoning
        enhanced_reasoning = self._generate_enhanced_reasoning(signal, quality)

        # Create enhanced signal
        enhanced_signal = Signal(
            signal_id=f"enhanced_{signal.signal_id}",
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            direction=signal.direction,
            confluence_score=enhanced_confluence,
            confidence=enhanced_confidence,
            market_regime=signal.market_regime,
            primary_timeframe=signal.primary_timeframe,
            timeframe_analysis=signal.timeframe_analysis,
            patterns=signal.patterns,
            indicators=signal.indicators,
            llm_analysis=signal.llm_analysis,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_reward_ratio=signal.risk_reward_ratio,
            max_risk_pct=signal.max_risk_pct,
            reasoning=enhanced_reasoning,
            key_factors=quality.quality_factors,
            expires_at=signal.expires_at,
            priority=self._calculate_enhanced_priority(quality)
        )

        return enhanced_signal

    def _calculate_enhanced_confluence(self, signal: Signal, quality: SignalQualityMetrics) -> float:
        """Calculate enhanced confluence score."""
        base_score = signal.confluence_score

        # Quality-based adjustments
        quality_multiplier = 1.0

        if quality.overall_quality >= 80:
            quality_multiplier = 1.2
        elif quality.overall_quality >= 60:
            quality_multiplier = 1.1
        elif quality.overall_quality < 40:
            quality_multiplier = 0.8

        # Pattern strength bonus
        pattern_bonus = 0.0
        for pattern in signal.patterns:
            if pattern.confidence > 0.7 and pattern.strength > 5:
                pattern_bonus += 5.0

        enhanced_score = (base_score * quality_multiplier) + pattern_bonus
        return min(100.0, enhanced_score)

    def _calculate_enhanced_confidence(self, signal: Signal, quality: SignalQualityMetrics) -> float:
        """Calculate enhanced confidence score."""
        base_confidence = signal.confidence

        # Quality-based confidence adjustment
        if quality.overall_quality >= 85:
            adjustment = 0.1
        elif quality.overall_quality >= 70:
            adjustment = 0.05
        elif quality.overall_quality < 40:
            adjustment = -0.1
        else:
            adjustment = 0.0

        enhanced_confidence = base_confidence + adjustment
        return min(1.0, max(0.0, enhanced_confidence))

    def _generate_enhanced_reasoning(self, signal: Signal, quality: SignalQualityMetrics) -> str:
        """Generate enhanced reasoning with quality insights."""
        base_reasoning = signal.reasoning

        quality_note = f" [Quality: {quality.trading_grade} - {quality.overall_quality:.1f}/100]"

        if quality.quality_factors:
            strengths = "; ".join(quality.quality_factors[:3])
            quality_note += f" Strengths: {strengths}."

        if quality.risk_factors:
            risks = "; ".join(quality.risk_factors[:2])
            quality_note += f" Risks: {risks}."

        return base_reasoning + quality_note

    def _calculate_enhanced_priority(self, quality: SignalQualityMetrics) -> int:
        """Calculate signal priority based on quality."""
        if quality.overall_quality >= 90:
            return 5  # Highest priority
        elif quality.overall_quality >= 80:
            return 4  # High priority
        elif quality.overall_quality >= 60:
            return 3  # Medium priority
        elif quality.overall_quality >= 40:
            return 2  # Low priority
        else:
            return 1  # Lowest priority


class SignalQualityOrchestrator:
    """Orchestrates signal quality enhancement across the trading system."""

    def __init__(self):
        self.confluence_engine = AdvancedConfluenceEngine()
        self.quality_history = []
        self.performance_tracker = {}

    def process_signal(self, signal: Signal) -> Optional[tuple[Signal, SignalQualityMetrics]]:
        """Process and enhance signal quality."""

        # Enhance signal quality
        enhanced_signal, quality_metrics = self.confluence_engine.enhance_signal_quality(signal)

        # Apply final quality filter
        if not self.confluence_engine.signal_filter.should_trade_signal(enhanced_signal, quality_metrics):
            return None

        # Track quality metrics
        self._track_signal_quality(enhanced_signal, quality_metrics)

        return enhanced_signal, quality_metrics

    def get_quality_report(self) -> dict[str, Any]:
        """Generate signal quality performance report."""
        if not self.quality_history:
            return {"message": "No signals processed yet"}

        recent_signals = self.quality_history[-50:]  # Last 50 signals

        avg_quality = np.mean([s['overall_quality'] for s in recent_signals])
        grade_distribution = {}

        for signal_data in recent_signals:
            grade = signal_data['trading_grade']
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        return {
            "total_signals_processed": len(self.quality_history),
            "recent_average_quality": round(avg_quality, 2),
            "grade_distribution": grade_distribution,
            "high_quality_percentage": len([s for s in recent_signals if s['overall_quality'] >= 70]) / len(recent_signals) * 100,
            "trading_ready_percentage": len([s for s in recent_signals if s['trading_grade'] in ['A+', 'A', 'B+', 'B']]) / len(recent_signals) * 100
        }

    def _track_signal_quality(self, signal: Signal, quality: SignalQualityMetrics):
        """Track signal quality for performance monitoring."""
        self.quality_history.append({
            "timestamp": signal.timestamp.isoformat(),
            "symbol": signal.symbol,
            "overall_quality": quality.overall_quality,
            "trading_grade": quality.trading_grade,
            "confidence": signal.confidence,
            "confluence_score": signal.confluence_score
        })
