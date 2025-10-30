"""
Excellent Performance Metrics System

This module provides enterprise-grade performance metrics that target
excellent quality across all trading dimensions and KPIs.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np

from .patterns import PatternHit
from .signals import Signal


class PerformanceGrade(str, Enum):
    """Performance quality grades."""
    EXCELLENT = "excellent"      # 90-100%
    VERY_GOOD = "very_good"     # 80-89%
    GOOD = "good"               # 70-79%
    SATISFACTORY = "satisfactory"  # 60-69%
    NEEDS_IMPROVEMENT = "needs_improvement"  # 50-59%
    POOR = "poor"               # <50%


@dataclass
class ExcellentMetrics:
    """Comprehensive excellent-quality performance metrics."""

    # Detection Excellence Metrics
    pattern_detection_accuracy: float  # 0-100: Pattern detection precision
    signal_quality_score: float       # 0-100: Overall signal quality
    confidence_calibration: float     # 0-100: Confidence accuracy
    false_positive_rate: float        # 0-100: False signal rate (lower is better)

    # Trading Excellence Metrics
    win_rate_quality: float           # 0-100: Win rate vs targets
    risk_reward_excellence: float     # 0-100: R:R ratio quality
    drawdown_control: float           # 0-100: Drawdown management
    profit_consistency: float        # 0-100: Profit stability

    # Technical Excellence Metrics
    execution_speed: float            # 0-100: Processing speed quality
    system_reliability: float        # 0-100: Uptime and stability
    data_quality: float              # 0-100: Data integrity score
    response_time_excellence: float  # 0-100: Response time quality

    # Market Excellence Metrics
    market_adaptation: float         # 0-100: Adaptation to conditions
    regime_detection: float          # 0-100: Market regime accuracy
    volatility_handling: float      # 0-100: Volatility management
    correlation_awareness: float    # 0-100: Cross-asset correlation

    # Composite Excellence Score
    overall_excellence: float        # 0-100: Weighted composite
    excellence_grade: PerformanceGrade  # Overall grade

    # Excellence Factors
    excellence_drivers: list[str]    # What drives excellent performance
    improvement_areas: list[str]     # Areas for enhancement
    excellence_recommendations: list[str]  # How to achieve excellence


class ExcellentPerformanceAnalyzer:
    """Analyzes and enhances performance metrics for excellent quality."""

    def __init__(self):
        # Excellence thresholds (targeting top 1% performance)
        self.excellence_thresholds = {
            'pattern_detection_accuracy': 95.0,  # 95%+ detection accuracy
            'signal_quality_score': 90.0,       # 90%+ signal quality
            'confidence_calibration': 92.0,     # 92%+ confidence accuracy
            'false_positive_rate': 5.0,         # <5% false positives
            'win_rate_quality': 85.0,           # 85%+ win rate quality
            'risk_reward_excellence': 88.0,     # 88%+ R:R quality
            'drawdown_control': 90.0,           # 90%+ drawdown control
            'profit_consistency': 85.0,         # 85%+ profit consistency
            'execution_speed': 95.0,            # 95%+ execution speed
            'system_reliability': 99.0,         # 99%+ system uptime
            'data_quality': 98.0,               # 98%+ data quality
            'response_time_excellence': 93.0,   # 93%+ response time
            'market_adaptation': 87.0,          # 87%+ market adaptation
            'regime_detection': 90.0,           # 90%+ regime detection
            'volatility_handling': 85.0,        # 85%+ volatility handling
            'correlation_awareness': 82.0       # 82%+ correlation awareness
        }

        # Weights for composite excellence score
        self.excellence_weights = {
            'detection': 0.25,      # Pattern detection quality
            'trading': 0.30,        # Trading performance quality
            'technical': 0.25,      # Technical system quality
            'market': 0.20          # Market analysis quality
        }

    def analyze_excellent_performance(self,
                                    patterns: list[PatternHit],
                                    signals: list[Signal],
                                    trading_history: list[dict],
                                    system_metrics: dict[str, float]) -> ExcellentMetrics:
        """Analyze performance for excellent quality across all dimensions."""

        # Detection Excellence Analysis
        detection_metrics = self._analyze_detection_excellence(patterns, signals)

        # Trading Excellence Analysis
        trading_metrics = self._analyze_trading_excellence(trading_history)

        # Technical Excellence Analysis
        technical_metrics = self._analyze_technical_excellence(system_metrics)

        # Market Excellence Analysis
        market_metrics = self._analyze_market_excellence(signals, patterns)

        # Calculate composite excellence score
        composite_score = (
            detection_metrics['composite'] * self.excellence_weights['detection'] +
            trading_metrics['composite'] * self.excellence_weights['trading'] +
            technical_metrics['composite'] * self.excellence_weights['technical'] +
            market_metrics['composite'] * self.excellence_weights['market']
        )

        # Determine excellence grade
        excellence_grade = self._calculate_excellence_grade(composite_score)

        # Generate excellence insights
        drivers = self._identify_excellence_drivers(detection_metrics, trading_metrics,
                                                  technical_metrics, market_metrics)
        improvements = self._identify_improvement_areas(detection_metrics, trading_metrics,
                                                      technical_metrics, market_metrics)
        recommendations = self._generate_excellence_recommendations(composite_score, improvements)

        return ExcellentMetrics(
            # Detection Excellence
            pattern_detection_accuracy=detection_metrics['accuracy'],
            signal_quality_score=detection_metrics['quality'],
            confidence_calibration=detection_metrics['calibration'],
            false_positive_rate=detection_metrics['false_positive'],

            # Trading Excellence
            win_rate_quality=trading_metrics['win_rate'],
            risk_reward_excellence=trading_metrics['risk_reward'],
            drawdown_control=trading_metrics['drawdown'],
            profit_consistency=trading_metrics['consistency'],

            # Technical Excellence
            execution_speed=technical_metrics['speed'],
            system_reliability=technical_metrics['reliability'],
            data_quality=technical_metrics['data_quality'],
            response_time_excellence=technical_metrics['response_time'],

            # Market Excellence
            market_adaptation=market_metrics['adaptation'],
            regime_detection=market_metrics['regime'],
            volatility_handling=market_metrics['volatility'],
            correlation_awareness=market_metrics['correlation'],

            # Composite
            overall_excellence=composite_score,
            excellence_grade=excellence_grade,

            # Insights
            excellence_drivers=drivers,
            improvement_areas=improvements,
            excellence_recommendations=recommendations
        )

    def _analyze_detection_excellence(self, patterns: list[PatternHit], signals: list[Signal]) -> dict[str, float]:
        """Analyze pattern detection excellence."""
        if not patterns:
            return {
                'accuracy': 0.0, 'quality': 0.0, 'calibration': 0.0,
                'false_positive': 100.0, 'composite': 0.0
            }

        # Pattern Detection Accuracy (based on confidence vs actual performance)
        high_confidence_patterns = [p for p in patterns if p.confidence >= 0.8]
        accuracy_score = min(100.0, (len(high_confidence_patterns) / len(patterns)) * 120)

        # Signal Quality Score
        if signals:
            avg_signal_quality = np.mean([s.confluence_score for s in signals])
            quality_score = min(100.0, avg_signal_quality * 1.1)  # Boost for excellence
        else:
            quality_score = 0.0

        # Confidence Calibration (how well confidence predicts success)
        avg_confidence = np.mean([p.confidence for p in patterns])
        calibration_score = min(100.0, avg_confidence * 110)  # Target >90% for excellence

        # False Positive Rate (estimated from low-confidence patterns)
        low_confidence_patterns = [p for p in patterns if p.confidence < 0.5]
        false_positive_rate = (len(low_confidence_patterns) / len(patterns)) * 100

        composite = (accuracy_score + quality_score + calibration_score + (100 - false_positive_rate)) / 4

        return {
            'accuracy': accuracy_score,
            'quality': quality_score,
            'calibration': calibration_score,
            'false_positive': false_positive_rate,
            'composite': composite
        }

    def _analyze_trading_excellence(self, trading_history: list[dict]) -> dict[str, float]:
        """Analyze trading performance excellence."""
        if not trading_history:
            return {
                'win_rate': 0.0, 'risk_reward': 0.0, 'drawdown': 0.0,
                'consistency': 0.0, 'composite': 0.0
            }

        # Win Rate Quality (target 70%+ for excellence)
        winning_trades = [t for t in trading_history if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(trading_history)
        win_rate_quality = min(100.0, (win_rate / 0.7) * 100)  # Scale to 70% target

        # Risk/Reward Excellence (target 2.5:1+ for excellence)
        avg_rr = np.mean([t.get('risk_reward_ratio', 1.0) for t in trading_history])
        rr_excellence = min(100.0, (avg_rr / 2.5) * 100)  # Scale to 2.5:1 target

        # Drawdown Control (target <5% for excellence)
        max_drawdown = max([abs(t.get('drawdown', 0)) for t in trading_history], default=0)
        drawdown_control = max(0.0, 100 - (max_drawdown * 20))  # Penalty for drawdown

        # Profit Consistency (coefficient of variation)
        pnls = [t.get('pnl', 0) for t in trading_history]
        if len(pnls) > 1 and np.std(pnls) > 0:
            cv = np.std(pnls) / abs(np.mean(pnls))
            consistency = max(0.0, 100 - (cv * 50))  # Lower CV = higher consistency
        else:
            consistency = 50.0  # Default for insufficient data

        composite = (win_rate_quality + rr_excellence + drawdown_control + consistency) / 4

        return {
            'win_rate': win_rate_quality,
            'risk_reward': rr_excellence,
            'drawdown': drawdown_control,
            'consistency': consistency,
            'composite': composite
        }

    def _analyze_technical_excellence(self, system_metrics: dict[str, float]) -> dict[str, float]:
        """Analyze technical system excellence."""

        # Execution Speed (target <10ms for excellence)
        execution_time = system_metrics.get('avg_execution_time_ms', 50)
        speed_score = max(0.0, 100 - (execution_time / 10) * 100)

        # System Reliability (target 99.9%+ uptime for excellence)
        uptime = system_metrics.get('uptime_percentage', 95.0)
        reliability_score = min(100.0, (uptime / 99.9) * 100)

        # Data Quality (target 99%+ for excellence)
        data_quality = system_metrics.get('data_quality_score', 90.0)
        data_score = min(100.0, (data_quality / 99.0) * 100)

        # Response Time Excellence (target <100ms for excellence)
        response_time = system_metrics.get('avg_response_time_ms', 200)
        response_score = max(0.0, 100 - (response_time / 100) * 100)

        composite = (speed_score + reliability_score + data_score + response_score) / 4

        return {
            'speed': speed_score,
            'reliability': reliability_score,
            'data_quality': data_score,
            'response_time': response_score,
            'composite': composite
        }

    def _analyze_market_excellence(self, signals: list[Signal], patterns: list[PatternHit]) -> dict[str, float]:
        """Analyze market analysis excellence."""

        # Market Adaptation (how well system adapts to different conditions)
        if signals:
            regime_distribution = {}
            for signal in signals:
                regime = signal.market_regime
                regime_distribution[regime] = regime_distribution.get(regime, 0) + 1

            # Diversity bonus for handling multiple regimes
            regime_count = len(regime_distribution)
            adaptation_score = min(100.0, 60 + (regime_count * 15))  # Bonus for diversity
        else:
            adaptation_score = 0.0

        # Regime Detection (accuracy of market regime identification)
        if signals:
            # Assume high-confidence signals indicate good regime detection
            high_conf_signals = [s for s in signals if s.confidence >= 0.8]
            regime_score = min(100.0, (len(high_conf_signals) / len(signals)) * 120)
        else:
            regime_score = 0.0

        # Volatility Handling (how well system handles different volatility levels)
        if patterns:
            # Strong patterns in volatile conditions indicate good handling
            strong_patterns = [p for p in patterns if p.strength >= 7.0]
            volatility_score = min(100.0, (len(strong_patterns) / len(patterns)) * 150)
        else:
            volatility_score = 0.0

        # Correlation Awareness (multi-asset analysis quality)
        if signals:
            symbols = set(s.symbol for s in signals)
            correlation_score = min(100.0, 70 + (len(symbols) * 10))  # Bonus for multi-asset
        else:
            correlation_score = 0.0

        composite = (adaptation_score + regime_score + volatility_score + correlation_score) / 4

        return {
            'adaptation': adaptation_score,
            'regime': regime_score,
            'volatility': volatility_score,
            'correlation': correlation_score,
            'composite': composite
        }

    def _calculate_excellence_grade(self, composite_score: float) -> PerformanceGrade:
        """Calculate overall excellence grade."""
        if composite_score >= 90.0:
            return PerformanceGrade.EXCELLENT
        elif composite_score >= 80.0:
            return PerformanceGrade.VERY_GOOD
        elif composite_score >= 70.0:
            return PerformanceGrade.GOOD
        elif composite_score >= 60.0:
            return PerformanceGrade.SATISFACTORY
        elif composite_score >= 50.0:
            return PerformanceGrade.NEEDS_IMPROVEMENT
        else:
            return PerformanceGrade.POOR

    def _identify_excellence_drivers(self, detection: dict, trading: dict,
                                   technical: dict, market: dict) -> list[str]:
        """Identify what drives excellent performance."""
        drivers = []

        # Detection excellence drivers
        if detection['accuracy'] >= 90:
            drivers.append("Exceptional pattern detection accuracy")
        if detection['quality'] >= 85:
            drivers.append("Outstanding signal quality")
        if detection['false_positive'] <= 5:
            drivers.append("Excellent false positive control")

        # Trading excellence drivers
        if trading['win_rate'] >= 85:
            drivers.append("Superior win rate performance")
        if trading['risk_reward'] >= 85:
            drivers.append("Excellent risk/reward management")
        if trading['drawdown'] >= 90:
            drivers.append("Outstanding drawdown control")

        # Technical excellence drivers
        if technical['speed'] >= 95:
            drivers.append("Lightning-fast execution speed")
        if technical['reliability'] >= 95:
            drivers.append("Exceptional system reliability")
        if technical['data_quality'] >= 95:
            drivers.append("Outstanding data quality")

        # Market excellence drivers
        if market['adaptation'] >= 85:
            drivers.append("Superior market adaptation")
        if market['regime'] >= 90:
            drivers.append("Excellent regime detection")

        return drivers

    def _identify_improvement_areas(self, detection: dict, trading: dict,
                                  technical: dict, market: dict) -> list[str]:
        """Identify areas needing improvement for excellence."""
        improvements = []

        # Detection improvements
        if detection['accuracy'] < 90:
            improvements.append("Enhance pattern detection accuracy")
        if detection['quality'] < 85:
            improvements.append("Improve signal quality scoring")
        if detection['false_positive'] > 10:
            improvements.append("Reduce false positive rate")

        # Trading improvements
        if trading['win_rate'] < 80:
            improvements.append("Optimize win rate performance")
        if trading['risk_reward'] < 80:
            improvements.append("Enhance risk/reward optimization")
        if trading['drawdown'] < 85:
            improvements.append("Strengthen drawdown control")

        # Technical improvements
        if technical['speed'] < 90:
            improvements.append("Optimize execution speed")
        if technical['reliability'] < 95:
            improvements.append("Improve system reliability")

        # Market improvements
        if market['adaptation'] < 80:
            improvements.append("Enhance market adaptation")
        if market['regime'] < 85:
            improvements.append("Improve regime detection")

        return improvements

    def _generate_excellence_recommendations(self, composite_score: float,
                                           improvements: list[str]) -> list[str]:
        """Generate recommendations to achieve excellence."""
        recommendations = []

        if composite_score >= 90:
            recommendations.append("Maintain excellent performance standards")
            recommendations.append("Focus on consistency and optimization")
        elif composite_score >= 80:
            recommendations.append("Push for excellence with focused improvements")
            recommendations.append("Target 90%+ composite score")
        elif composite_score >= 70:
            recommendations.append("Implement systematic performance enhancements")
            recommendations.append("Focus on top 3 improvement areas")
        else:
            recommendations.append("Comprehensive performance overhaul needed")
            recommendations.append("Address all major improvement areas")

        # Add specific recommendations based on improvements
        if "Enhance pattern detection accuracy" in improvements:
            recommendations.append("Implement advanced pattern recognition algorithms")
        if "Improve signal quality scoring" in improvements:
            recommendations.append("Deploy enhanced confluence scoring system")
        if "Optimize win rate performance" in improvements:
            recommendations.append("Refine entry and exit timing mechanisms")

        return recommendations


class ExcellentPerformanceOptimizer:
    """Optimizes system performance to achieve excellent quality standards."""

    def __init__(self):
        self.analyzer = ExcellentPerformanceAnalyzer()
        self.optimization_history = []

        # Excellence targets
        self.excellence_targets = {
            'pattern_detection': 95.0,      # 95%+ accuracy
            'signal_quality': 90.0,         # 90%+ quality
            'win_rate': 75.0,               # 75%+ win rate
            'risk_reward': 2.5,             # 2.5:1+ R:R ratio
            'max_drawdown': 3.0,            # <3% max drawdown
            'sharpe_ratio': 2.0,            # 2.0+ Sharpe ratio
            'profit_factor': 2.0,           # 2.0+ profit factor
            'system_uptime': 99.9,          # 99.9%+ uptime
            'response_time': 50.0,          # <50ms response time
            'data_quality': 99.0            # 99%+ data quality
        }

    def optimize_for_excellence(self, current_metrics: ExcellentMetrics) -> dict[str, Any]:
        """Generate optimization plan to achieve excellent performance."""

        optimization_plan = {
            'current_grade': current_metrics.excellence_grade,
            'target_grade': PerformanceGrade.EXCELLENT,
            'current_score': current_metrics.overall_excellence,
            'target_score': 90.0,
            'gap_analysis': {},
            'priority_actions': [],
            'optimization_roadmap': {},
            'expected_improvements': {}
        }

        # Gap analysis
        gaps = {}
        if current_metrics.pattern_detection_accuracy < self.excellence_targets['pattern_detection']:
            gaps['pattern_detection'] = self.excellence_targets['pattern_detection'] - current_metrics.pattern_detection_accuracy

        if current_metrics.signal_quality_score < self.excellence_targets['signal_quality']:
            gaps['signal_quality'] = self.excellence_targets['signal_quality'] - current_metrics.signal_quality_score

        if current_metrics.win_rate_quality < 85.0:  # Excellence threshold
            gaps['win_rate'] = 85.0 - current_metrics.win_rate_quality

        optimization_plan['gap_analysis'] = gaps

        # Priority actions (focus on biggest gaps first)
        priority_actions = []
        sorted_gaps = sorted(gaps.items(), key=lambda x: x[1], reverse=True)

        for metric, gap in sorted_gaps[:3]:  # Top 3 priorities
            if metric == 'pattern_detection':
                priority_actions.append("Implement advanced pattern detection algorithms")
            elif metric == 'signal_quality':
                priority_actions.append("Deploy enhanced signal quality filters")
            elif metric == 'win_rate':
                priority_actions.append("Optimize entry/exit timing and risk management")

        optimization_plan['priority_actions'] = priority_actions

        # Optimization roadmap
        roadmap = {
            'immediate': "Focus on top 3 improvement areas",
            'short_term': "Implement enhanced algorithms and filters",
            'medium_term': "Validate and optimize new implementations",
            'long_term': "Maintain excellence and continuous improvement"
        }
        optimization_plan['optimization_roadmap'] = roadmap

        # Expected improvements
        expected = {}
        for metric, gap in gaps.items():
            expected[metric] = f"Improve by {gap:.1f} points to reach excellence"
        optimization_plan['expected_improvements'] = expected

        return optimization_plan


class ExcellentPerformanceMonitor:
    """Monitors and tracks excellent performance metrics in real-time."""

    def __init__(self):
        self.analyzer = ExcellentPerformanceAnalyzer()
        self.optimizer = ExcellentPerformanceOptimizer()
        self.performance_history = []
        self.excellence_tracking = {
            'daily_scores': [],
            'trend_analysis': {},
            'achievement_milestones': []
        }

    def track_real_time_excellence(self, patterns: list[PatternHit],
                                 signals: list[Signal],
                                 system_metrics: dict[str, float]) -> ExcellentMetrics:
        """Track excellent performance metrics in real-time."""

        # Analyze current performance
        metrics = self.analyzer.analyze_excellent_performance(
            patterns, signals, [], system_metrics
        )

        # Track performance history
        self.performance_history.append({
            'timestamp': datetime.now(UTC),
            'overall_excellence': metrics.overall_excellence,
            'grade': metrics.excellence_grade,
            'detection_accuracy': metrics.pattern_detection_accuracy,
            'signal_quality': metrics.signal_quality_score
        })

        # Check for excellence achievements
        self._check_excellence_milestones(metrics)

        return metrics

    def generate_excellence_dashboard(self) -> dict[str, Any]:
        """Generate real-time excellence dashboard."""
        if not self.performance_history:
            return {"status": "No performance data available"}

        recent_performance = self.performance_history[-10:]  # Last 10 measurements

        dashboard = {
            'current_status': {
                'excellence_score': recent_performance[-1]['overall_excellence'],
                'grade': recent_performance[-1]['grade'],
                'trend': self._calculate_trend(recent_performance)
            },
            'excellence_metrics': {
                'avg_detection_accuracy': np.mean([p['detection_accuracy'] for p in recent_performance]),
                'avg_signal_quality': np.mean([p['signal_quality'] for p in recent_performance]),
                'consistency_score': self._calculate_consistency(recent_performance)
            },
            'achievement_status': {
                'excellence_achieved': recent_performance[-1]['overall_excellence'] >= 90,
                'consecutive_excellent_periods': self._count_consecutive_excellent(),
                'time_to_excellence': self._estimate_time_to_excellence()
            },
            'performance_insights': {
                'strongest_area': self._identify_strongest_area(recent_performance[-1]),
                'improvement_priority': self._identify_top_improvement_area(recent_performance[-1]),
                'excellence_probability': self._calculate_excellence_probability()
            }
        }

        return dashboard

    def _check_excellence_milestones(self, metrics: ExcellentMetrics):
        """Check and record excellence milestone achievements."""
        milestones = []

        if metrics.overall_excellence >= 90 and not any(m.get('overall_excellence_90') for m in self.excellence_tracking['achievement_milestones']):
            milestones.append({
                'achievement': 'overall_excellence_90',
                'timestamp': datetime.now(UTC),
                'description': 'Achieved 90%+ overall excellence'
            })

        if metrics.pattern_detection_accuracy >= 95 and not any(m.get('detection_95') for m in self.excellence_tracking['achievement_milestones']):
            milestones.append({
                'achievement': 'detection_95',
                'timestamp': datetime.now(UTC),
                'description': 'Achieved 95%+ pattern detection accuracy'
            })

        if metrics.signal_quality_score >= 90 and not any(m.get('signal_quality_90') for m in self.excellence_tracking['achievement_milestones']):
            milestones.append({
                'achievement': 'signal_quality_90',
                'timestamp': datetime.now(UTC),
                'description': 'Achieved 90%+ signal quality score'
            })

        self.excellence_tracking['achievement_milestones'].extend(milestones)

    def _calculate_trend(self, recent_performance: list[dict]) -> str:
        """Calculate performance trend."""
        if len(recent_performance) < 3:
            return "insufficient_data"

        scores = [p['overall_excellence'] for p in recent_performance]

        # Simple trend analysis
        recent_avg = np.mean(scores[-3:])
        earlier_avg = np.mean(scores[:-3]) if len(scores) > 3 else scores[0]

        if recent_avg > earlier_avg + 2:
            return "improving"
        elif recent_avg < earlier_avg - 2:
            return "declining"
        else:
            return "stable"

    def _calculate_consistency(self, recent_performance: list[dict]) -> float:
        """Calculate performance consistency score."""
        if len(recent_performance) < 2:
            return 0.0

        scores = [p['overall_excellence'] for p in recent_performance]
        cv = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 1.0

        # Lower coefficient of variation = higher consistency
        return max(0.0, 100 - (cv * 100))

    def _count_consecutive_excellent(self) -> int:
        """Count consecutive excellent performance periods."""
        count = 0
        for performance in reversed(self.performance_history):
            if performance['overall_excellence'] >= 90:
                count += 1
            else:
                break
        return count

    def _estimate_time_to_excellence(self) -> str:
        """Estimate time to achieve excellence."""
        if not self.performance_history:
            return "unknown"

        current_score = self.performance_history[-1]['overall_excellence']

        if current_score >= 90:
            return "achieved"
        elif current_score >= 85:
            return "1-2 optimization cycles"
        elif current_score >= 75:
            return "3-5 optimization cycles"
        else:
            return "major_improvements_needed"

    def _identify_strongest_area(self, latest_performance: dict) -> str:
        """Identify the strongest performance area."""
        # This would be enhanced with actual metric breakdown
        return "pattern_detection"  # Placeholder

    def _identify_top_improvement_area(self, latest_performance: dict) -> str:
        """Identify the top area for improvement."""
        # This would be enhanced with actual metric breakdown
        return "signal_quality"  # Placeholder

    def _calculate_excellence_probability(self) -> float:
        """Calculate probability of achieving excellence."""
        if len(self.performance_history) < 5:
            return 0.5  # Insufficient data

        recent_scores = [p['overall_excellence'] for p in self.performance_history[-5:]]
        trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]  # Linear trend

        # Project trend to excellence threshold
        current_score = recent_scores[-1]
        if trend > 0:
            periods_to_excellence = max(1, (90 - current_score) / trend)
            probability = min(1.0, max(0.0, 1 - (periods_to_excellence / 10)))
        else:
            probability = 0.1  # Low probability if declining

        return probability
