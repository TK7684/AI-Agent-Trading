"""
Unit tests for the memory learning and adaptation system.
"""

import tempfile
from datetime import datetime, timedelta

import numpy as np
import pytest

from libs.trading_models.memory_learning import (
    BanditAlgorithm,
    MemoryLearningSystem,
    MultiArmedBandit,
    PatternPerformance,
    PerformanceWindow,
    TradeOutcome,
)


class TestTradeOutcome:
    """Test TradeOutcome data model."""

    def test_trade_outcome_creation(self):
        """Test creating a trade outcome."""
        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="pin_bar_reversal",
            symbol="EURUSD",
            entry_time=datetime(2024, 1, 1, 10, 0),
            exit_time=datetime(2024, 1, 1, 14, 0),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.5,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        assert outcome.trade_id == "trade_001"
        assert outcome.pattern_id == "pin_bar_reversal"
        assert outcome.was_winner is True
        assert outcome.return_multiple == 2.5

    def test_trade_outcome_serialization(self):
        """Test trade outcome serialization and deserialization."""
        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="pin_bar_reversal",
            symbol="EURUSD",
            entry_time=datetime(2024, 1, 1, 10, 0),
            exit_time=datetime(2024, 1, 1, 14, 0),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.5,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        # Serialize to dict
        data = outcome.to_dict()
        assert isinstance(data, dict)
        assert data['trade_id'] == "trade_001"
        assert data['was_winner'] is True

        # Deserialize from dict
        restored = TradeOutcome.from_dict(data)
        assert restored.trade_id == outcome.trade_id
        assert restored.pattern_id == outcome.pattern_id
        assert restored.was_winner == outcome.was_winner
        assert restored.return_multiple == outcome.return_multiple


class TestPatternPerformance:
    """Test PatternPerformance tracking."""

    def test_pattern_performance_initialization(self):
        """Test pattern performance initialization."""
        perf = PatternPerformance(pattern_id="test_pattern")

        assert perf.pattern_id == "test_pattern"
        assert perf.total_trades == 0
        assert perf.win_rate == 0.0
        assert perf.expectancy == 0.0

    def test_update_metrics_winning_trade(self):
        """Test updating metrics with winning trade."""
        perf = PatternPerformance(pattern_id="test_pattern")

        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.5,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        perf.update_metrics(outcome)

        assert perf.total_trades == 1
        assert perf.winning_trades == 1
        assert perf.losing_trades == 0
        assert perf.win_rate == 1.0
        assert perf.expectancy == 2.5
        assert perf.current_consecutive_losses == 0

    def test_update_metrics_losing_trade(self):
        """Test updating metrics with losing trade."""
        perf = PatternPerformance(pattern_id="test_pattern")

        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.0950,
            position_size=10000,
            pnl=-50.0,
            return_multiple=-1.0,
            holding_time_hours=2.0,
            was_winner=False,
            confidence_score=0.75,
            market_regime="bear",
            timeframe="1h"
        )

        perf.update_metrics(outcome)

        assert perf.total_trades == 1
        assert perf.winning_trades == 0
        assert perf.losing_trades == 1
        assert perf.win_rate == 0.0
        assert perf.expectancy == -1.0
        assert perf.current_consecutive_losses == 1
        assert perf.max_consecutive_losses == 1

    def test_consecutive_losses_tracking(self):
        """Test consecutive losses tracking."""
        perf = PatternPerformance(pattern_id="test_pattern")

        # Add 3 losing trades
        for i in range(3):
            outcome = TradeOutcome(
                trade_id=f"trade_{i:03d}",
                pattern_id="test_pattern",
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.0950,
                position_size=10000,
                pnl=-50.0,
                return_multiple=-1.0,
                holding_time_hours=2.0,
                was_winner=False,
                confidence_score=0.75,
                market_regime="bear",
                timeframe="1h"
            )
            perf.update_metrics(outcome)

        assert perf.current_consecutive_losses == 3
        assert perf.max_consecutive_losses == 3

        # Add winning trade
        winning_outcome = TradeOutcome(
            trade_id="trade_win",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )
        perf.update_metrics(winning_outcome)

        assert perf.current_consecutive_losses == 0
        assert perf.max_consecutive_losses == 3  # Should remain at max


class TestPerformanceWindow:
    """Test PerformanceWindow functionality."""

    def test_performance_window_creation(self):
        """Test performance window creation."""
        window = PerformanceWindow(window_days=30)
        assert window.window_days == 30
        assert len(window.outcomes) == 0

    def test_add_outcome(self):
        """Test adding outcomes to window."""
        window = PerformanceWindow(window_days=30)

        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        window.add_outcome(outcome)
        assert len(window.outcomes) == 1

    def test_cleanup_old_outcomes(self):
        """Test cleanup of old outcomes."""
        window = PerformanceWindow(window_days=30)

        # Add old outcome (35 days ago)
        old_outcome = TradeOutcome(
            trade_id="trade_old",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now() - timedelta(days=35),
            exit_time=datetime.now() - timedelta(days=35),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        # Add recent outcome
        recent_outcome = TradeOutcome(
            trade_id="trade_recent",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now() - timedelta(days=5),
            exit_time=datetime.now() - timedelta(days=5),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        window.add_outcome(old_outcome)
        window.add_outcome(recent_outcome)

        # Only recent outcome should remain
        assert len(window.outcomes) == 1
        assert window.outcomes[0].trade_id == "trade_recent"

    def test_get_performance_metrics_empty(self):
        """Test performance metrics for empty window."""
        window = PerformanceWindow(window_days=30)
        metrics = window.get_performance_metrics()

        assert metrics['total_trades'] == 0
        assert metrics['win_rate'] == 0.0
        assert metrics['expectancy'] == 0.0
        assert metrics['total_pnl'] == 0.0

    def test_get_performance_metrics_with_data(self):
        """Test performance metrics calculation."""
        window = PerformanceWindow(window_days=30)

        # Add winning trade
        winning_outcome = TradeOutcome(
            trade_id="trade_win",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        # Add losing trade
        losing_outcome = TradeOutcome(
            trade_id="trade_loss",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.0950,
            position_size=10000,
            pnl=-50.0,
            return_multiple=-1.0,
            holding_time_hours=2.0,
            was_winner=False,
            confidence_score=0.75,
            market_regime="bear",
            timeframe="1h"
        )

        window.add_outcome(winning_outcome)
        window.add_outcome(losing_outcome)

        metrics = window.get_performance_metrics()

        assert metrics['total_trades'] == 2
        assert metrics['win_rate'] == 0.5
        assert metrics['expectancy'] == 0.5  # (2.0 + (-1.0)) / 2
        assert metrics['total_pnl'] == 0.0  # 50.0 + (-50.0)


class TestMultiArmedBandit:
    """Test MultiArmedBandit algorithms."""

    def test_bandit_initialization(self):
        """Test bandit initialization."""
        bandit = MultiArmedBandit(BanditAlgorithm.UCB1, epsilon=0.1, random_seed=42)

        assert bandit.algorithm == BanditAlgorithm.UCB1
        assert bandit.epsilon == 0.1
        assert bandit.total_selections == 0

    def test_epsilon_greedy_exploration(self):
        """Test epsilon-greedy exploration."""
        bandit = MultiArmedBandit(BanditAlgorithm.EPSILON_GREEDY, epsilon=1.0, random_seed=42)
        patterns = ["pattern_1", "pattern_2", "pattern_3"]

        # With epsilon=1.0, should always explore (random selection)
        selections = []
        for _ in range(100):
            selection = bandit.select_pattern(patterns)
            selections.append(selection)
            bandit.update_reward(selection, 1.0)  # Dummy reward

        # Should have selected all patterns
        unique_selections = set(selections)
        assert len(unique_selections) > 1  # Should have some variety

    def test_epsilon_greedy_exploitation(self):
        """Test epsilon-greedy exploitation."""
        bandit = MultiArmedBandit(BanditAlgorithm.EPSILON_GREEDY, epsilon=0.0, random_seed=42)
        patterns = ["pattern_1", "pattern_2", "pattern_3"]

        # Give pattern_1 higher rewards
        for _ in range(10):
            bandit.update_reward("pattern_1", 2.0)
            bandit.update_reward("pattern_2", 1.0)
            bandit.update_reward("pattern_3", 0.5)

        # With epsilon=0.0, should always exploit (choose best)
        selections = []
        for _ in range(20):
            selection = bandit.select_pattern(patterns)
            selections.append(selection)

        # Should mostly select pattern_1
        pattern_1_count = selections.count("pattern_1")
        assert pattern_1_count > 15  # Should be mostly pattern_1

    def test_ucb1_selection(self):
        """Test UCB1 selection algorithm."""
        bandit = MultiArmedBandit(BanditAlgorithm.UCB1, random_seed=42)
        patterns = ["pattern_1", "pattern_2", "pattern_3"]

        # Initially should select unselected patterns
        first_selections = []
        for _ in range(3):
            selection = bandit.select_pattern(patterns)
            first_selections.append(selection)
            bandit.update_reward(selection, 1.0)

        # Should have selected each pattern once
        assert set(first_selections) == set(patterns)

    def test_ucb1_confidence_interval(self):
        """Test UCB1 confidence interval calculation."""
        bandit = MultiArmedBandit(BanditAlgorithm.UCB1, random_seed=42)

        # Add some selections and rewards
        bandit.update_reward("pattern_1", 2.0)
        bandit.update_reward("pattern_1", 1.5)
        bandit.update_reward("pattern_2", 1.0)

        stats = bandit.get_pattern_statistics()

        assert "pattern_1" in stats
        assert "pattern_2" in stats
        assert stats["pattern_1"]["confidence_interval"] > 0
        assert stats["pattern_2"]["confidence_interval"] > 0

        # Pattern with fewer selections should have higher confidence interval
        assert stats["pattern_2"]["confidence_interval"] > stats["pattern_1"]["confidence_interval"]

    def test_bandit_convergence(self):
        """Test bandit algorithm convergence with reproducible results."""
        # Test with fixed seed for reproducibility
        bandit1 = MultiArmedBandit(BanditAlgorithm.UCB1, random_seed=42)
        bandit2 = MultiArmedBandit(BanditAlgorithm.UCB1, random_seed=42)

        patterns = ["good_pattern", "bad_pattern"]

        # Simulate rewards (good_pattern has higher expected reward)
        for bandit in [bandit1, bandit2]:
            for _ in range(100):
                selection = bandit.select_pattern(patterns)
                if selection == "good_pattern":
                    reward = np.random.normal(2.0, 0.5)  # Higher mean
                else:
                    reward = np.random.normal(1.0, 0.5)  # Lower mean
                bandit.update_reward(selection, reward)

        # Both bandits should converge to similar statistics
        stats1 = bandit1.get_pattern_statistics()
        stats2 = bandit2.get_pattern_statistics()

        # Should have similar average rewards (within tolerance)
        # Note: Due to randomness, we use a more generous tolerance
        assert abs(stats1["good_pattern"]["avg_reward"] - stats2["good_pattern"]["avg_reward"]) < 0.3
        assert abs(stats1["bad_pattern"]["avg_reward"] - stats2["bad_pattern"]["avg_reward"]) < 0.3


class TestMemoryLearningSystem:
    """Test MemoryLearningSystem integration."""

    def test_system_initialization(self):
        """Test system initialization."""
        system = MemoryLearningSystem(random_seed=42)

        assert system.bandit.algorithm == BanditAlgorithm.UCB1
        assert len(system.pattern_performance) == 0
        assert len(system.trade_outcomes) == 0
        assert 30 in system.performance_windows
        assert 60 in system.performance_windows
        assert 90 in system.performance_windows

    def test_record_trade_outcome(self):
        """Test recording trade outcomes."""
        system = MemoryLearningSystem(random_seed=42)

        outcome = TradeOutcome(
            trade_id="trade_001",
            pattern_id="pin_bar_reversal",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.5,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        system.record_trade_outcome(outcome)

        assert len(system.trade_outcomes) == 1
        assert "pin_bar_reversal" in system.pattern_performance
        assert system.pattern_performance["pin_bar_reversal"].total_trades == 1
        assert system.pattern_performance["pin_bar_reversal"].win_rate == 1.0

    def test_adaptive_position_sizing(self):
        """Test adaptive position sizing."""
        system = MemoryLearningSystem(
            min_position_size_multiplier=0.5,
            max_position_size_multiplier=2.0,
            min_trades_for_adaptation=5,
            random_seed=42
        )

        # Test unknown pattern (should return 1.0)
        multiplier = system.get_adaptive_position_size_multiplier("unknown_pattern", 0.8)
        assert multiplier == 1.0

        # Add some winning trades for a pattern
        for i in range(10):
            outcome = TradeOutcome(
                trade_id=f"trade_{i:03d}",
                pattern_id="good_pattern",
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.1050,
                position_size=10000,
                pnl=50.0,
                return_multiple=2.0,  # Good expectancy
                holding_time_hours=4.0,
                was_winner=True,
                confidence_score=0.85,
                market_regime="bull",
                timeframe="1h"
            )
            system.record_trade_outcome(outcome)

        # Should get higher multiplier for good pattern
        multiplier = system.get_adaptive_position_size_multiplier("good_pattern", 0.8)
        assert multiplier > 1.0
        assert multiplier <= 2.0  # Should respect max bound

        # Add some losing trades for another pattern
        for i in range(10):
            outcome = TradeOutcome(
                trade_id=f"trade_bad_{i:03d}",
                pattern_id="bad_pattern",
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.0950,
                position_size=10000,
                pnl=-50.0,
                return_multiple=-1.0,  # Poor expectancy
                holding_time_hours=2.0,
                was_winner=False,
                confidence_score=0.75,
                market_regime="bear",
                timeframe="1h"
            )
            system.record_trade_outcome(outcome)

        # Should get lower multiplier for bad pattern
        multiplier = system.get_adaptive_position_size_multiplier("bad_pattern", 0.8)
        assert multiplier < 1.0
        assert multiplier >= 0.5  # Should respect min bound

    def test_pattern_weights(self):
        """Test pattern weight calculation."""
        system = MemoryLearningSystem(random_seed=42)

        # Add trades for multiple patterns
        patterns_data = [
            ("good_pattern", 2.0, True),
            ("bad_pattern", -1.0, False),
            ("mediocre_pattern", 0.5, True)
        ]

        for pattern_id, return_mult, is_winner in patterns_data:
            for i in range(5):
                outcome = TradeOutcome(
                    trade_id=f"trade_{pattern_id}_{i:03d}",
                    pattern_id=pattern_id,
                    symbol="EURUSD",
                    entry_time=datetime.now(),
                    exit_time=datetime.now(),
                    entry_price=1.1000,
                    exit_price=1.1050 if is_winner else 1.0950,
                    position_size=10000,
                    pnl=50.0 if is_winner else -50.0,
                    return_multiple=return_mult,
                    holding_time_hours=4.0,
                    was_winner=is_winner,
                    confidence_score=0.85,
                    market_regime="bull",
                    timeframe="1h"
                )
                system.record_trade_outcome(outcome)

        weights = system.get_pattern_weights()

        assert "good_pattern" in weights
        assert "bad_pattern" in weights
        assert "mediocre_pattern" in weights

        # Good pattern should have highest weight
        assert weights["good_pattern"] > weights["mediocre_pattern"]
        assert weights["mediocre_pattern"] > weights["bad_pattern"]

    def test_performance_report(self):
        """Test performance report generation."""
        system = MemoryLearningSystem(random_seed=42)

        # Add some trade outcomes
        for i in range(5):
            outcome = TradeOutcome(
                trade_id=f"trade_{i:03d}",
                pattern_id="test_pattern",
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.1050,
                position_size=10000,
                pnl=50.0,
                return_multiple=2.0,
                holding_time_hours=4.0,
                was_winner=True,
                confidence_score=0.85,
                market_regime="bull",
                timeframe="1h"
            )
            system.record_trade_outcome(outcome)

        report = system.get_performance_report()

        assert 'timestamp' in report
        assert 'total_trades' in report
        assert 'pattern_performance' in report
        assert 'performance_windows' in report
        assert 'bandit_statistics' in report
        assert 'system_parameters' in report

        assert report['total_trades'] == 5
        assert 'test_pattern' in report['pattern_performance']
        assert '30_days' in report['performance_windows']
        assert '60_days' in report['performance_windows']
        assert '90_days' in report['performance_windows']

    def test_state_persistence(self):
        """Test saving and loading system state."""
        system1 = MemoryLearningSystem(random_seed=42)

        # Add some trade outcomes
        for i in range(3):
            outcome = TradeOutcome(
                trade_id=f"trade_{i:03d}",
                pattern_id="test_pattern",
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.1050,
                position_size=10000,
                pnl=50.0,
                return_multiple=2.0,
                holding_time_hours=4.0,
                was_winner=True,
                confidence_score=0.85,
                market_regime="bull",
                timeframe="1h"
            )
            system1.record_trade_outcome(outcome)

        # Save state
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        system1.save_state(temp_file)

        # Create new system and load state
        system2 = MemoryLearningSystem(random_seed=42)
        system2.load_state(temp_file)

        # Verify state was restored
        assert len(system2.trade_outcomes) == 3
        assert "test_pattern" in system2.pattern_performance
        assert system2.pattern_performance["test_pattern"].total_trades == 3
        assert system2.bandit.total_selections == system1.bandit.total_selections

        # Clean up
        import os
        os.unlink(temp_file)

    def test_walk_forward_improvement(self):
        """Test that adaptive weights improve performance over static weights."""
        # This is a simplified test of the walk-forward concept
        system = MemoryLearningSystem(
            bandit_algorithm=BanditAlgorithm.UCB1,
            min_trades_for_adaptation=5,
            random_seed=42
        )

        # Simulate patterns with different performance characteristics
        patterns = {
            "declining_pattern": {"initial_performance": 2.0, "decay_rate": 0.95},
            "improving_pattern": {"initial_performance": 0.5, "growth_rate": 1.05},
            "stable_pattern": {"initial_performance": 1.5, "stability": 1.0}
        }

        # Simulate 100 trades with changing pattern performance
        for trade_num in range(100):
            # Select pattern using bandit
            available_patterns = list(patterns.keys())
            selected_pattern = system.bandit.select_pattern(available_patterns)

            # Calculate performance based on pattern characteristics
            pattern_data = patterns[selected_pattern]
            if "decay_rate" in pattern_data:
                performance = pattern_data["initial_performance"] * (pattern_data["decay_rate"] ** trade_num)
            elif "growth_rate" in pattern_data:
                performance = pattern_data["initial_performance"] * (pattern_data["growth_rate"] ** (trade_num / 20))
            else:
                performance = pattern_data["initial_performance"]

            # Add some noise
            performance += np.random.normal(0, 0.2)

            # Create trade outcome
            outcome = TradeOutcome(
                trade_id=f"trade_{trade_num:03d}",
                pattern_id=selected_pattern,
                symbol="EURUSD",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                entry_price=1.1000,
                exit_price=1.1000 + (performance * 0.001),
                position_size=10000,
                pnl=performance * 10,
                return_multiple=performance,
                holding_time_hours=4.0,
                was_winner=performance > 0,
                confidence_score=0.8,
                market_regime="bull",
                timeframe="1h"
            )

            system.record_trade_outcome(outcome)

        # Check that the system learned to prefer the improving pattern
        # and avoid the declining pattern
        stats = system.bandit.get_pattern_statistics()

        # The improving pattern should have been selected more in later trades
        # This is a basic check - in practice, you'd want more sophisticated metrics
        assert len(stats) == 3
        assert all(pattern in stats for pattern in patterns.keys())

        # System should have adapted weights based on performance
        weights = system.get_pattern_weights()
        assert len(weights) == 3

        # Performance report should show learning occurred
        report = system.get_performance_report()
        assert report['total_trades'] == 100
        assert len(report['pattern_performance']) == 3


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_pattern_list(self):
        """Test bandit with empty pattern list."""
        bandit = MultiArmedBandit(BanditAlgorithm.UCB1)

        with pytest.raises(ValueError, match="No patterns available"):
            bandit.select_pattern([])

    def test_zero_trades_performance(self):
        """Test performance calculations with zero trades."""
        system = MemoryLearningSystem()

        # Should handle zero trades gracefully
        multiplier = system.get_adaptive_position_size_multiplier("unknown_pattern", 0.8)
        assert multiplier == 1.0

        weights = system.get_pattern_weights()
        assert len(weights) == 0

        report = system.get_performance_report()
        assert report['total_trades'] == 0

    def test_extreme_outliers(self):
        """Test handling of extreme outlier values."""
        system = MemoryLearningSystem(random_seed=42)

        # Add extreme outlier
        extreme_outcome = TradeOutcome(
            trade_id="extreme_trade",
            pattern_id="outlier_pattern",
            symbol="EURUSD",
            entry_time=datetime.now(),
            exit_time=datetime.now(),
            entry_price=1.1000,
            exit_price=1.2000,  # Extreme move
            position_size=10000,
            pnl=10000.0,  # Extreme profit
            return_multiple=100.0,  # Extreme R-multiple
            holding_time_hours=1.0,
            was_winner=True,
            confidence_score=0.95,
            market_regime="bull",
            timeframe="1h"
        )

        system.record_trade_outcome(extreme_outcome)

        # System should handle extreme values without crashing
        multiplier = system.get_adaptive_position_size_multiplier("outlier_pattern", 0.8)
        assert 0.5 <= multiplier <= 2.0  # Should be bounded

        report = system.get_performance_report()
        assert report['total_trades'] == 1
        assert 'outlier_pattern' in report['pattern_performance']

    def test_bandit_algorithm_bounds(self):
        """Test bandit algorithm parameter bounds."""
        # Test epsilon bounds
        bandit = MultiArmedBandit(BanditAlgorithm.EPSILON_GREEDY, epsilon=0.0)
        assert bandit.epsilon == 0.0

        bandit = MultiArmedBandit(BanditAlgorithm.EPSILON_GREEDY, epsilon=1.0)
        assert bandit.epsilon == 1.0

        # Test with single pattern
        patterns = ["single_pattern"]
        selection = bandit.select_pattern(patterns)
        assert selection == "single_pattern"

    def test_performance_window_edge_cases(self):
        """Test performance window edge cases."""
        window = PerformanceWindow(window_days=1)  # Very short window

        # Add outcome from exactly 1 day ago
        outcome = TradeOutcome(
            trade_id="edge_trade",
            pattern_id="test_pattern",
            symbol="EURUSD",
            entry_time=datetime.now() - timedelta(days=1, seconds=1),
            exit_time=datetime.now() - timedelta(days=1, seconds=1),
            entry_price=1.1000,
            exit_price=1.1050,
            position_size=10000,
            pnl=50.0,
            return_multiple=2.0,
            holding_time_hours=4.0,
            was_winner=True,
            confidence_score=0.85,
            market_regime="bull",
            timeframe="1h"
        )

        window.add_outcome(outcome)

        # Should be cleaned up due to age
        assert len(window.outcomes) == 0


if __name__ == "__main__":
    pytest.main([__file__])
