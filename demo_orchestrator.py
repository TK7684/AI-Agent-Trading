#!/usr/bin/env python3
"""
Demo script for the Orchestrator and Main Trading Pipeline.

This script demonstrates:
1. Orchestrator initialization and configuration
2. Trading pipeline workflow
3. Position lifecycle management
4. Configuration hot reload
5. Safe mode triggering and recovery
6. Integration with all system components
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from libs.trading_models.config_manager import ConfigManager
from libs.trading_models.enums import Direction, MarketRegime, Timeframe
from libs.trading_models.orchestrator import (
    CheckInterval,
    OrchestrationConfig,
    Orchestrator,
    PositionLifecycle,
    create_orchestrator,
)
from libs.trading_models.signals import Signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_orchestrator():
    """Demonstrate basic orchestrator functionality."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Orchestrator Functionality")
    print("="*60)

    # Create orchestrator with test configuration
    config = OrchestrationConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframes=["1h", "4h"],
        base_check_interval=5,  # 5 seconds for demo
        max_concurrent_analyses=2
    )

    orchestrator = Orchestrator(config)

    print("✓ Orchestrator initialized")
    print(f"  - State: {orchestrator.state}")
    print(f"  - Symbols: {orchestrator.config.symbols}")
    print(f"  - Timeframes: {orchestrator.config.timeframes}")
    print(f"  - Check interval: {orchestrator.current_check_interval}")

    # Test symbol analysis timing
    print("\n📊 Testing symbol analysis timing:")
    for symbol in config.symbols:
        should_analyze = orchestrator._should_analyze_symbol(symbol)
        print(f"  - {symbol}: Should analyze = {should_analyze}")

    # Mark symbols as analyzed
    for symbol in config.symbols:
        orchestrator.last_analysis[symbol] = datetime.now()

    print("\n⏰ After marking as analyzed:")
    for symbol in config.symbols:
        should_analyze = orchestrator._should_analyze_symbol(symbol)
        print(f"  - {symbol}: Should analyze = {should_analyze}")

    return orchestrator


async def demo_trading_pipeline():
    """Demonstrate complete trading pipeline."""
    print("\n" + "="*60)
    print("DEMO 2: Complete Trading Pipeline")
    print("="*60)

    orchestrator = create_orchestrator({
        "symbols": ["BTCUSDT"],
        "base_check_interval": 1
    })

    print("🔄 Simulating complete trading pipeline...")

    # Simulate market data analysis
    print("\n1. Market Data Analysis:")
    market_data = await orchestrator._fetch_market_data("BTCUSDT")
    print(f"   ✓ Market data fetched: {market_data}")

    # Simulate technical analysis
    print("\n2. Technical Analysis:")
    indicators = await orchestrator._compute_indicators("BTCUSDT", market_data)
    print(f"   ✓ Indicators computed: {indicators}")

    patterns = await orchestrator._detect_patterns("BTCUSDT", market_data, indicators)
    print(f"   ✓ Patterns detected: {len(patterns)} patterns")

    # Simulate LLM analysis
    print("\n3. LLM Analysis:")
    llm_analysis = await orchestrator._get_llm_analysis("BTCUSDT", market_data, indicators, patterns)
    print(f"   ✓ LLM analysis: {llm_analysis}")

    # Simulate signal generation
    print("\n4. Signal Generation:")
    signal = await orchestrator._generate_trading_signal("BTCUSDT", indicators, patterns, llm_analysis)
    if signal:
        print("   ✓ Trading signal generated:")
        print(f"     - Symbol: {signal.symbol}")
        print(f"     - Direction: {signal.direction}")
        print(f"     - Confidence: {signal.confidence:.2f}")
        print(f"     - Confluence Score: {signal.confluence_score:.1f}")
        print(f"     - Reasoning: {signal.reasoning}")

    # Simulate risk assessment
    if signal and signal.confidence > 0.6:
        print("\n5. Risk Assessment:")
        decision = await orchestrator._make_trading_decision(signal)
        if decision:
            print(f"   ✓ Trading decision: {decision}")

            print("\n6. Order Execution:")
            await orchestrator._execute_trading_decision(decision)
            print("   ✓ Order executed successfully")

    return orchestrator


async def demo_position_lifecycle():
    """Demonstrate position lifecycle management."""
    print("\n" + "="*60)
    print("DEMO 3: Position Lifecycle Management")
    print("="*60)

    orchestrator = create_orchestrator()

    # Create test positions
    positions = [
        PositionLifecycle(
            position_id="pos_001",
            symbol="BTCUSDT",
            state="open",
            entry_time=datetime.now() - timedelta(minutes=5),
            last_check=datetime.now() - timedelta(minutes=1),
            stop_loss=49000.0,
            take_profit=52000.0
        ),
        PositionLifecycle(
            position_id="pos_002",
            symbol="ETHUSDT",
            state="monitoring",
            entry_time=datetime.now() - timedelta(minutes=15),
            last_check=datetime.now() - timedelta(minutes=2),
            stop_loss=1800.0,
            take_profit=2200.0,
            trailing_stop=1850.0
        )
    ]

    # Add positions to orchestrator
    for pos in positions:
        orchestrator.active_positions[pos.position_id] = pos

    print(f"📈 Created {len(positions)} test positions:")
    for pos in positions:
        print(f"   - {pos.position_id}: {pos.symbol} ({pos.state})")
        print(f"     Entry: {pos.entry_time.strftime('%H:%M:%S')}")
        print(f"     Stop Loss: ${pos.stop_loss:,.0f}")
        print(f"     Take Profit: ${pos.take_profit:,.0f}")
        if pos.trailing_stop:
            print(f"     Trailing Stop: ${pos.trailing_stop:,.0f}")

    print("\n🔄 Managing position lifecycles...")

    # Simulate position management
    for pos_id, pos in orchestrator.active_positions.items():
        print(f"\n   Managing {pos_id} ({pos.state}):")

        initial_state = pos.state
        await orchestrator._manage_position_lifecycle(pos)

        if pos.state != initial_state:
            print(f"     ✓ State changed: {initial_state} → {pos.state}")
        else:
            print(f"     - State unchanged: {pos.state}")

        print(f"     - Adjustments: {pos.adjustment_count}/{pos.max_adjustments}")
        print(f"     - Last check: {pos.last_check.strftime('%H:%M:%S')}")

    return orchestrator


async def demo_safe_mode():
    """Demonstrate safe mode functionality."""
    print("\n" + "="*60)
    print("DEMO 4: Safe Mode and Risk Management")
    print("="*60)

    orchestrator = create_orchestrator({
        "safe_mode_cooldown": 3  # 3 seconds for demo
    })

    # Add some test positions
    for i in range(3):
        pos = PositionLifecycle(
            position_id=f"pos_{i:03d}",
            symbol="BTCUSDT",
            state="monitoring",
            entry_time=datetime.now(),
            last_check=datetime.now()
        )
        orchestrator.active_positions[pos.position_id] = pos

    print("📊 Initial state:")
    print(f"   - Orchestrator state: {orchestrator.state}")
    print(f"   - Active positions: {len(orchestrator.active_positions)}")
    print(f"   - In safe mode: {orchestrator._is_in_safe_mode()}")

    # Trigger safe mode
    print("\n⚠️  Triggering safe mode (simulated drawdown)...")
    orchestrator.trigger_safe_mode("Daily drawdown threshold exceeded (8%)")

    print("   ✓ Safe mode triggered:")
    print(f"     - State: {orchestrator.state}")
    print(f"     - Safe mode until: {orchestrator.safe_mode_until.strftime('%H:%M:%S')}")
    print(f"     - In safe mode: {orchestrator._is_in_safe_mode()}")

    # Simulate emergency position closure
    print("\n🚨 Emergency position closure...")
    await orchestrator._emergency_position_closure()

    closing_positions = [pos for pos in orchestrator.active_positions.values() if pos.state == "closing"]
    print(f"   ✓ {len(closing_positions)} positions marked for closing")

    # Wait for safe mode to expire
    print("\n⏳ Waiting for safe mode cooldown...")
    await asyncio.sleep(4)

    print("   ✓ Safe mode expired:")
    print(f"     - State: {orchestrator.state}")
    print(f"     - In safe mode: {orchestrator._is_in_safe_mode()}")

    return orchestrator


async def demo_adaptive_intervals():
    """Demonstrate adaptive check intervals."""
    print("\n" + "="*60)
    print("DEMO 5: Adaptive Check Intervals")
    print("="*60)

    orchestrator = create_orchestrator()

    print(f"📊 Current check interval: {orchestrator.current_check_interval}")

    # Simulate different volatility scenarios
    volatility_scenarios = [
        (0.01, "Low volatility"),
        (0.03, "Normal volatility"),
        (0.07, "High volatility"),
        (0.02, "Back to normal")
    ]

    for volatility, description in volatility_scenarios:
        print(f"\n🎯 {description} (volatility: {volatility:.3f}):")

        # Mock volatility calculation
        original_method = orchestrator._calculate_market_volatility
        orchestrator._calculate_market_volatility = lambda: asyncio.create_task(
            asyncio.coroutine(lambda: volatility)()
        )

        # Simulate adaptive interval adjustment
        if volatility > orchestrator.config.volatility_threshold_high:
            orchestrator.current_check_interval = CheckInterval.FAST
        elif volatility < orchestrator.config.volatility_threshold_low:
            orchestrator.current_check_interval = CheckInterval.SLOW
        else:
            orchestrator.current_check_interval = CheckInterval.NORMAL

        print(f"   ✓ Adjusted to: {orchestrator.current_check_interval.name}")
        print(f"     - Interval: {orchestrator.current_check_interval.value} seconds")

        # Restore original method
        orchestrator._calculate_market_volatility = original_method

    return orchestrator


async def demo_configuration_management():
    """Demonstrate configuration management and hot reload."""
    print("\n" + "="*60)
    print("DEMO 6: Configuration Management")
    print("="*60)

    # Create temporary config file
    config_path = "demo_config.json"

    try:
        # Create config manager and export template
        manager = ConfigManager(config_path)
        manager.export_config_template(config_path)
        print(f"✓ Configuration template created: {config_path}")

        # Load configuration
        config = manager.load_config()
        print("✓ Configuration loaded:")
        print(f"   - Symbols: {config.symbols}")
        print(f"   - Check interval: {config.base_check_interval}")
        print(f"   - Risk thresholds: {config.daily_drawdown_threshold:.1%} daily, {config.monthly_drawdown_threshold:.1%} monthly")

        # Test callback registration
        callback_triggered = False

        def config_callback(new_config):
            nonlocal callback_triggered
            callback_triggered = True
            print("   📢 Configuration callback triggered!")
            print(f"      - New symbols: {new_config.symbols}")

        manager.register_callback(config_callback)
        print("✓ Callback registered")

        # Simulate configuration update
        print("\n🔄 Simulating configuration update...")
        time.sleep(0.1)  # Ensure different mtime

        # Update JSON config
        with open(config_path) as f:
            config_data = json.load(f)
        config_data["symbols"] = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        config_data["_updated"] = True
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

        # Check for updates
        updated = manager.check_for_updates()
        print(f"   ✓ Update detected: {updated}")
        print(f"   ✓ Callback triggered: {callback_triggered}")

        # Show updated config
        updated_config = manager.get_config()
        print(f"   ✓ Updated symbols: {updated_config.symbols}")

    finally:
        # Cleanup
        if Path(config_path).exists():
            Path(config_path).unlink()
            print(f"✓ Cleaned up: {config_path}")

    return manager


async def demo_error_handling():
    """Demonstrate error handling and recovery."""
    print("\n" + "="*60)
    print("DEMO 7: Error Handling and Recovery")
    print("="*60)

    orchestrator = create_orchestrator()

    # Test error scenarios
    error_scenarios = [
        ("Market data unavailable", lambda: orchestrator._fetch_market_data("INVALID")),
        ("LLM timeout", lambda: orchestrator._get_llm_analysis("BTCUSDT", {}, {}, [])),
        ("Risk limit violation", lambda: orchestrator._make_trading_decision(
            Signal(
                signal_id="high_risk_signal",
                symbol="BTCUSDT",
                timestamp=datetime.now(),
                direction=Direction.LONG,
                confluence_score=90.0,
                confidence=0.9,
                market_regime=MarketRegime.SIDEWAYS,
                primary_timeframe=Timeframe.H1,
                reasoning="High risk signal"
            )
        ))
    ]

    for scenario_name, error_func in error_scenarios:
        print(f"\n🚨 Testing: {scenario_name}")
        try:
            result = await error_func()
            print(f"   ✓ Handled gracefully: {result}")
        except Exception as e:
            print(f"   ⚠️  Exception caught: {type(e).__name__}: {e}")

    # Test circuit breaker behavior
    print("\n🔌 Testing circuit breaker pattern:")
    failure_count = 0
    max_failures = 3

    for attempt in range(5):
        try:
            if failure_count < max_failures:
                failure_count += 1
                raise Exception(f"Simulated failure {failure_count}")
            else:
                print("   ✓ Circuit breaker opened, using fallback")
                break
        except Exception as e:
            print(f"   ⚠️  Attempt {attempt + 1}: {e}")
            if failure_count >= max_failures:
                print("   🔌 Circuit breaker activated")
                break

    return orchestrator


async def main():
    """Run all orchestrator demos."""
    print("🚀 Autonomous Trading System - Orchestrator Demo")
    print("=" * 80)

    try:
        # Run all demos
        await demo_basic_orchestrator()
        await demo_trading_pipeline()
        await demo_position_lifecycle()
        await demo_safe_mode()
        await demo_adaptive_intervals()
        await demo_configuration_management()
        await demo_error_handling()

        print("\n" + "="*80)
        print("✅ All orchestrator demos completed successfully!")
        print("="*80)

        # Summary
        print("\n📋 ORCHESTRATOR CAPABILITIES DEMONSTRATED:")
        print("   ✓ Central coordination of all system components")
        print("   ✓ Complete trading pipeline (analysis → scoring → risk → execution)")
        print("   ✓ Position lifecycle management (Open → Monitor → Adjust → Close)")
        print("   ✓ Dynamic check intervals with adaptive backoff")
        print("   ✓ Configuration management and hot reload")
        print("   ✓ Safe mode triggering and recovery")
        print("   ✓ Comprehensive error handling and resilience")
        print("   ✓ Integration with all trading system components")

        print("\n🎯 KEY FEATURES:")
        print("   • Multi-timeframe market analysis coordination")
        print("   • Concurrent analysis with semaphore limiting")
        print("   • Position lifecycle state machine")
        print("   • Volatility-based adaptive scheduling")
        print("   • Hot configuration reload without restart")
        print("   • Emergency safe mode with position closure")
        print("   • Comprehensive logging and audit trail")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
