"""
Adaptive Strategy Manager
Handles dynamic strategy optimization based on real-time performance and market conditions.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from ..database.performance_repository import PerformanceRepository
from ..database.trade_repository import TradeRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StrategyParameter:
    """Represents a strategy parameter with bounds and current value"""

    name: str
    current_value: float
    min_value: float
    max_value: float
    optimal_value: Optional[float] = None
    importance: float = 1.0
    adjustment_rate: float = 0.1


@dataclass
class StrategyState:
    """Represents the current state of a trading strategy"""

    strategy_name: str
    parameters: Dict[str, StrategyParameter]
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    adaptation_history: List[Dict[str, Any]] = field(default_factory=list)
    last_adaptation: Optional[datetime] = None
    is_active: bool = True
    confidence_score: float = 1.0


@dataclass
class MarketCondition:
    """Represents current market conditions"""

    volatility: float
    trend_strength: float
    volume_profile: float
    correlation_matrix: Dict[str, float]
    time_of_day: str
    day_of_week: str
    market_phase: str  # BULL, BEAR, SIDEWAYS


class AdaptiveStrategyManager:
    """
    Adaptive strategy manager that optimizes trading strategies based on
    performance feedback and changing market conditions.
    """

    def __init__(self):
        self.trade_repository = TradeRepository()
        self.performance_repository = PerformanceRepository()

        # Strategy registry
        self.strategies: Dict[str, StrategyState] = {}

        # Machine learning components
        self.performance_classifier = RandomForestClassifier(
            n_estimators=100, random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False

        # Adaptive parameters
        self.adaptation_threshold = 0.05  # 5% performance drop triggers adaptation
        self.min_sample_size = 20  # Minimum trades before adaptation
        self.max_adaptation_frequency = 3600  # Max once per hour

        # Performance tracking
        self.performance_window = 100  # Track last 100 trades
        self.benchmark_win_rate = 0.65
        self.benchmark_profit_factor = 1.5

        logger.info("Adaptive Strategy Manager initialized")

    async def register_strategy(
        self,
        strategy_name: str,
        parameters: Dict[str, Dict[str, float]],
        initial_performance: Optional[Dict[str, float]] = None,
    ) -> None:
        """Register a new strategy for adaptive optimization"""

        strategy_params = {}
        for param_name, param_config in parameters.items():
            strategy_params[param_name] = StrategyParameter(
                name=param_name,
                current_value=param_config.get("current", 0.5),
                min_value=param_config.get("min", 0.0),
                max_value=param_config.get("max", 1.0),
                importance=param_config.get("importance", 1.0),
                adjustment_rate=param_config.get("adjustment_rate", 0.1),
            )

        strategy_state = StrategyState(
            strategy_name=strategy_name,
            parameters=strategy_params,
            performance_metrics=initial_performance or {},
        )

        self.strategies[strategy_name] = strategy_state
        logger.info(f"Strategy registered: {strategy_name}")

    async def get_adjustments(self, trade_signal) -> Dict[str, Any]:
        """Get adaptive adjustments for a trading signal"""

        strategy_name = getattr(trade_signal, "strategy", "UNKNOWN")
        if strategy_name not in self.strategies:
            return {"risk_adjustment": 1.0, "confidence_adjustment": 1.0}

        strategy = self.strategies[strategy_name]

        # Get current market conditions
        market_conditions = await self._assess_market_conditions(trade_signal.symbol)

        # Calculate adjustments based on strategy performance and market conditions
        adjustments = await self._calculate_adaptive_adjustments(
            strategy, market_conditions
        )

        return adjustments

    async def should_exit_position(
        self, position, current_price: float
    ) -> Dict[str, Any]:
        """Determine if a position should be closed based on adaptive logic"""

        strategy_name = getattr(position, "strategy", "UNKNOWN")
        if strategy_name not in self.strategies:
            return {"should_exit": False, "reason": "NO_ADAPTIVE_LOGIC"}

        strategy = self.strategies[strategy_name]

        # Calculate current position performance
        current_pnl_pct = (current_price - position.entry_price) / position.entry_price
        if position.side == "SHORT":
            current_pnl_pct = -current_pnl_pct

        # Get adaptive exit signals
        exit_signal = await self._calculate_exit_signal(
            strategy, position, current_pnl_pct
        )

        return exit_signal

    async def update_strategies(self, calibration_results: Dict[str, Any]) -> None:
        """Update strategies based on calibration results"""

        for strategy_name, results in calibration_results.items():
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]

                # Update performance metrics
                strategy.performance_metrics.update(results.get("performance", {}))

                # Adjust parameters based on results
                parameter_updates = results.get("parameter_updates", {})
                await self._apply_parameter_updates(strategy, parameter_updates)

                # Record adaptation
                strategy.adaptation_history.append(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "CALIBRATION",
                        "performance_before": strategy.performance_metrics,
                        "updates": parameter_updates,
                    }
                )

                strategy.last_adaptation = datetime.now(timezone.utc)

        logger.info(f"Updated {len(calibration_results)} strategies")

    async def optimize_strategies(
        self, recent_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform strategy optimization based on recent performance"""

        optimization_results = {}

        for strategy_name, strategy in self.strategies.items():
            if not strategy.is_active:
                continue

            # Check if optimization is needed
            if not await self._should_optimize_strategy(strategy, recent_performance):
                continue

            # Perform optimization
            optimization_result = await self._optimize_single_strategy(
                strategy, recent_performance
            )
            optimization_results[strategy_name] = optimization_result

        logger.info(f"Optimized {len(optimization_results)} strategies")
        return optimization_results

    async def apply_optimizations(self, optimizations: Dict[str, Any]) -> None:
        """Apply optimization results to strategies"""

        for strategy_name, optimization in optimizations.items():
            if strategy_name not in self.strategies:
                continue

            strategy = self.strategies[strategy_name]

            # Apply parameter changes
            if "parameter_changes" in optimization:
                await self._apply_parameter_updates(
                    strategy, optimization["parameter_changes"]
                )

            # Update confidence score
            if "confidence_score" in optimization:
                strategy.confidence_score = optimization["confidence_score"]

            # Record optimization
            strategy.adaptation_history.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "OPTIMIZATION",
                    "optimization": optimization,
                }
            )

            strategy.last_adaptation = datetime.now(timezone.utc)

        logger.info(f"Applied optimizations to {len(optimizations)} strategies")

    async def _assess_market_conditions(self, symbol: str) -> MarketCondition:
        """Assess current market conditions for a symbol"""

        try:
            # Get recent trades for volatility calculation
            recent_trades = await self.trade_repository.get_trades_by_symbol(
                symbol, limit=50
            )

            if not recent_trades:
                # Return default conditions if no data
                return MarketCondition(
                    volatility=0.2,
                    trend_strength=0.5,
                    volume_profile=0.5,
                    correlation_matrix={},
                    time_of_day=datetime.now(timezone.utc).strftime("%H:%M"),
                    day_of_week=datetime.now(timezone.utc).strftime("%A"),
                    market_phase="SIDEWAYS",
                )

            # Calculate volatility
            prices = [trade.entry_price for trade in recent_trades if trade.entry_price]
            if len(prices) > 1:
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
            else:
                volatility = 0.2

            # Calculate trend strength (simplified)
            if len(prices) > 10:
                recent_prices = prices[-10:]
                trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                trend_strength = abs(trend)
            else:
                trend_strength = 0.5

            # Estimate market phase
            if trend_strength > 0.1:
                market_phase = "BULL" if trend > 0 else "BEAR"
            else:
                market_phase = "SIDEWAYS"

            return MarketCondition(
                volatility=min(volatility, 1.0),
                trend_strength=trend_strength,
                volume_profile=0.5,  # Simplified
                correlation_matrix={},  # Would be calculated with more symbols
                time_of_day=datetime.now(timezone.utc).strftime("%H:%M"),
                day_of_week=datetime.now(timezone.utc).strftime("%A"),
                market_phase=market_phase,
            )

        except Exception as e:
            logger.error(f"Error assessing market conditions: {e}")
            # Return default conditions on error
            return MarketCondition(
                volatility=0.2,
                trend_strength=0.5,
                volume_profile=0.5,
                correlation_matrix={},
                time_of_day=datetime.now(timezone.utc).strftime("%H:%M"),
                day_of_week=datetime.now(timezone.utc).strftime("%A"),
                market_phase="SIDEWAYS",
            )

    async def _calculate_adaptive_adjustments(
        self, strategy: StrategyState, market_conditions: MarketCondition
    ) -> Dict[str, Any]:
        """Calculate adaptive adjustments based on strategy and market conditions"""

        adjustments = {
            "risk_adjustment": 1.0,
            "confidence_adjustment": 1.0,
            "position_size_adjustment": 1.0,
        }

        # Adjust based on strategy confidence
        adjustments["confidence_adjustment"] = strategy.confidence_score

        # Adjust based on market volatility
        if market_conditions.volatility > 0.3:  # High volatility
            adjustments["risk_adjustment"] *= 0.8  # Reduce risk
            adjustments["position_size_adjustment"] *= 0.7
        elif market_conditions.volatility < 0.1:  # Low volatility
            adjustments["risk_adjustment"] *= 1.2  # Increase risk
            adjustments["position_size_adjustment"] *= 1.1

        # Adjust based on market phase
        if market_conditions.market_phase == "BEAR":
            adjustments["risk_adjustment"] *= 0.9
            adjustments["position_size_adjustment"] *= 0.8
        elif market_conditions.market_phase == "BULL":
            adjustments["risk_adjustment"] *= 1.1
            adjustments["position_size_adjustment"] *= 1.1

        # Adjust based on strategy performance
        win_rate = strategy.performance_metrics.get("win_rate", 0.5)
        if win_rate < self.benchmark_win_rate:
            adjustments["position_size_adjustment"] *= 0.8

        # Apply time-based adjustments
        current_hour = int(market_conditions.time_of_day.split(":")[0])
        if 22 <= current_hour or current_hour <= 6:  # Low activity hours
            adjustments["position_size_adjustment"] *= 0.9

        return adjustments

    async def _calculate_exit_signal(
        self, strategy: StrategyState, position, current_pnl_pct: float
    ) -> Dict[str, Any]:
        """Calculate adaptive exit signals for a position"""

        # Base exit logic
        should_exit = False
        reason = ""

        # Profit protection - move stop loss to breakeven
        if current_pnl_pct > 0.01:  # 1% profit
            reason = "PROFIT_PROTECTION"
            should_exit = False  # Just move stop loss

        # Adaptive profit taking based on strategy performance
        profit_target = 0.02  # Base 2% target
        if strategy.performance_metrics.get("win_rate", 0.5) > 0.7:
            profit_target *= 1.5  # Increase target for high-performing strategies

        if current_pnl_pct >= profit_target:
            should_exit = True
            reason = "ADAPTIVE_PROFIT_TARGET"

        # Adaptive stop loss
        max_loss = -0.015  # Base 1.5% max loss
        if strategy.performance_metrics.get("win_rate", 0.5) < 0.5:
            max_loss *= 0.8  # Tighter stop for poor performance

        if current_pnl_pct <= max_loss:
            should_exit = True
            reason = "ADAPTIVE_STOP_LOSS"

        # Time-based exit (don't hold losing positions too long)
        if hasattr(position, "entry_time"):
            duration_hours = (
                datetime.now(timezone.utc) - position.entry_time
            ).total_seconds() / 3600
            if (
                duration_hours > 24 and current_pnl_pct < -0.005
            ):  # Losing position for >24 hours
                should_exit = True
                reason = "TIME_BASED_EXIT"

        return {
            "should_exit": should_exit,
            "reason": reason,
            "current_pnl_pct": current_pnl_pct,
        }

    async def _should_optimize_strategy(
        self, strategy: StrategyState, recent_performance: Dict[str, Any]
    ) -> bool:
        """Determine if a strategy should be optimized"""

        # Check if enough time has passed since last adaptation
        if strategy.last_adaptation:
            time_since_last = (
                datetime.now(timezone.utc) - strategy.last_adaptation
            ).seconds
            if time_since_last < self.max_adaptation_frequency:
                return False

        # Check if we have enough sample data
        strategy_performance = recent_performance.get("strategies", {}).get(
            strategy.strategy_name, {}
        )
        trade_count = strategy_performance.get("total_trades", 0)
        if trade_count < self.min_sample_size:
            return False

        # Check if performance has degraded
        current_win_rate = strategy_performance.get(
            "win_rate", strategy.performance_metrics.get("win_rate", 0.5)
        )
        if current_win_rate < self.benchmark_win_rate - self.adaptation_threshold:
            return True

        # Check if profit factor is low
        profit_factor = strategy_performance.get("profit_factor", 1.0)
        if profit_factor < self.benchmark_profit_factor:
            return True

        return False

    async def _optimize_single_strategy(
        self, strategy: StrategyState, recent_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize a single strategy using machine learning"""

        try:
            # Get historical data for this strategy
            strategy_trades = await self.trade_repository.get_trades_by_strategy(
                strategy.strategy_name, limit=200
            )

            if len(strategy_trades) < 20:
                return {"status": "INSUFFICIENT_DATA"}

            # Prepare features for ML model
            features, labels = self._prepare_training_data(strategy_trades)

            if len(features) < 10:
                return {"status": "INSUFFICIENT_FEATURES"}

            # Train model if not already trained
            if not self.is_trained:
                self.performance_classifier.fit(features, labels)
                self.scaler.fit(features)
                self.is_trained = True

            # Predict optimal parameters
            scaled_features = self.scaler.transform(features)
            feature_importance = self.performance_classifier.feature_importances_

            # Calculate parameter adjustments
            parameter_changes = {}
            for param_name, param in strategy.parameters.items():
                # Simplified parameter optimization
                if param_name in feature_importance:
                    importance = (
                        feature_importance[features[0].index(param_name)]
                        if len(features[0]) > 0
                        else 0.5
                    )
                    adjustment = (importance - 0.5) * param.adjustment_rate
                    new_value = np.clip(
                        param.current_value + adjustment,
                        param.min_value,
                        param.max_value,
                    )
                    parameter_changes[param_name] = new_value

            # Calculate new confidence score
            strategy_performance = recent_performance.get("strategies", {}).get(
                strategy.strategy_name, {}
            )
            win_rate = strategy_performance.get("win_rate", 0.5)
            new_confidence = min(max(win_rate / self.benchmark_win_rate, 0.3), 1.0)

            return {
                "status": "SUCCESS",
                "parameter_changes": parameter_changes,
                "confidence_score": new_confidence,
                "feature_importance": dict(
                    zip(
                        [f"param_{i}" for i in range(len(feature_importance))],
                        feature_importance,
                    )
                ),
                "sample_size": len(strategy_trades),
            }

        except Exception as e:
            logger.error(f"Error optimizing strategy {strategy.strategy_name}: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def _apply_parameter_updates(
        self, strategy: StrategyState, updates: Dict[str, float]
    ) -> None:
        """Apply parameter updates to a strategy"""

        for param_name, new_value in updates.items():
            if param_name in strategy.parameters:
                param = strategy.parameters[param_name]
                # Ensure the new value is within bounds
                param.current_value = np.clip(
                    new_value, param.min_value, param.max_value
                )

    def _prepare_training_data(self, trades) -> Tuple[List[List[float]], List[int]]:
        """Prepare training data from trade history"""

        features = []
        labels = []

        for trade in trades:
            if trade.pnl is None:
                continue

            # Simple feature extraction (would be more sophisticated in practice)
            feature = [
                trade.confidence or 0.5,
                trade.risk_reward_ratio or 1.0,
                float(trade.quantity or 0.0),
                hash(trade.pattern) % 100 / 100.0 if trade.pattern else 0.5,
                hash(trade.timeframe) % 100 / 100.0 if trade.timeframe else 0.5,
            ]

            features.append(feature)
            labels.append(1 if trade.pnl > 0 else 0)  # 1 for win, 0 for loss

        return features, labels

    async def get_strategy_report(self) -> Dict[str, Any]:
        """Get a comprehensive report of all strategies"""

        report = {
            "total_strategies": len(self.strategies),
            "active_strategies": sum(
                1 for s in self.strategies.values() if s.is_active
            ),
            "strategies": {},
            "system_trained": self.is_trained,
        }

        for name, strategy in self.strategies.items():
            report["strategies"][name] = {
                "is_active": strategy.is_active,
                "confidence_score": strategy.confidence_score,
                "parameter_count": len(strategy.parameters),
                "adaptation_count": len(strategy.adaptation_history),
                "last_adaptation": strategy.last_adaptation.isoformat()
                if strategy.last_adaptation
                else None,
                "performance_metrics": strategy.performance_metrics,
                "parameters": {
                    name: {
                        "current_value": param.current_value,
                        "optimal_value": param.optimal_value,
                        "importance": param.importance,
                    }
                    for name, param in strategy.parameters.items()
                },
            }

        return report
