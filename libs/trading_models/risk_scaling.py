"""
Risk Scaling Manager

This module manages progressive scaling of risk exposure based on performance validation.
It implements algorithms to gradually increase position sizes and trading exposure as the
system proves reliable, while maintaining strict safety controls.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from .live_trading_config import (
    PerformanceMetrics,
    PerformanceThresholds,
    RiskLimits,
    ScalingValidation,
)

logger = logging.getLogger(__name__)


class ScalingPhase(str, Enum):
    """Risk scaling phases."""
    PAPER = "paper"
    MINIMAL = "minimal"
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    MAXIMUM = "maximum"


@dataclass
class ScalingRule:
    """Defines rules for risk scaling progression."""
    phase: ScalingPhase
    max_risk_per_trade: float
    max_portfolio_exposure: float
    min_performance_days: int
    required_win_rate: float
    required_sharpe_ratio: float
    max_drawdown: float
    min_trades: int
    max_correlation: float = 0.7

    def __post_init__(self):
        if not (0 < self.max_risk_per_trade <= 0.02):  # Max 2%
            raise ValueError("Risk per trade must be between 0 and 2%")
        if not (0 < self.max_portfolio_exposure <= 1.0):
            raise ValueError("Portfolio exposure must be between 0 and 100%")


@dataclass
class ScalingHistory:
    """Records scaling decisions and performance."""
    timestamp: datetime
    from_phase: ScalingPhase
    to_phase: ScalingPhase
    trigger_performance: PerformanceMetrics
    new_risk_limits: RiskLimits
    reason: str
    validation_passed: bool


@dataclass
class MarketVolatilityMetrics:
    """Market volatility metrics for risk adjustment."""
    symbol: str
    current_volatility: float  # Current volatility (e.g., ATR-based)
    avg_volatility: float      # Average volatility over period
    volatility_percentile: float  # Percentile ranking (0-100)
    trend_strength: float      # Trend strength indicator
    last_updated: datetime


class RiskScalingManager:
    """
    Manages progressive scaling of trading risk based on performance validation.

    Implements a phase-based approach where risk is gradually increased as the
    system demonstrates consistent performance over time.
    """

    def __init__(self, initial_phase: ScalingPhase = ScalingPhase.PAPER):
        """
        Initialize risk scaling manager.

        Args:
            initial_phase: Starting scaling phase
        """
        self.current_phase = initial_phase
        self.scaling_rules = self._initialize_scaling_rules()
        self.scaling_history: list[ScalingHistory] = []
        self.last_scaling_time: Optional[datetime] = None
        self.performance_history: list[PerformanceMetrics] = []
        self.volatility_metrics: dict[str, MarketVolatilityMetrics] = {}

        logger.info(f"Risk scaling manager initialized at phase: {initial_phase}")

    def _initialize_scaling_rules(self) -> dict[ScalingPhase, ScalingRule]:
        """Initialize scaling rules for each phase."""
        return {
            ScalingPhase.PAPER: ScalingRule(
                phase=ScalingPhase.PAPER,
                max_risk_per_trade=0.005,  # 0.5%
                max_portfolio_exposure=0.20,  # 20%
                min_performance_days=7,
                required_win_rate=0.45,
                required_sharpe_ratio=0.5,
                max_drawdown=0.15,
                min_trades=10
            ),
            ScalingPhase.MINIMAL: ScalingRule(
                phase=ScalingPhase.MINIMAL,
                max_risk_per_trade=0.001,  # 0.1%
                max_portfolio_exposure=0.02,  # 2%
                min_performance_days=7,
                required_win_rate=0.50,
                required_sharpe_ratio=0.6,
                max_drawdown=0.10,
                min_trades=15
            ),
            ScalingPhase.CONSERVATIVE: ScalingRule(
                phase=ScalingPhase.CONSERVATIVE,
                max_risk_per_trade=0.0025,  # 0.25%
                max_portfolio_exposure=0.05,  # 5%
                min_performance_days=14,
                required_win_rate=0.52,
                required_sharpe_ratio=0.7,
                max_drawdown=0.08,
                min_trades=25
            ),
            ScalingPhase.MODERATE: ScalingRule(
                phase=ScalingPhase.MODERATE,
                max_risk_per_trade=0.005,  # 0.5%
                max_portfolio_exposure=0.10,  # 10%
                min_performance_days=21,
                required_win_rate=0.55,
                required_sharpe_ratio=0.8,
                max_drawdown=0.06,
                min_trades=40
            ),
            ScalingPhase.AGGRESSIVE: ScalingRule(
                phase=ScalingPhase.AGGRESSIVE,
                max_risk_per_trade=0.0075,  # 0.75%
                max_portfolio_exposure=0.15,  # 15%
                min_performance_days=30,
                required_win_rate=0.58,
                required_sharpe_ratio=1.0,
                max_drawdown=0.05,
                min_trades=60
            ),
            ScalingPhase.MAXIMUM: ScalingRule(
                phase=ScalingPhase.MAXIMUM,
                max_risk_per_trade=0.01,  # 1.0%
                max_portfolio_exposure=0.20,  # 20%
                min_performance_days=45,
                required_win_rate=0.60,
                required_sharpe_ratio=1.2,
                max_drawdown=0.04,
                min_trades=100
            )
        }

    def calculate_next_risk_level(self, performance: PerformanceMetrics) -> float:
        """
        Calculate the next appropriate risk level based on performance.

        Args:
            performance: Current performance metrics

        Returns:
            Recommended risk per trade
        """
        current_rule = self.scaling_rules[self.current_phase]

        # Check if we can scale up
        validation = self.validate_scaling_conditions(performance)

        if not validation.can_scale:
            # Return current risk level if scaling not allowed
            return current_rule.max_risk_per_trade

        # Get next phase
        next_phase = self._get_next_phase()
        if next_phase is None:
            # Already at maximum phase
            return current_rule.max_risk_per_trade

        next_rule = self.scaling_rules[next_phase]

        # Apply performance-based adjustment
        performance_multiplier = self._calculate_performance_multiplier(performance)

        # Apply volatility adjustment
        volatility_multiplier = self._calculate_volatility_multiplier()

        # Calculate adjusted risk level
        base_risk = next_rule.max_risk_per_trade
        adjusted_risk = base_risk * performance_multiplier * volatility_multiplier

        # Ensure we don't exceed the next phase's maximum
        final_risk = min(adjusted_risk, next_rule.max_risk_per_trade)

        logger.info(f"Calculated next risk level: {final_risk:.4f} "
                   f"(base: {base_risk:.4f}, perf: {performance_multiplier:.2f}, "
                   f"vol: {volatility_multiplier:.2f})")

        return final_risk

    def validate_scaling_conditions(self, performance: PerformanceMetrics) -> ScalingValidation:
        """
        Validate if conditions are met for scaling up risk.

        Args:
            performance: Current performance metrics

        Returns:
            ScalingValidation with detailed results
        """
        current_rule = self.scaling_rules[self.current_phase]
        blocking_reasons = []

        # Check time since last scaling
        days_since_scaling = 0
        if self.last_scaling_time:
            days_since_scaling = (datetime.now(UTC) - self.last_scaling_time).days

        if days_since_scaling < current_rule.min_performance_days:
            blocking_reasons.append(
                f"Insufficient time since last scaling: {days_since_scaling} < {current_rule.min_performance_days} days"
            )

        # Check performance thresholds
        if performance.win_rate < current_rule.required_win_rate:
            blocking_reasons.append(
                f"Win rate too low: {performance.win_rate:.1%} < {current_rule.required_win_rate:.1%}"
            )

        if performance.sharpe_ratio < current_rule.required_sharpe_ratio:
            blocking_reasons.append(
                f"Sharpe ratio too low: {performance.sharpe_ratio:.2f} < {current_rule.required_sharpe_ratio:.2f}"
            )

        if performance.max_drawdown > current_rule.max_drawdown:
            blocking_reasons.append(
                f"Drawdown too high: {performance.max_drawdown:.1%} > {current_rule.max_drawdown:.1%}"
            )

        if performance.total_trades < current_rule.min_trades:
            blocking_reasons.append(
                f"Insufficient trades: {performance.total_trades} < {current_rule.min_trades}"
            )

        # Check market volatility
        avg_volatility = self._get_average_market_volatility()
        if avg_volatility > 0.8:  # High volatility threshold
            blocking_reasons.append(f"Market volatility too high: {avg_volatility:.1%}")

        # Calculate risk concentration
        risk_concentration = self._calculate_risk_concentration()

        can_scale = len(blocking_reasons) == 0

        return ScalingValidation(
            can_scale=can_scale,
            current_performance=performance,
            required_thresholds=PerformanceThresholds(
                min_win_rate=current_rule.required_win_rate,
                min_sharpe_ratio=current_rule.required_sharpe_ratio,
                max_drawdown=current_rule.max_drawdown,
                min_trades=current_rule.min_trades
            ),
            days_since_last_scale=days_since_scaling,
            risk_concentration=risk_concentration,
            market_volatility=avg_volatility,
            blocking_reasons=blocking_reasons
        )

    def apply_risk_scaling(self, new_risk_level: float, performance: PerformanceMetrics) -> bool:
        """
        Apply risk scaling to move to the next phase.

        Args:
            new_risk_level: New risk per trade level
            performance: Performance metrics that triggered scaling

        Returns:
            True if scaling was applied successfully
        """
        # Validate scaling conditions
        validation = self.validate_scaling_conditions(performance)

        if not validation.can_scale:
            logger.warning(f"Scaling blocked: {', '.join(validation.blocking_reasons)}")
            return False

        # Determine target phase based on risk level
        target_phase = self._determine_phase_for_risk_level(new_risk_level)

        if target_phase == self.current_phase:
            logger.info("Risk level matches current phase, no scaling needed")
            return True

        # Create new risk limits
        target_rule = self.scaling_rules[target_phase]
        new_risk_limits = RiskLimits(
            max_risk_per_trade=new_risk_level,
            max_portfolio_exposure=target_rule.max_portfolio_exposure,
            daily_loss_limit=target_rule.max_portfolio_exposure * 0.5,  # 50% of max exposure
            max_correlation=target_rule.max_correlation
        )

        # Record scaling decision
        scaling_record = ScalingHistory(
            timestamp=datetime.now(UTC),
            from_phase=self.current_phase,
            to_phase=target_phase,
            trigger_performance=performance,
            new_risk_limits=new_risk_limits,
            reason=f"Performance validation passed: {performance.win_rate:.1%} win rate, "
                   f"{performance.sharpe_ratio:.2f} Sharpe ratio",
            validation_passed=True
        )

        self.scaling_history.append(scaling_record)
        self.current_phase = target_phase
        self.last_scaling_time = datetime.now(UTC)

        logger.info(f"Risk scaling applied: {scaling_record.from_phase} -> {scaling_record.to_phase} "
                   f"(risk: {new_risk_level:.4f})")

        return True

    def monitor_concentration_risk(self, positions: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Monitor portfolio concentration risk.

        Args:
            positions: List of current positions

        Returns:
            Concentration risk report
        """
        if not positions:
            return {
                "total_positions": 0,
                "max_single_exposure": 0.0,
                "sector_concentration": {},
                "correlation_risk": 0.0,
                "concentration_score": 0.0,
                "warnings": []
            }

        # Calculate exposures
        total_exposure = sum(abs(pos.get("exposure", 0)) for pos in positions)
        max_single_exposure = max(abs(pos.get("exposure", 0)) for pos in positions) if positions else 0
        max_single_percentage = (max_single_exposure / total_exposure) if total_exposure > 0 else 0

        # Group by sector/symbol type
        sector_exposure = {}
        for pos in positions:
            symbol = pos.get("symbol", "")
            sector = self._get_symbol_sector(symbol)
            sector_exposure[sector] = sector_exposure.get(sector, 0) + abs(pos.get("exposure", 0))

        # Calculate sector percentages
        sector_percentages = {}
        if total_exposure > 0:
            sector_percentages = {
                sector: exposure / total_exposure
                for sector, exposure in sector_exposure.items()
            }

        # Calculate correlation risk (simplified)
        correlation_risk = self._estimate_correlation_risk(positions)

        # Calculate overall concentration score (0-100, higher = more concentrated)
        concentration_score = (
            max_single_percentage * 40 +  # Single position weight (40%)
            max(sector_percentages.values(), default=0) * 40 +  # Sector concentration (40%)
            correlation_risk * 20  # Correlation risk (20%)
        ) * 100

        # Generate warnings
        warnings = []
        current_rule = self.scaling_rules[self.current_phase]

        if max_single_percentage > 0.3:  # 30% in single position
            warnings.append(f"High single position exposure: {max_single_percentage:.1%}")

        if max(sector_percentages.values(), default=0) > 0.5:  # 50% in single sector
            warnings.append(f"High sector concentration: {max(sector_percentages.values()):.1%}")

        if correlation_risk > current_rule.max_correlation:
            warnings.append(f"High correlation risk: {correlation_risk:.1%}")

        return {
            "total_positions": len(positions),
            "total_exposure": total_exposure,
            "max_single_exposure": max_single_percentage,
            "sector_concentration": sector_percentages,
            "correlation_risk": correlation_risk,
            "concentration_score": concentration_score,
            "warnings": warnings
        }

    def adjust_for_market_volatility(self, base_risk: float, symbol: str) -> float:
        """
        Adjust risk level based on current market volatility.

        Args:
            base_risk: Base risk level
            symbol: Trading symbol

        Returns:
            Volatility-adjusted risk level
        """
        if symbol not in self.volatility_metrics:
            # No volatility data, use base risk
            return base_risk

        vol_metrics = self.volatility_metrics[symbol]

        # Calculate volatility adjustment factor
        if vol_metrics.avg_volatility > 0:
            vol_ratio = vol_metrics.current_volatility / vol_metrics.avg_volatility
        else:
            vol_ratio = 1.0

        # Reduce risk when volatility is high
        if vol_ratio > 1.5:  # High volatility
            adjustment_factor = 0.7  # Reduce risk by 30%
        elif vol_ratio > 1.2:  # Moderate volatility
            adjustment_factor = 0.85  # Reduce risk by 15%
        elif vol_ratio < 0.8:  # Low volatility
            adjustment_factor = 1.1  # Increase risk by 10%
        else:
            adjustment_factor = 1.0  # Normal volatility

        adjusted_risk = base_risk * adjustment_factor

        # Ensure we don't exceed current phase limits
        current_rule = self.scaling_rules[self.current_phase]
        final_risk = min(adjusted_risk, current_rule.max_risk_per_trade)

        if adjusted_risk != base_risk:
            logger.info(f"Volatility adjustment for {symbol}: {base_risk:.4f} -> {final_risk:.4f} "
                       f"(vol ratio: {vol_ratio:.2f})")

        return final_risk

    def update_volatility_metrics(self, symbol: str, volatility: float, trend_strength: float) -> None:
        """Update volatility metrics for a symbol."""
        now = datetime.now(UTC)

        if symbol in self.volatility_metrics:
            # Update existing metrics
            metrics = self.volatility_metrics[symbol]
            # Simple exponential moving average
            alpha = 0.1  # Smoothing factor
            metrics.avg_volatility = (1 - alpha) * metrics.avg_volatility + alpha * volatility
            metrics.current_volatility = volatility
            metrics.trend_strength = trend_strength
            metrics.last_updated = now
        else:
            # Create new metrics
            self.volatility_metrics[symbol] = MarketVolatilityMetrics(
                symbol=symbol,
                current_volatility=volatility,
                avg_volatility=volatility,
                volatility_percentile=50.0,  # Default to median
                trend_strength=trend_strength,
                last_updated=now
            )

    def get_current_risk_limits(self) -> RiskLimits:
        """Get current risk limits for the active phase."""
        current_rule = self.scaling_rules[self.current_phase]

        return RiskLimits(
            max_risk_per_trade=current_rule.max_risk_per_trade,
            max_portfolio_exposure=current_rule.max_portfolio_exposure,
            daily_loss_limit=current_rule.max_portfolio_exposure * 0.5,
            max_correlation=current_rule.max_correlation
        )

    def get_scaling_status(self) -> dict[str, Any]:
        """Get current scaling status and metrics."""
        current_rule = self.scaling_rules[self.current_phase]
        next_phase = self._get_next_phase()

        status = {
            "current_phase": self.current_phase.value,
            "current_risk_per_trade": current_rule.max_risk_per_trade,
            "current_max_exposure": current_rule.max_portfolio_exposure,
            "next_phase": next_phase.value if next_phase else None,
            "days_since_last_scaling": 0,
            "scaling_history_count": len(self.scaling_history),
            "can_scale_up": next_phase is not None,
            "volatility_symbols": list(self.volatility_metrics.keys())
        }

        if self.last_scaling_time:
            status["days_since_last_scaling"] = (
                datetime.now(UTC) - self.last_scaling_time
            ).days

        return status

    def _get_next_phase(self) -> Optional[ScalingPhase]:
        """Get the next scaling phase."""
        phases = list(ScalingPhase)
        current_index = phases.index(self.current_phase)

        if current_index < len(phases) - 1:
            return phases[current_index + 1]
        return None

    def _determine_phase_for_risk_level(self, risk_level: float) -> ScalingPhase:
        """Determine appropriate phase for a given risk level."""
        for phase in reversed(list(ScalingPhase)):
            rule = self.scaling_rules[phase]
            if risk_level <= rule.max_risk_per_trade:
                return phase

        return ScalingPhase.PAPER  # Fallback to most conservative

    def _calculate_performance_multiplier(self, performance: PerformanceMetrics) -> float:
        """Calculate performance-based risk multiplier."""
        # Base multiplier on win rate and Sharpe ratio
        win_rate_factor = min(performance.win_rate / 0.6, 1.2)  # Cap at 1.2x
        sharpe_factor = min(performance.sharpe_ratio / 1.0, 1.2)  # Cap at 1.2x

        # Penalty for high drawdown
        drawdown_penalty = max(0.8, 1.0 - (performance.max_drawdown * 2))

        multiplier = (win_rate_factor + sharpe_factor) / 2 * drawdown_penalty

        return max(0.5, min(1.2, multiplier))  # Clamp between 0.5x and 1.2x

    def _calculate_volatility_multiplier(self) -> float:
        """Calculate volatility-based risk multiplier."""
        if not self.volatility_metrics:
            return 1.0

        avg_vol_ratio = sum(
            m.current_volatility / m.avg_volatility if m.avg_volatility > 0 else 1.0
            for m in self.volatility_metrics.values()
        ) / len(self.volatility_metrics)

        # Reduce multiplier when volatility is high
        if avg_vol_ratio > 1.5:
            return 0.7
        elif avg_vol_ratio > 1.2:
            return 0.85
        elif avg_vol_ratio < 0.8:
            return 1.1
        else:
            return 1.0

    def _get_average_market_volatility(self) -> float:
        """Get average market volatility across all symbols."""
        if not self.volatility_metrics:
            return 0.5  # Default moderate volatility

        return sum(m.volatility_percentile for m in self.volatility_metrics.values()) / len(self.volatility_metrics) / 100

    def _calculate_risk_concentration(self) -> float:
        """Calculate current risk concentration."""
        # Simplified calculation - would need actual position data
        return 0.3  # Default 30% concentration

    def _estimate_correlation_risk(self, positions: list[dict[str, Any]]) -> float:
        """Estimate correlation risk between positions."""
        if len(positions) <= 1:
            return 0.0

        # Simplified correlation estimation based on symbol types
        crypto_count = sum(1 for pos in positions if "USDT" in pos.get("symbol", ""))
        total_positions = len(positions)

        if total_positions == 0:
            return 0.0

        # High correlation if all positions are in same asset class
        crypto_ratio = crypto_count / total_positions

        if crypto_ratio > 0.8:  # >80% crypto
            return 0.8
        elif crypto_ratio > 0.6:  # >60% crypto
            return 0.6
        else:
            return 0.3  # Diversified

    def _get_symbol_sector(self, symbol: str) -> str:
        """Get sector classification for a symbol."""
        if "USDT" in symbol or "BUSD" in symbol:
            return "crypto"
        elif "USD" in symbol:
            return "forex"
        else:
            return "other"
