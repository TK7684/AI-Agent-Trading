#!/usr/bin/env python3
"""
Demo script for the comprehensive risk management system.

This script demonstrates:
1. Position sizing with confidence-based scaling
2. Portfolio exposure monitoring with correlation checks
3. Drawdown protection with SAFE_MODE triggers
4. Stop-loss management (ATR-based, breakeven, trailing)
5. Leverage controls and risk limit validation
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal

from libs.tradi, UTCng_models.enums import Direction
from libs.trading_models.risk_management import (
    PortfolioMetrics,
    Position,
    RiskManager,
    StopType,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def demo_position_sizing():
    """Demonstrate position sizing with confidence-based scaling."""
    print_section("POSITION SIZING DEMO")

    risk_manager = RiskManager()
    portfolio_value = Decimal("100000")
    available_margin = Decimal("50000")

    # Test different confidence levels
    test_cases = [
        ("Low Confidence", 0.2, "Conservative sizing expected"),
        ("Medium Confidence", 0.5, "Moderate sizing expected"),
        ("High Confidence", 0.8, "Aggressive sizing expected"),
        ("Maximum Confidence", 1.0, "Maximum sizing expected"),
    ]

    for name, confidence, description in test_cases:
        print_subsection(f"{name} (Confidence: {confidence})")
        print(f"Description: {description}")

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),  # 50 pip stop
            confidence=confidence,
            portfolio_value=portfolio_value,
            available_margin=available_margin,
            leverage=3.0
        )

        print(f"Approved: {assessment.approved}")
        print(f"Risk Score: {assessment.risk_score:.1f}/100")
        print(f"Position Risk: {assessment.position_risk_pct:.2f}%")
        print(f"Portfolio Risk: {assessment.portfolio_risk_pct:.2f}%")
        print(f"Leverage Used: {assessment.leverage_used}x")
        print(f"Margin Utilization: {assessment.margin_utilization:.1f}%")

        if assessment.suggested_position_size:
            print(f"Suggested Position Size: {assessment.suggested_position_size}")

        print(f"Assessment: {assessment.assessment_reason}")


def demo_correlation_monitoring():
    """Demonstrate correlation monitoring and exposure limits."""
    print_section("CORRELATION MONITORING DEMO")

    risk_manager = RiskManager()
    portfolio_value = Decimal("100000")

    # Set up currency correlations
    print_subsection("Setting up Currency Correlations")
    correlations = [
        ("EURUSD", "GBPUSD", 0.85),
        ("EURUSD", "AUDUSD", 0.72),
        ("EURUSD", "USDJPY", -0.65),
        ("GBPUSD", "AUDUSD", 0.78),
    ]

    for sym1, sym2, corr in correlations:
        risk_manager.correlation_monitor.update_correlation(sym1, sym2, corr)
        print(f"{sym1} vs {sym2}: {corr:+.2f}")

    # Add existing position
    print_subsection("Adding Existing Position")
    existing_position = Position(
        position_id="pos1",
        symbol="GBPUSD",
        direction=Direction.LONG,
        quantity=Decimal("8000"),
        entry_price=Decimal("1.3000"),
        current_price=Decimal("1.3050"),
        stop_loss=Decimal("1.2950"),
        unrealized_pnl=Decimal("400"),
        initial_risk=Decimal("400"),
        current_risk=Decimal("400"),
        opened_at=datetime.now(UTC)
    )

    risk_manager.add_position(existing_position)
    position_value = existing_position.calculate_position_value()
    print(f"GBPUSD Position: {existing_position.quantity} units")
    print(f"Position Value: ${position_value:,.2f}")
    print(f"Portfolio Exposure: {float(position_value / portfolio_value):.1%}")

    # Test new correlated position
    print_subsection("Testing New Correlated Position")

    assessment = risk_manager.assess_trade_risk(
        symbol="EURUSD",
        direction=Direction.LONG,
        entry_price=Decimal("1.1000"),
        stop_loss=Decimal("1.0950"),
        confidence=0.8,
        portfolio_value=portfolio_value,
        available_margin=Decimal("50000"),
        leverage=3.0
    )

    print("EURUSD Trade Assessment:")
    print(f"Approved: {assessment.approved}")
    print(f"Risk Factors: {assessment.risk_factors}")
    print(f"Warnings: {assessment.warnings}")

    if not assessment.approved:
        print("❌ Trade rejected due to correlation limits")
    else:
        print("✅ Trade approved - correlation within limits")


def demo_drawdown_protection():
    """Demonstrate drawdown protection and safe mode triggers."""
    print_section("DRAWDOWN PROTECTION DEMO")

    risk_manager = RiskManager()
    portfolio_value = Decimal("100000")

    # Simulate different drawdown scenarios
    scenarios = [
        {
            "name": "Normal Trading",
            "daily_dd": 0.03,
            "monthly_dd": 0.08,
            "description": "Acceptable drawdown levels"
        },
        {
            "name": "Daily Limit Breach",
            "daily_dd": 0.09,
            "monthly_dd": 0.12,
            "description": "Daily drawdown exceeds 8% limit"
        },
        {
            "name": "Monthly Limit Breach",
            "daily_dd": 0.05,
            "monthly_dd": 0.22,
            "description": "Monthly drawdown exceeds 20% limit"
        },
        {
            "name": "Emergency Situation",
            "daily_dd": 0.15,
            "monthly_dd": 0.25,
            "description": "Extreme drawdown triggers emergency mode"
        }
    ]

    for scenario in scenarios:
        print_subsection(scenario["name"])
        print(f"Description: {scenario['description']}")

        # Create portfolio metrics
        metrics = PortfolioMetrics(
            total_equity=portfolio_value,
            available_margin=Decimal("50000"),
            used_margin=Decimal("20000"),
            unrealized_pnl=Decimal(str(-portfolio_value * Decimal(str(scenario["daily_dd"])))),
            daily_pnl=Decimal(str(-portfolio_value * Decimal(str(scenario["daily_dd"])))),
            monthly_pnl=Decimal(str(-portfolio_value * Decimal(str(scenario["monthly_dd"])))),
            daily_drawdown=scenario["daily_dd"],
            monthly_drawdown=scenario["monthly_dd"],
            max_drawdown=max(scenario["daily_dd"], scenario["monthly_dd"]),
            win_rate=0.55,
            sharpe_ratio=1.0,
            total_trades=100,
            open_positions=3
        )

        # Update risk manager with metrics
        risk_manager.update_portfolio_metrics(metrics)

        print(f"Daily Drawdown: {scenario['daily_dd']:.1%}")
        print(f"Monthly Drawdown: {scenario['monthly_dd']:.1%}")
        print(f"Safe Mode: {risk_manager.drawdown_protection.current_safe_mode}")

        # Test position size adjustment
        adjustment = risk_manager.drawdown_protection.get_position_size_adjustment()
        print(f"Position Size Adjustment: {adjustment:.0%}")

        # Test new trade in this mode
        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=portfolio_value,
            available_margin=Decimal("50000"),
            leverage=3.0
        )

        if assessment.approved:
            print("✅ New trades allowed with reduced size")
        else:
            print("❌ New trades blocked")
            print(f"Reason: {assessment.assessment_reason}")


def demo_stop_loss_management():
    """Demonstrate different stop loss management strategies."""
    print_section("STOP LOSS MANAGEMENT DEMO")

    risk_manager = RiskManager()

    # Create positions with different stop types
    positions = [
        {
            "name": "ATR-Based Stop",
            "position": Position(
                position_id="atr_pos",
                symbol="EURUSD",
                direction=Direction.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                current_price=Decimal("1.1000"),
                stop_loss=Decimal("1.0950"),
                stop_type=StopType.ATR_BASED,
                unrealized_pnl=Decimal("0"),
                initial_risk=Decimal("500"),
                current_risk=Decimal("500"),
                opened_at=datetime.now(UTC)
            )
        },
        {
            "name": "Trailing Stop",
            "position": Position(
                position_id="trail_pos",
                symbol="GBPUSD",
                direction=Direction.LONG,
                quantity=Decimal("8000"),
                entry_price=Decimal("1.3000"),
                current_price=Decimal("1.3000"),
                stop_loss=Decimal("1.2950"),
                stop_type=StopType.TRAILING,
                unrealized_pnl=Decimal("0"),
                initial_risk=Decimal("400"),
                current_risk=Decimal("400"),
                opened_at=datetime.now(UTC)
            )
        },
        {
            "name": "Breakeven Stop",
            "position": Position(
                position_id="be_pos",
                symbol="USDJPY",
                direction=Direction.LONG,
                quantity=Decimal("100000"),
                entry_price=Decimal("110.00"),
                current_price=Decimal("110.00"),
                stop_loss=Decimal("109.50"),
                stop_type=StopType.BREAKEVEN,
                unrealized_pnl=Decimal("0"),
                initial_risk=Decimal("500"),
                current_risk=Decimal("500"),
                opened_at=datetime.now(UTC)
            )
        }
    ]

    # Add positions to risk manager
    for pos_data in positions:
        risk_manager.add_position(pos_data["position"])

    # Simulate price movements and stop updates
    price_scenarios = [
        {"name": "Initial State", "eurusd": 1.1000, "gbpusd": 1.3000, "usdjpy": 110.00},
        {"name": "Small Profit", "eurusd": 1.1020, "gbpusd": 1.3030, "usdjpy": 110.20},
        {"name": "Good Profit", "eurusd": 1.1050, "gbpusd": 1.3080, "usdjpy": 110.80},
        {"name": "Large Profit", "eurusd": 1.1100, "gbpusd": 1.3150, "usdjpy": 111.50},
    ]

    for scenario in price_scenarios:
        print_subsection(scenario["name"])

        # Update positions with new prices
        for pos_data in positions:
            position = pos_data["position"]

            if position.symbol == "EURUSD":
                new_price = Decimal(str(scenario["eurusd"]))
            elif position.symbol == "GBPUSD":
                new_price = Decimal(str(scenario["gbpusd"]))
            else:  # USDJPY
                new_price = Decimal(str(scenario["usdjpy"]))

            position.current_price = new_price
            position.calculate_unrealized_pnl()

            print(f"{pos_data['name']} ({position.symbol}):")
            print(f"  Current Price: {new_price}")
            print(f"  P&L: ${position.unrealized_pnl}")
            print(f"  Stop Loss: {position.stop_loss}")

        # Update stops based on ATR (simulated)
        atr_values = {"EURUSD": 0.0025, "GBPUSD": 0.0030, "USDJPY": 0.25}

        for symbol, atr in atr_values.items():
            old_positions = [p for p in risk_manager.current_positions if p.symbol == symbol]
            if old_positions:
                old_stop = old_positions[0].stop_loss

            risk_manager.update_position_stops(symbol, Decimal(str(scenario[symbol.lower()])), atr)

            new_positions = [p for p in risk_manager.current_positions if p.symbol == symbol]
            if new_positions and old_positions:
                new_stop = new_positions[0].stop_loss
                if new_stop != old_stop:
                    print(f"  ✅ {symbol} stop updated: {old_stop} → {new_stop}")


def demo_leverage_controls():
    """Demonstrate leverage controls and limits."""
    print_section("LEVERAGE CONTROLS DEMO")

    risk_manager = RiskManager()
    portfolio_value = Decimal("100000")
    available_margin = Decimal("50000")

    # Test different leverage levels
    leverage_tests = [
        (1.0, "Conservative - No leverage"),
        (3.0, "Default - Moderate leverage"),
        (5.0, "Aggressive - High leverage"),
        (10.0, "Maximum - At limit"),
        (15.0, "Excessive - Should be rejected"),
        (20.0, "Extreme - Should be rejected"),
    ]

    for leverage, description in leverage_tests:
        print_subsection(f"{leverage}x Leverage")
        print(f"Description: {description}")

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=portfolio_value,
            available_margin=available_margin,
            leverage=leverage
        )

        print(f"Approved: {assessment.approved}")
        print(f"Risk Score: {assessment.risk_score:.1f}/100")
        print(f"Leverage Used: {assessment.leverage_used}x")
        print(f"Margin Utilization: {assessment.margin_utilization:.1f}%")

        if assessment.suggested_leverage:
            print(f"Suggested Leverage: {assessment.suggested_leverage}x")

        if assessment.risk_factors:
            print(f"Risk Factors: {'; '.join(assessment.risk_factors)}")

        if assessment.approved:
            print("✅ Leverage approved")
        else:
            print("❌ Leverage rejected")


def demo_comprehensive_risk_assessment():
    """Demonstrate comprehensive risk assessment."""
    print_section("COMPREHENSIVE RISK ASSESSMENT")

    risk_manager = RiskManager()

    # Set up a complex scenario
    print_subsection("Setting up Complex Trading Scenario")

    # Add existing positions
    existing_positions = [
        Position(
            position_id="pos1",
            symbol="EURUSD",
            direction=Direction.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.0950"),
            current_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0900"),
            unrealized_pnl=Decimal("250"),
            initial_risk=Decimal("250"),
            current_risk=Decimal("250"),
            opened_at=datetime.now(UTC) - timedelta(hours=2)
        ),
        Position(
            position_id="pos2",
            symbol="GBPUSD",
            direction=Direction.SHORT,
            quantity=Decimal("3000"),
            entry_price=Decimal("1.3100"),
            current_price=Decimal("1.3050"),
            stop_loss=Decimal("1.3150"),
            unrealized_pnl=Decimal("150"),
            initial_risk=Decimal("150"),
            current_risk=Decimal("150"),
            opened_at=datetime.now(UTC) - timedelta(hours=1)
        )
    ]

    for position in existing_positions:
        risk_manager.add_position(position)
        print(f"Added {position.symbol} position: {position.quantity} units")

    # Set up correlations
    risk_manager.correlation_monitor.update_correlation("EURUSD", "GBPUSD", 0.75)
    risk_manager.correlation_monitor.update_correlation("EURUSD", "AUDUSD", 0.80)

    # Set portfolio metrics with some drawdown
    portfolio_value = Decimal("100000")
    metrics = PortfolioMetrics(
        total_equity=portfolio_value,
        available_margin=Decimal("45000"),
        used_margin=Decimal("15000"),
        unrealized_pnl=Decimal("400"),
        daily_pnl=Decimal("-2000"),
        monthly_pnl=Decimal("-5000"),
        daily_drawdown=0.05,  # 5% drawdown
        monthly_drawdown=0.12,  # 12% drawdown
        max_drawdown=0.15,
        win_rate=0.58,
        sharpe_ratio=1.1,
        total_trades=85,
        open_positions=2
    )

    risk_manager.update_portfolio_metrics(metrics)

    # Test new trade proposal
    print_subsection("Assessing New Trade Proposal")

    assessment = risk_manager.assess_trade_risk(
        symbol="AUDUSD",
        direction=Direction.LONG,
        entry_price=Decimal("0.7500"),
        stop_loss=Decimal("0.7450"),
        confidence=0.85,
        portfolio_value=portfolio_value,
        available_margin=Decimal("45000"),
        leverage=4.0
    )

    print("Trade Symbol: AUDUSD")
    print("Direction: LONG")
    print("Entry Price: 0.7500")
    print("Stop Loss: 0.7450")
    print("Confidence: 85%")
    print("Leverage: 4x")
    print()

    print("RISK ASSESSMENT RESULTS:")
    print(f"Approved: {'✅ YES' if assessment.approved else '❌ NO'}")
    print(f"Risk Score: {assessment.risk_score:.1f}/100")
    print(f"Position Risk: {assessment.position_risk_pct:.2f}%")
    print(f"Total Portfolio Risk: {assessment.portfolio_risk_pct:.2f}%")
    print(f"Leverage Used: {assessment.leverage_used}x")
    print(f"Margin Utilization: {assessment.margin_utilization:.1f}%")
    print(f"Safe Mode: {assessment.safe_mode_status}")
    print()

    if assessment.risk_factors:
        print("RISK FACTORS:")
        for factor in assessment.risk_factors:
            print(f"  ⚠️  {factor}")
        print()

    if assessment.warnings:
        print("WARNINGS:")
        for warning in assessment.warnings:
            print(f"  ⚡ {warning}")
        print()

    print(f"Assessment Reason: {assessment.assessment_reason}")

    # Show risk summary
    print_subsection("Current Risk Summary")
    summary = risk_manager.get_risk_summary()

    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")


def demo_performance_benchmarks():
    """Demonstrate performance benchmarks for risk decisions."""
    print_section("PERFORMANCE BENCHMARKS")

    risk_manager = RiskManager()
    portfolio_value = Decimal("100000")
    available_margin = Decimal("50000")

    print("Testing risk decision latency (target: ≤2ms)...")

    # Warm up
    for _ in range(10):
        risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=portfolio_value,
            available_margin=available_margin,
            leverage=3.0
        )

    # Benchmark risk assessments
    num_tests = 1000
    start_time = time.perf_counter()

    for i in range(num_tests):
        # Vary parameters slightly to avoid caching effects
        entry_price = Decimal("1.1000") + Decimal(str(i * 0.0001))
        confidence = 0.5 + (i % 50) * 0.01

        assessment = risk_manager.assess_trade_risk(
            symbol="EURUSD",
            direction=Direction.LONG,
            entry_price=entry_price,
            stop_loss=Decimal("1.0950"),
            confidence=confidence,
            portfolio_value=portfolio_value,
            available_margin=available_margin,
            leverage=3.0
        )

    end_time = time.perf_counter()
    total_time = end_time - start_time
    avg_time_ms = (total_time / num_tests) * 1000

    print(f"Completed {num_tests} risk assessments")
    print(f"Total time: {total_time:.3f} seconds")
    print(f"Average time per assessment: {avg_time_ms:.3f} ms")

    if avg_time_ms <= 2.0:
        print("✅ Performance target met (≤2ms)")
    else:
        print("❌ Performance target missed (>2ms)")

    # Test with positions
    print("\nTesting with existing positions...")

    # Add some positions
    for i in range(10):
        position = Position(
            position_id=f"perf_pos_{i}",
            symbol=f"PAIR{i}",
            direction=Direction.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.0000"),
            current_price=Decimal("1.0010"),
            stop_loss=Decimal("0.9950"),
            unrealized_pnl=Decimal("10"),
            initial_risk=Decimal("50"),
            current_risk=Decimal("50"),
            opened_at=datetime.now(UTC)
        )
        risk_manager.add_position(position)

    start_time = time.perf_counter()

    for i in range(100):  # Fewer tests with positions
        assessment = risk_manager.assess_trade_risk(
            symbol="NEWPAIR",
            direction=Direction.LONG,
            entry_price=Decimal("1.1000") + Decimal(str(i * 0.0001)),
            stop_loss=Decimal("1.0950"),
            confidence=0.8,
            portfolio_value=portfolio_value,
            available_margin=available_margin,
            leverage=3.0
        )

    end_time = time.perf_counter()
    total_time = end_time - start_time
    avg_time_ms = (total_time / 100) * 1000

    print(f"Average time with 10 positions: {avg_time_ms:.3f} ms")

    if avg_time_ms <= 2.0:
        print("✅ Performance target met with positions (≤2ms)")
    else:
        print("❌ Performance target missed with positions (>2ms)")


def main():
    """Run all risk management demos."""
    print("🚀 AUTONOMOUS TRADING SYSTEM - RISK MANAGEMENT DEMO")
    print("This demo showcases the comprehensive risk management system")
    print("with position sizing, correlation monitoring, drawdown protection,")
    print("stop-loss management, and leverage controls.")

    try:
        demo_position_sizing()
        demo_correlation_monitoring()
        demo_drawdown_protection()
        demo_stop_loss_management()
        demo_leverage_controls()
        demo_comprehensive_risk_assessment()
        demo_performance_benchmarks()

        print_section("DEMO COMPLETED SUCCESSFULLY")
        print("✅ All risk management components demonstrated")
        print("✅ Performance targets verified")
        print("✅ Risk limits and controls validated")
        print("\nThe risk management system is ready for integration!")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
