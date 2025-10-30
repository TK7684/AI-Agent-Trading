"""
Self-learning memory and adaptation system for autonomous trading.

This module implements multi-armed bandit algorithms, performance tracking,
and adaptive position sizing based on historical trade outcomes.
"""

import json
import math
import random
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import numpy as np
from pydantic import Field

from .base import BaseModel


class BanditAlgorithm(Enum):
    """Available multi-armed bandit algorithms."""
    EPSILON_GREEDY = "epsilon_greedy"
    UCB1 = "ucb1"


class TradeOutcome(BaseModel):
    """Represents the outcome of a completed trade."""
    trade_id: str
    pattern_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    return_multiple: float  # R-multiple (PnL / risk)
    holding_time_hours: float
    was_winner: bool
    confidence_score: float
    market_regime: str
    timeframe: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'trade_id': self.trade_id,
            'pattern_id': self.pattern_id,
            'symbol': self.symbol,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'position_size': self.position_size,
            'pnl': self.pnl,
            'return_multiple': self.return_multiple,
            'holding_time_hours': self.holding_time_hours,
            'was_winner': self.was_winner,
            'confidence_score': self.confidence_score,
            'market_regime': self.market_regime,
            'timeframe': self.timeframe
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TradeOutcome':
        """Create from dictionary."""
        return cls(
            trade_id=data['trade_id'],
            pattern_id=data['pattern_id'],
            symbol=data['symbol'],
            entry_time=datetime.fromisoformat(data['entry_time']),
            exit_time=datetime.fromisoformat(data['exit_time']),
            entry_price=data['entry_price'],
            exit_price=data['exit_price'],
            position_size=data['position_size'],
            pnl=data['pnl'],
            return_multiple=data['return_multiple'],
            holding_time_hours=data['holding_time_hours'],
            was_winner=data['was_winner'],
            confidence_score=data['confidence_score'],
            market_regime=data['market_regime'],
            timeframe=data['timeframe']
        )


class PatternPerformance(BaseModel):
    """Performance metrics for a specific pattern."""
    pattern_id: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_return_multiple: float = 0.0
    expectancy: float = 0.0  # Average R-multiple
    avg_holding_time_hours: float = 0.0
    max_consecutive_losses: int = 0
    current_consecutive_losses: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

    # Bandit algorithm specific
    weight: float = 1.0
    confidence_interval: float = 0.0

    def update_metrics(self, outcome: TradeOutcome) -> None:
        """Update performance metrics with new trade outcome."""
        self.total_trades += 1
        self.total_pnl += outcome.pnl
        self.total_return_multiple += outcome.return_multiple

        if outcome.was_winner:
            self.winning_trades += 1
            self.current_consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.current_consecutive_losses += 1
            self.max_consecutive_losses = max(
                self.max_consecutive_losses,
                self.current_consecutive_losses
            )

        # Recalculate derived metrics
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        self.expectancy = self.total_return_multiple / self.total_trades if self.total_trades > 0 else 0.0

        # Update average holding time (weighted average)
        if self.total_trades == 1:
            self.avg_holding_time_hours = outcome.holding_time_hours
        else:
            # Weighted average with more weight on recent trades
            weight = 0.1  # 10% weight for new trade
            self.avg_holding_time_hours = (
                (1 - weight) * self.avg_holding_time_hours +
                weight * outcome.holding_time_hours
            )

        self.last_updated = datetime.now()


class PerformanceWindow:
    """Rolling performance window for strategy calibration."""

    def __init__(self, window_days: int):
        self.window_days = window_days
        self.outcomes: deque = deque()

    def add_outcome(self, outcome: TradeOutcome) -> None:
        """Add new trade outcome to the window."""
        self.outcomes.append(outcome)
        self._cleanup_old_outcomes()

    def _cleanup_old_outcomes(self) -> None:
        """Remove outcomes older than window_days."""
        cutoff_time = datetime.now() - timedelta(days=self.window_days)
        while self.outcomes and self.outcomes[0].exit_time < cutoff_time:
            self.outcomes.popleft()

    def get_performance_metrics(self) -> dict[str, float]:
        """Calculate performance metrics for current window."""
        if not self.outcomes:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'expectancy': 0.0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }

        total_trades = len(self.outcomes)
        winning_trades = sum(1 for o in self.outcomes if o.was_winner)
        win_rate = winning_trades / total_trades

        returns = [o.return_multiple for o in self.outcomes]
        expectancy = np.mean(returns)
        total_pnl = sum(o.pnl for o in self.outcomes)

        # Calculate Sharpe ratio (assuming daily returns)
        if len(returns) > 1:
            std_returns = np.std(returns)
            if std_returns > 0:
                sharpe_ratio = np.mean(returns) / std_returns * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Calculate maximum drawdown
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'expectancy': expectancy,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown
        }


class MultiArmedBandit:
    """Multi-armed bandit algorithm for pattern weight optimization."""

    def __init__(self, algorithm: BanditAlgorithm = BanditAlgorithm.UCB1,
                 epsilon: float = 0.1, random_seed: Optional[int] = None):
        self.algorithm = algorithm
        self.epsilon = epsilon
        self.total_selections = 0
        self.pattern_selections: dict[str, int] = defaultdict(int)
        self.pattern_rewards: dict[str, list[float]] = defaultdict(list)

        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

    def select_pattern(self, available_patterns: list[str]) -> str:
        """Select a pattern using the configured bandit algorithm."""
        if not available_patterns:
            raise ValueError("No patterns available for selection")

        if self.algorithm == BanditAlgorithm.EPSILON_GREEDY:
            return self._epsilon_greedy_select(available_patterns)
        elif self.algorithm == BanditAlgorithm.UCB1:
            return self._ucb1_select(available_patterns)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")

    def update_reward(self, pattern_id: str, reward: float) -> None:
        """Update the reward for a pattern based on trade outcome."""
        self.pattern_rewards[pattern_id].append(reward)
        self.pattern_selections[pattern_id] += 1
        self.total_selections += 1

    def _epsilon_greedy_select(self, patterns: list[str]) -> str:
        """Epsilon-greedy pattern selection."""
        # Explore with probability epsilon
        if random.random() < self.epsilon:
            return random.choice(patterns)

        # Exploit: choose pattern with highest average reward
        best_pattern = None
        best_avg_reward = float('-inf')

        for pattern in patterns:
            if pattern not in self.pattern_rewards or not self.pattern_rewards[pattern]:
                # Unselected patterns get priority
                return pattern

            avg_reward = np.mean(self.pattern_rewards[pattern])
            if avg_reward > best_avg_reward:
                best_avg_reward = avg_reward
                best_pattern = pattern

        return best_pattern or random.choice(patterns)

    def _ucb1_select(self, patterns: list[str]) -> str:
        """UCB1 (Upper Confidence Bound) pattern selection."""
        if self.total_selections == 0:
            return random.choice(patterns)

        best_pattern = None
        best_ucb_value = float('-inf')

        for pattern in patterns:
            if pattern not in self.pattern_rewards or not self.pattern_rewards[pattern]:
                # Unselected patterns get infinite UCB value
                return pattern

            avg_reward = np.mean(self.pattern_rewards[pattern])
            n_selections = self.pattern_selections[pattern]

            # UCB1 formula
            confidence_interval = math.sqrt(
                (2 * math.log(self.total_selections)) / n_selections
            )
            ucb_value = avg_reward + confidence_interval

            if ucb_value > best_ucb_value:
                best_ucb_value = ucb_value
                best_pattern = pattern

        return best_pattern or random.choice(patterns)

    def get_pattern_statistics(self) -> dict[str, dict[str, float]]:
        """Get statistics for all patterns."""
        stats = {}
        for pattern_id in self.pattern_rewards:
            rewards = self.pattern_rewards[pattern_id]
            if rewards:
                stats[pattern_id] = {
                    'avg_reward': np.mean(rewards),
                    'std_reward': np.std(rewards),
                    'total_selections': self.pattern_selections[pattern_id],
                    'confidence_interval': self._calculate_confidence_interval(pattern_id)
                }
        return stats

    def _calculate_confidence_interval(self, pattern_id: str) -> float:
        """Calculate confidence interval for UCB1."""
        if self.total_selections == 0 or pattern_id not in self.pattern_selections:
            return float('inf')

        n_selections = self.pattern_selections[pattern_id]
        if n_selections == 0:
            return float('inf')

        return math.sqrt((2 * math.log(self.total_selections)) / n_selections)


class MemoryLearningSystem:
    """Main system for self-learning memory and adaptation."""

    def __init__(self,
                 bandit_algorithm: BanditAlgorithm = BanditAlgorithm.UCB1,
                 epsilon: float = 0.1,
                 min_position_size_multiplier: float = 0.5,
                 max_position_size_multiplier: float = 2.0,
                 performance_window_days: int = 60,
                 min_trades_for_adaptation: int = 10,
                 random_seed: Optional[int] = None):

        self.bandit = MultiArmedBandit(bandit_algorithm, epsilon, random_seed)
        self.pattern_performance: dict[str, PatternPerformance] = {}
        self.trade_outcomes: list[TradeOutcome] = []
        self.performance_windows = {
            30: PerformanceWindow(30),
            60: PerformanceWindow(60),
            90: PerformanceWindow(90)
        }

        # Position sizing parameters
        self.min_position_size_multiplier = min_position_size_multiplier
        self.max_position_size_multiplier = max_position_size_multiplier
        self.min_trades_for_adaptation = min_trades_for_adaptation

        # Performance tracking
        self.last_calibration = datetime.now()
        self.calibration_interval = timedelta(days=1)

    def record_trade_outcome(self, outcome: TradeOutcome) -> None:
        """Record a completed trade outcome and update all metrics."""
        self.trade_outcomes.append(outcome)

        # Update pattern performance
        if outcome.pattern_id not in self.pattern_performance:
            self.pattern_performance[outcome.pattern_id] = PatternPerformance(
                pattern_id=outcome.pattern_id
            )

        self.pattern_performance[outcome.pattern_id].update_metrics(outcome)

        # Update bandit algorithm
        reward = outcome.return_multiple  # Use R-multiple as reward
        self.bandit.update_reward(outcome.pattern_id, reward)

        # Update performance windows
        for window in self.performance_windows.values():
            window.add_outcome(outcome)

        # Check if calibration is needed
        if datetime.now() - self.last_calibration > self.calibration_interval:
            self.calibrate_system()

    def get_adaptive_position_size_multiplier(self, pattern_id: str,
                                            base_confidence: float) -> float:
        """Calculate adaptive position size multiplier based on pattern performance."""
        if pattern_id not in self.pattern_performance:
            return 1.0  # Default multiplier for unknown patterns

        performance = self.pattern_performance[pattern_id]

        # Need minimum trades for adaptation
        if performance.total_trades < self.min_trades_for_adaptation:
            return 1.0

        # Base multiplier on expectancy and win rate
        expectancy_factor = max(0.1, min(2.0, performance.expectancy))
        win_rate_factor = max(0.5, min(1.5, performance.win_rate * 2))
        confidence_factor = max(0.8, min(1.2, base_confidence))

        # Combine factors
        multiplier = expectancy_factor * win_rate_factor * confidence_factor

        # Apply bounds
        multiplier = max(self.min_position_size_multiplier,
                        min(self.max_position_size_multiplier, multiplier))

        return multiplier

    def get_pattern_weights(self) -> dict[str, float]:
        """Get current pattern weights based on performance."""
        weights = {}
        bandit_stats = self.bandit.get_pattern_statistics()

        for pattern_id, performance in self.pattern_performance.items():
            if pattern_id in bandit_stats:
                # Combine expectancy with bandit statistics
                base_weight = max(0.1, performance.expectancy)
                bandit_weight = bandit_stats[pattern_id]['avg_reward']

                # Weighted combination
                weights[pattern_id] = 0.7 * base_weight + 0.3 * bandit_weight
            else:
                weights[pattern_id] = max(0.1, performance.expectancy)

        return weights

    def calibrate_system(self) -> None:
        """Perform system calibration based on recent performance."""
        self.last_calibration = datetime.now()

        # Update pattern weights based on recent performance
        for pattern_id, performance in self.pattern_performance.items():
            if performance.total_trades >= self.min_trades_for_adaptation:
                # Adjust bandit epsilon based on performance stability
                recent_outcomes = [
                    o for o in self.trade_outcomes[-50:]
                    if o.pattern_id == pattern_id
                ]

                if len(recent_outcomes) >= 10:
                    recent_returns = [o.return_multiple for o in recent_outcomes]
                    volatility = np.std(recent_returns)

                    # Higher volatility = more exploration
                    if volatility > 1.5:
                        self.bandit.epsilon = min(0.3, self.bandit.epsilon * 1.1)
                    elif volatility < 0.5:
                        self.bandit.epsilon = max(0.05, self.bandit.epsilon * 0.9)

    def get_performance_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(self.trade_outcomes),
            'pattern_performance': {},
            'performance_windows': {},
            'bandit_statistics': self.bandit.get_pattern_statistics(),
            'system_parameters': {
                'bandit_algorithm': self.bandit.algorithm.value,
                'epsilon': self.bandit.epsilon,
                'min_position_multiplier': self.min_position_size_multiplier,
                'max_position_multiplier': self.max_position_size_multiplier,
                'min_trades_for_adaptation': self.min_trades_for_adaptation
            }
        }

        # Pattern performance
        for pattern_id, performance in self.pattern_performance.items():
            report['pattern_performance'][pattern_id] = {
                'total_trades': performance.total_trades,
                'win_rate': performance.win_rate,
                'expectancy': performance.expectancy,
                'avg_holding_time_hours': performance.avg_holding_time_hours,
                'max_consecutive_losses': performance.max_consecutive_losses,
                'current_weight': performance.weight
            }

        # Performance windows
        for days, window in self.performance_windows.items():
            report['performance_windows'][f'{days}_days'] = window.get_performance_metrics()

        return report

    def save_state(self, filepath: str) -> None:
        """Save system state to file."""
        state = {
            'pattern_performance': {
                pid: {
                    'pattern_id': p.pattern_id,
                    'total_trades': p.total_trades,
                    'winning_trades': p.winning_trades,
                    'losing_trades': p.losing_trades,
                    'win_rate': p.win_rate,
                    'total_pnl': p.total_pnl,
                    'total_return_multiple': p.total_return_multiple,
                    'expectancy': p.expectancy,
                    'avg_holding_time_hours': p.avg_holding_time_hours,
                    'max_consecutive_losses': p.max_consecutive_losses,
                    'current_consecutive_losses': p.current_consecutive_losses,
                    'last_updated': p.last_updated.isoformat(),
                    'weight': p.weight,
                    'confidence_interval': p.confidence_interval
                }
                for pid, p in self.pattern_performance.items()
            },
            'trade_outcomes': [outcome.to_dict() for outcome in self.trade_outcomes],
            'bandit_state': {
                'algorithm': self.bandit.algorithm.value,
                'epsilon': self.bandit.epsilon,
                'total_selections': self.bandit.total_selections,
                'pattern_selections': dict(self.bandit.pattern_selections),
                'pattern_rewards': {k: list(v) for k, v in self.bandit.pattern_rewards.items()}
            }
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: str) -> None:
        """Load system state from file."""
        with open(filepath) as f:
            state = json.load(f)

        # Restore pattern performance
        self.pattern_performance = {}
        for pid, p_data in state['pattern_performance'].items():
            perf = PatternPerformance(
                pattern_id=p_data['pattern_id'],
                total_trades=p_data['total_trades'],
                winning_trades=p_data['winning_trades'],
                losing_trades=p_data['losing_trades'],
                win_rate=p_data['win_rate'],
                total_pnl=p_data['total_pnl'],
                total_return_multiple=p_data['total_return_multiple'],
                expectancy=p_data['expectancy'],
                avg_holding_time_hours=p_data['avg_holding_time_hours'],
                max_consecutive_losses=p_data['max_consecutive_losses'],
                current_consecutive_losses=p_data['current_consecutive_losses'],
                last_updated=datetime.fromisoformat(p_data['last_updated']),
                weight=p_data['weight'],
                confidence_interval=p_data['confidence_interval']
            )
            self.pattern_performance[pid] = perf

        # Restore trade outcomes
        self.trade_outcomes = [
            TradeOutcome.from_dict(outcome_data)
            for outcome_data in state['trade_outcomes']
        ]

        # Restore bandit state
        bandit_state = state['bandit_state']
        self.bandit.algorithm = BanditAlgorithm(bandit_state['algorithm'])
        self.bandit.epsilon = bandit_state['epsilon']
        self.bandit.total_selections = bandit_state['total_selections']
        self.bandit.pattern_selections = defaultdict(int, bandit_state['pattern_selections'])
        self.bandit.pattern_rewards = defaultdict(list, {
            k: list(v) for k, v in bandit_state['pattern_rewards'].items()
        })

        # Rebuild performance windows
        for window in self.performance_windows.values():
            window.outcomes.clear()
            for outcome in self.trade_outcomes:
                window.add_outcome(outcome)
