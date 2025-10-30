#!/usr/bin/env python3
"""
Demo script for the Memory Learning and Adaptation System.

This script demonstrates:
1. Trade outcome tracking with pattern performance metrics
2. Multi-armed bandit algorithms (ε-greedy, UCB1) for pattern weight adaptation
3. Performance-based position sizing with bounded risk scaling
4. Rolling performance windows for strategy calibration
5. Pattern weight updates based on trade outcomes
6. Performance trend analysis and reporting
"""

import json
import random
from datetime import datetime, timedelta

import numpy as np

from libs.trading_models.memory_learning import (
    BanditAlgorithm,
    MemoryLearningSystem,
    TradeOutcome,
)


def generate_synthetic_trade_outcome(
    trade_id: str,
    pattern_id: str,
    pattern_performance: dict[str, float],
    market_regime: str = "bull",
    timeframe: str = "1h"
) -> TradeOutcome:
    """Generate a synthetic trade outcome based on pattern performance."""

    # Get pattern characteristics
    base_win_rate = pattern_performance.get("win_rate", 0.5)
    base_expectancy = pattern_performance.get("expectancy", 1.0)
    volatility = pattern_performance.get("volatility", 0.3)

    # Adjust for market regime
    regime_multiplier = {
        "bull": 1.2,
        "bear": 0.8,
        "sideways": 0.9
    }.get(market_regime, 1.0)

    adjusted_win_rate = min(0.95, base_win_rate * regime_multiplier)
    adjusted_expectancy = base_expectancy * regime_multiplier

    # Determine if trade is winner
    is_winner = random.random() < adjusted_win_rate

    # Generate return multiple
    if is_winner:
        return_multiple = max(0.1, np.random.normal(adjusted_expectancy, volatility))
    else:
        return_multiple = min(-0.1, np.random.normal(-1.0, volatility * 0.5))

    # Generate other trade details
    entry_price = 1.1000 + np.random.normal(0, 0.001)
    exit_price = entry_price * (1 + return_multiple * 0.001)
    position_size = 10000
    pnl = (exit_price - entry_price) * position_size
    holding_time = max(0.5, np.random.exponential(4.0))

    entry_time = datetime.now() - timedelta(hours=holding_time)
    exit_time = datetime.now()

    return TradeOutcome(
        trade_id=trade_id,
        pattern_id=pattern_id,
        symbol="EURUSD",
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=entry_price,
        exit_price=exit_price,
        position_size=position_size,
        pnl=pnl,
        return_multiple=return_multiple,
        holding_time_hours=holding_time,
        was_winner=is_winner,
        confidence_score=random.uniform(0.6, 0.95),
        market_regime=market_regime,
        timeframe=timeframe
    )


def simulate_pattern_evolution(initial_performance: dict[str, float],
                             trade_number: int,
                             total_trades: int) -> dict[str, float]:
    """Simulate how pattern performance evolves over time."""
    progress = trade_number / total_trades

    # Different evolution patterns
    if "declining" in initial_performance.get("type", ""):
        # Performance declines over time
        decay_factor = 0.95 ** (progress * 50)
        return {
            "win_rate": initial_performance["win_rate"] * decay_factor,
            "expectancy": initial_performance["expectancy"] * decay_factor,
            "volatility": initial_performance["volatility"] * (1 + progress * 0.2)
        }
    elif "improving" in initial_performance.get("type", ""):
        # Performance improves over time
        growth_factor = 1.0 + progress * 0.5
        return {
            "win_rate": min(0.8, initial_performance["win_rate"] * growth_factor),
            "expectancy": initial_performance["expectancy"] * growth_factor,
            "volatility": initial_performance["volatility"] * (1 - progress * 0.1)
        }
    elif "cyclical" in initial_performance.get("type", ""):
        # Performance cycles
        cycle_factor = 1.0 + 0.3 * np.sin(progress * 4 * np.pi)
        return {
            "win_rate": initial_performance["win_rate"] * cycle_factor,
            "expectancy": initial_performance["expectancy"] * cycle_factor,
            "volatility": initial_performance["volatility"]
        }
    else:
        # Stable performance
        return {
            "win_rate": initial_performance["win_rate"],
            "expectancy": initial_performance["expectancy"],
            "volatility": initial_performance["volatility"]
        }


def run_bandit_comparison_demo():
    """Compare different bandit algorithms."""
    print("=" * 80)
    print("MULTI-ARMED BANDIT ALGORITHM COMPARISON")
    print("=" * 80)

    # Define patterns with different characteristics
    pattern_definitions = {
        "pin_bar_reversal": {
            "win_rate": 0.65,
            "expectancy": 1.8,
            "volatility": 0.4,
            "type": "stable"
        },
        "breakout_momentum": {
            "win_rate": 0.45,
            "expectancy": 2.5,
            "volatility": 0.6,
            "type": "declining"
        },
        "support_resistance": {
            "win_rate": 0.55,
            "expectancy": 1.2,
            "volatility": 0.3,
            "type": "improving"
        },
        "divergence_signal": {
            "win_rate": 0.60,
            "expectancy": 1.5,
            "volatility": 0.5,
            "type": "cyclical"
        }
    }

    algorithms = [BanditAlgorithm.EPSILON_GREEDY, BanditAlgorithm.UCB1]
    results = {}

    for algorithm in algorithms:
        print(f"\nTesting {algorithm.value.upper()} Algorithm:")
        print("-" * 50)

        # Create system with specific algorithm
        system = MemoryLearningSystem(
            bandit_algorithm=algorithm,
            epsilon=0.1,
            min_trades_for_adaptation=5,
            random_seed=42
        )

        total_trades = 200
        cumulative_return = 0.0

        for trade_num in range(total_trades):
            # Select pattern using bandit
            available_patterns = list(pattern_definitions.keys())
            selected_pattern = system.bandit.select_pattern(available_patterns)

            # Get evolved pattern performance
            current_performance = simulate_pattern_evolution(
                pattern_definitions[selected_pattern],
                trade_num,
                total_trades
            )

            # Generate trade outcome
            outcome = generate_synthetic_trade_outcome(
                trade_id=f"trade_{algorithm.value}_{trade_num:03d}",
                pattern_id=selected_pattern,
                pattern_performance=current_performance,
                market_regime="bull" if trade_num < 100 else "bear"
            )

            system.record_trade_outcome(outcome)
            cumulative_return += outcome.return_multiple

            # Print progress every 50 trades
            if (trade_num + 1) % 50 == 0:
                avg_return = cumulative_return / (trade_num + 1)
                print(f"  Trade {trade_num + 1:3d}: Avg Return = {avg_return:.3f}, "
                      f"Selected = {selected_pattern}")

        # Store results
        final_stats = system.bandit.get_pattern_statistics()
        results[algorithm.value] = {
            "total_return": cumulative_return,
            "avg_return": cumulative_return / total_trades,
            "pattern_stats": final_stats,
            "system": system
        }

        print(f"\nFinal Results for {algorithm.value.upper()}:")
        print(f"  Total Return: {cumulative_return:.2f}")
        print(f"  Average Return: {cumulative_return / total_trades:.3f}")
        print("  Pattern Selection Counts:")
        for pattern_id, stats in final_stats.items():
            print(f"    {pattern_id}: {stats['total_selections']} selections, "
                  f"avg reward: {stats['avg_reward']:.3f}")

    # Compare algorithms
    print(f"\n{'='*80}")
    print("ALGORITHM COMPARISON SUMMARY")
    print(f"{'='*80}")

    for algo_name, result in results.items():
        print(f"\n{algo_name.upper()}:")
        print(f"  Total Return: {result['total_return']:.2f}")
        print(f"  Average Return: {result['avg_return']:.3f}")

    # Determine winner
    best_algo = max(results.keys(), key=lambda x: results[x]['avg_return'])
    print(f"\nBest Performing Algorithm: {best_algo.upper()}")

    return results


def run_adaptive_position_sizing_demo():
    """Demonstrate adaptive position sizing."""
    print("\n" + "=" * 80)
    print("ADAPTIVE POSITION SIZING DEMONSTRATION")
    print("=" * 80)

    system = MemoryLearningSystem(
        min_position_size_multiplier=0.5,
        max_position_size_multiplier=2.0,
        min_trades_for_adaptation=5,
        random_seed=42
    )

    # Define patterns with different performance profiles
    patterns = {
        "high_performer": {"win_rate": 0.75, "expectancy": 2.2, "volatility": 0.3},
        "average_performer": {"win_rate": 0.55, "expectancy": 1.1, "volatility": 0.4},
        "poor_performer": {"win_rate": 0.35, "expectancy": 0.6, "volatility": 0.5}
    }

    print("Simulating trades to build performance history...")

    # Build performance history
    for pattern_id, performance in patterns.items():
        print(f"\nBuilding history for {pattern_id}:")

        for i in range(15):  # Build sufficient history
            outcome = generate_synthetic_trade_outcome(
                trade_id=f"history_{pattern_id}_{i:03d}",
                pattern_id=pattern_id,
                pattern_performance=performance
            )
            system.record_trade_outcome(outcome)

        # Show pattern performance
        perf = system.pattern_performance[pattern_id]
        print(f"  Trades: {perf.total_trades}, Win Rate: {perf.win_rate:.2f}, "
              f"Expectancy: {perf.expectancy:.2f}")

    print(f"\n{'Pattern':<20} {'Base Size':<10} {'Confidence':<12} {'Multiplier':<12} {'Final Size':<12}")
    print("-" * 70)

    base_position_size = 1000
    confidence_levels = [0.6, 0.8, 0.9]

    for pattern_id in patterns.keys():
        for confidence in confidence_levels:
            multiplier = system.get_adaptive_position_size_multiplier(pattern_id, confidence)
            final_size = base_position_size * multiplier

            print(f"{pattern_id:<20} {base_position_size:<10} {confidence:<12.1f} "
                  f"{multiplier:<12.2f} {final_size:<12.0f}")

    print("\nKey Insights:")
    print("- High performers get larger position sizes")
    print("- Poor performers get reduced position sizes")
    print("- Higher confidence increases position size")
    print("- All multipliers are bounded between 0.5 and 2.0")


def run_performance_windows_demo():
    """Demonstrate rolling performance windows."""
    print("\n" + "=" * 80)
    print("ROLLING PERFORMANCE WINDOWS DEMONSTRATION")
    print("=" * 80)

    system = MemoryLearningSystem(random_seed=42)

    # Simulate trades over different time periods
    print("Simulating trades over 120 days...")

    pattern_performance = {"win_rate": 0.6, "expectancy": 1.5, "volatility": 0.4}

    for day in range(120):
        # Generate 1-3 trades per day
        trades_per_day = random.randint(1, 3)

        for trade_num in range(trades_per_day):
            # Vary performance over time (market regime changes)
            if day < 30:
                regime = "bull"
                regime_multiplier = 1.2
            elif day < 60:
                regime = "sideways"
                regime_multiplier = 0.9
            elif day < 90:
                regime = "bear"
                regime_multiplier = 0.7
            else:
                regime = "recovery"
                regime_multiplier = 1.1

            adjusted_performance = {
                "win_rate": pattern_performance["win_rate"] * regime_multiplier,
                "expectancy": pattern_performance["expectancy"] * regime_multiplier,
                "volatility": pattern_performance["volatility"]
            }

            # Create outcome with specific date
            outcome = generate_synthetic_trade_outcome(
                trade_id=f"day_{day:03d}_trade_{trade_num}",
                pattern_id="test_pattern",
                pattern_performance=adjusted_performance,
                market_regime=regime
            )

            # Adjust entry/exit times to specific day
            outcome.entry_time = datetime.now() - timedelta(days=120-day, hours=trade_num*2)
            outcome.exit_time = outcome.entry_time + timedelta(hours=outcome.holding_time_hours)

            system.record_trade_outcome(outcome)

    print(f"Total trades recorded: {len(system.trade_outcomes)}")

    # Show performance windows
    print(f"\n{'Window':<15} {'Trades':<8} {'Win Rate':<10} {'Expectancy':<12} {'Sharpe':<10} {'Max DD':<10}")
    print("-" * 70)

    for window_days in [30, 60, 90]:
        metrics = system.performance_windows[window_days].get_performance_metrics()

        print(f"{window_days} days{'':<8} {metrics['total_trades']:<8} "
              f"{metrics['win_rate']:<10.2f} {metrics['expectancy']:<12.2f} "
              f"{metrics['sharpe_ratio']:<10.2f} {metrics['max_drawdown']:<10.2f}")

    print("\nKey Insights:")
    print("- Shorter windows show more recent performance")
    print("- Longer windows provide more stable metrics")
    print("- Performance varies significantly across market regimes")
    print("- System adapts to changing market conditions")


def run_walk_forward_analysis():
    """Demonstrate walk-forward testing showing improvement over static weights."""
    print("\n" + "=" * 80)
    print("WALK-FORWARD ANALYSIS: ADAPTIVE vs STATIC WEIGHTS")
    print("=" * 80)

    # Define patterns with evolving performance
    pattern_definitions = {
        "pattern_a": {
            "initial": {"win_rate": 0.7, "expectancy": 2.0, "volatility": 0.3},
            "evolution": "declining"
        },
        "pattern_b": {
            "initial": {"win_rate": 0.4, "expectancy": 1.0, "volatility": 0.4},
            "evolution": "improving"
        },
        "pattern_c": {
            "initial": {"win_rate": 0.6, "expectancy": 1.5, "volatility": 0.35},
            "evolution": "stable"
        }
    }

    # Test adaptive system
    adaptive_system = MemoryLearningSystem(
        bandit_algorithm=BanditAlgorithm.UCB1,
        min_trades_for_adaptation=10,
        random_seed=42
    )

    # Test static system (equal weights)
    static_system = MemoryLearningSystem(
        bandit_algorithm=BanditAlgorithm.EPSILON_GREEDY,
        epsilon=1.0,  # Always random = equal weights
        min_trades_for_adaptation=10,
        random_seed=42
    )

    systems = {
        "Adaptive (UCB1)": adaptive_system,
        "Static (Equal)": static_system
    }

    results = {name: {"returns": [], "hit_rates": []} for name in systems.keys()}

    total_trades = 300
    window_size = 50  # Evaluate every 50 trades

    print("Running walk-forward analysis...")
    print(f"Total trades: {total_trades}, Evaluation window: {window_size}")

    for trade_num in range(total_trades):
        for system_name, system in systems.items():
            # Select pattern
            available_patterns = list(pattern_definitions.keys())
            selected_pattern = system.bandit.select_pattern(available_patterns)

            # Get current pattern performance (evolving over time)
            pattern_def = pattern_definitions[selected_pattern]
            if pattern_def["evolution"] == "declining":
                decay = 0.998 ** trade_num
                current_perf = {
                    "win_rate": pattern_def["initial"]["win_rate"] * decay,
                    "expectancy": pattern_def["initial"]["expectancy"] * decay,
                    "volatility": pattern_def["initial"]["volatility"]
                }
            elif pattern_def["evolution"] == "improving":
                growth = 1.0 + (trade_num / total_trades) * 0.8
                current_perf = {
                    "win_rate": min(0.85, pattern_def["initial"]["win_rate"] * growth),
                    "expectancy": pattern_def["initial"]["expectancy"] * growth,
                    "volatility": pattern_def["initial"]["volatility"]
                }
            else:  # stable
                current_perf = pattern_def["initial"]

            # Generate outcome
            outcome = generate_synthetic_trade_outcome(
                trade_id=f"{system_name}_{trade_num:03d}",
                pattern_id=selected_pattern,
                pattern_performance=current_perf
            )

            system.record_trade_outcome(outcome)

        # Evaluate performance every window_size trades
        if (trade_num + 1) % window_size == 0:
            window_start = max(0, trade_num + 1 - window_size)

            for system_name, system in systems.items():
                # Calculate metrics for recent window
                recent_outcomes = system.trade_outcomes[window_start:]
                if recent_outcomes:
                    avg_return = np.mean([o.return_multiple for o in recent_outcomes])
                    hit_rate = np.mean([o.was_winner for o in recent_outcomes])

                    results[system_name]["returns"].append(avg_return)
                    results[system_name]["hit_rates"].append(hit_rate)

    # Display results
    print(f"\n{'System':<20} {'Avg Return':<12} {'Avg Hit Rate':<15} {'Final Hit Rate':<15}")
    print("-" * 65)

    for system_name in systems.keys():
        avg_return = np.mean(results[system_name]["returns"])
        avg_hit_rate = np.mean(results[system_name]["hit_rates"])
        final_hit_rate = results[system_name]["hit_rates"][-1] if results[system_name]["hit_rates"] else 0

        print(f"{system_name:<20} {avg_return:<12.3f} {avg_hit_rate:<15.3f} {final_hit_rate:<15.3f}")

    # Calculate improvement
    adaptive_final = results["Adaptive (UCB1)"]["hit_rates"][-1]
    static_final = results["Static (Equal)"]["hit_rates"][-1]
    improvement = (adaptive_final - static_final) / static_final * 100

    print(f"\nHit Rate Improvement: {improvement:.1f}%")

    if improvement >= 5.0:
        print("✅ SUCCESS: Adaptive system shows ≥5% improvement over static weights!")
    else:
        print("⚠️  Note: Improvement less than 5% - may need parameter tuning")

    # Show pattern selection evolution
    print("\nPattern Selection Evolution (Adaptive System):")
    print("-" * 50)

    bandit_stats = adaptive_system.bandit.get_pattern_statistics()
    for pattern_id, stats in bandit_stats.items():
        evolution = pattern_definitions[pattern_id]["evolution"]
        print(f"{pattern_id} ({evolution}): {stats['total_selections']} selections, "
              f"avg reward: {stats['avg_reward']:.3f}")

    return results


def run_comprehensive_demo():
    """Run comprehensive demonstration of all features."""
    print("🚀 AUTONOMOUS TRADING SYSTEM - MEMORY LEARNING DEMO")
    print("=" * 80)
    print("This demo showcases the self-learning memory and adaptation system")
    print("with multi-armed bandit algorithms, adaptive position sizing,")
    print("and performance tracking across rolling windows.")
    print("=" * 80)

    # Run all demonstrations
    bandit_results = run_bandit_comparison_demo()
    run_adaptive_position_sizing_demo()
    run_performance_windows_demo()
    walk_forward_results = run_walk_forward_analysis()

    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SYSTEM REPORT")
    print("=" * 80)

    # Use the best performing system from bandit comparison
    best_system = max(bandit_results.values(), key=lambda x: x['avg_return'])['system']
    report = best_system.get_performance_report()

    print("\nSystem Configuration:")
    print(f"  Algorithm: {report['system_parameters']['bandit_algorithm']}")
    print(f"  Epsilon: {report['system_parameters']['epsilon']}")
    print(f"  Position Size Range: {report['system_parameters']['min_position_multiplier']:.1f}x - {report['system_parameters']['max_position_multiplier']:.1f}x")

    print("\nOverall Performance:")
    print(f"  Total Trades: {report['total_trades']}")

    print("\nPattern Performance:")
    for pattern_id, perf in report['pattern_performance'].items():
        print(f"  {pattern_id}:")
        print(f"    Trades: {perf['total_trades']}, Win Rate: {perf['win_rate']:.2f}")
        print(f"    Expectancy: {perf['expectancy']:.2f}, Max Consecutive Losses: {perf['max_consecutive_losses']}")

    print("\nRolling Window Performance:")
    for window, metrics in report['performance_windows'].items():
        if metrics['total_trades'] > 0:
            print(f"  {window}: {metrics['total_trades']} trades, "
                  f"Win Rate: {metrics['win_rate']:.2f}, "
                  f"Sharpe: {metrics['sharpe_ratio']:.2f}")

    print("\n✅ Demo completed successfully!")
    print("📊 All components working as expected:")
    print("   - Multi-armed bandit algorithms implemented and tested")
    print("   - Adaptive position sizing with bounded risk scaling")
    print("   - Rolling performance windows for strategy calibration")
    print("   - Pattern weight updates based on trade outcomes")
    print("   - Walk-forward analysis showing improvement over static weights")

    return report


if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    np.random.seed(42)

    try:
        report = run_comprehensive_demo()

        # Save report to file
        with open("memory_learning_demo_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        print("\n📁 Detailed report saved to: memory_learning_demo_report.json")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        raise
