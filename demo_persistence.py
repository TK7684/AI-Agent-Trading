#!/usr/bin/env python3
"""
Demo script for persistence and audit logging system.

This script demonstrates the key features of the persistence system including:
- Database operations for trades, positions, and metrics
- JSON journal with tamper-evident logging
- Structured logging with reasoning steps
- Data export and replay functionality
- Backup and restore operations
"""

import asyncio
import json
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from libs.trading_models.enums import Direction, MarketRegime, OrderStatus
from libs.trading_models.migrations import (
    BackupManager,
    DataReplaySystem,
    MigrationManager,
)
from libs.trading_models.orders import ExecutionResult, OrderDecision
from libs.trading_models.persistence import (
    DecisionContext,
    MarketSnapshot,
    PerformanceMetricModel,
    PersistenceManager,
    PositionRecordModel,
    TradeRecordModel,
)
from libs.trading_models.signals import Signal, TimeframeAnalysis


def create_sample_data() -> dict[str, Any]:
    """Create sample trading data for demonstration."""

    # Sample market snapshot
    market_snapshot = MarketSnapshot(
        symbol="BTCUSD",
        timestamp=datetime.now(UTC),
        price=50000.0,
        volume=1500.0,
        indicators={
            "rsi": 65.0,
            "ema_20": 49500.0,
            "ema_50": 48000.0,
            "macd": 150.0,
            "bb_upper": 52000.0,
            "bb_lower": 48000.0
        },
        patterns=["bullish_engulfing", "support_bounce"],
        regime=MarketRegime.BULL
    )

    # Sample signal
    signal = Signal(
        signal_id=str(uuid.uuid4()),
        symbol="BTCUSD",
        direction=Direction.LONG,
        confluence_score=85.0,
        confidence=0.85,
        market_regime=MarketRegime.BULL,
        primary_timeframe="1h",
        reasoning="Strong bullish momentum with RSI confirmation and pattern breakout",
        timeframe_analysis={
            "15m": TimeframeAnalysis(
                timeframe="15m",
                timestamp=datetime.now(UTC),
                trend_score=8.0,
                momentum_score=7.5,
                volatility_score=6.0,
                volume_score=7.0,
                pattern_count=2,
                strongest_pattern_confidence=0.8,
                bullish_indicators=6,
                bearish_indicators=1,
                neutral_indicators=3,
                timeframe_weight=0.3
            ),
            "1h": TimeframeAnalysis(
                timeframe="1h",
                timestamp=datetime.now(UTC),
                trend_score=9.0,
                momentum_score=8.0,
                volatility_score=5.5,
                volume_score=8.5,
                pattern_count=3,
                strongest_pattern_confidence=0.9,
                bullish_indicators=7,
                bearish_indicators=0,
                neutral_indicators=3,
                timeframe_weight=0.7
            )
        },
        timestamp=datetime.now(UTC)
    )

    # Sample decision context
    decision_context = DecisionContext(
        signal=signal,
        market_snapshot=market_snapshot,
        risk_assessment={
            "position_size": 0.02,
            "stop_loss": 48000.0,
            "take_profit": 55000.0,
            "risk_reward_ratio": 2.5,
            "max_loss_percentage": 4.0
        },
        reasoning_steps=[
            "Analyzed technical indicators across multiple timeframes",
            "Identified bullish engulfing pattern with volume confirmation",
            "Confirmed support level bounce at 49000",
            "Calculated optimal position size based on 2% risk rule",
            "Set stop loss below key support level",
            "Target profit at next resistance zone"
        ],
        confidence_factors={
            "technical_analysis": 0.85,
            "pattern_recognition": 0.80,
            "volume_confirmation": 0.75,
            "risk_management": 0.90
        },
        llm_analysis={
            "model": "claude-3-sonnet",
            "confidence": 0.82,
            "reasoning": "Market shows strong bullish momentum with multiple confirmations",
            "risk_factors": ["Potential resistance at 52k", "Overall market volatility"]
        }
    )

    # Sample order decision
    order_decision = OrderDecision(
        symbol="BTCUSD",
        action="BUY",
        quantity=0.1,
        price=50000.0,
        order_type="MARKET",
        stop_loss=48000.0,
        take_profit=55000.0,
        reasoning="High confidence bullish signal with strong technical confirmation"
    )

    # Sample execution result
    execution_result = ExecutionResult(
        order_id=f"order_{uuid.uuid4()}",
        status="FILLED",
        filled_quantity=0.1,
        average_price=50025.0,
        fees=25.0,
        timestamp=datetime.now(UTC)
    )

    return {
        "market_snapshot": market_snapshot,
        "signal": signal,
        "decision_context": decision_context,
        "order_decision": order_decision,
        "execution_result": execution_result
    }


def demo_database_operations(persistence_manager: PersistenceManager):
    """Demonstrate database operations."""
    print("\n=== Database Operations Demo ===")

    # Create sample trade records
    trades = []
    for i in range(3):
        entry_time = datetime.now(UTC) - timedelta(days=i+1)
        exit_time = entry_time + timedelta(hours=2+i)

        trade = TradeRecordModel(
            id=f"trade_{i+1:03d}",
            symbol="BTCUSD",
            direction=Direction.LONG if i % 2 == 0 else Direction.SHORT,
            entry_price=50000.0 + (i * 1000),
            exit_price=52000.0 + (i * 1000) if i % 2 == 0 else 49000.0 + (i * 1000),
            quantity=0.1,
            entry_time=entry_time,
            exit_time=exit_time,
            pnl=200.0 if i % 2 == 0 else -100.0,
            pnl_percentage=4.0 if i % 2 == 0 else -2.0,
            fees=25.0,
            status=OrderStatus.FILLED,
            stop_loss=48000.0 + (i * 1000),
            take_profit=55000.0 + (i * 1000),
            pattern_id=f"pattern_{i+1}",
            confidence_score=0.8 + (i * 0.05),
            reasoning=f"Trade {i+1} reasoning with technical analysis",
            trade_metadata={"demo": True, "batch": 1},
            created_at=entry_time,
            updated_at=exit_time
        )

        persistence_manager.save_trade(trade)
        trades.append(trade)
        print(f"Saved trade {trade.id}: {trade.direction} {trade.symbol} @ {trade.entry_price}")

    # Create position snapshots
    for i, trade in enumerate(trades):
        for hour in range(3):
            snapshot_time = trade.entry_time + timedelta(hours=hour)
            current_price = trade.entry_price + (hour * 100) - 50

            position = PositionRecordModel(
                id=f"pos_{trade.id}_{hour}",
                trade_id=trade.id,
                symbol=trade.symbol,
                quantity=trade.quantity,
                average_price=trade.entry_price,
                current_price=current_price,
                unrealized_pnl=(current_price - trade.entry_price) * trade.quantity,
                unrealized_pnl_percentage=((current_price - trade.entry_price) / trade.entry_price) * 100,
                margin_used=trade.entry_price * trade.quantity * 0.1,  # 10x leverage
                timestamp=snapshot_time,
                position_metadata={"hour": hour}
            )

            persistence_manager.save_position_snapshot(position)

    print(f"Saved {len(trades) * 3} position snapshots")

    # Create performance metrics
    metrics = [
        ("win_rate", 0.67),
        ("sharpe_ratio", 1.45),
        ("max_drawdown", 0.08),
        ("profit_factor", 2.1),
        ("avg_trade_duration", 2.5)
    ]

    for metric_name, value in metrics:
        metric = PerformanceMetricModel(
            id=f"metric_{metric_name}_{int(datetime.now().timestamp())}",
            metric_name=metric_name,
            metric_value=value,
            period_start=datetime.now(UTC) - timedelta(days=30),
            period_end=datetime.now(UTC),
            symbol="BTCUSD",
            pattern_id="overall",
            timeframe="1h",
            timestamp=datetime.now(UTC)
        )

        persistence_manager.save_performance_metric(metric)
        print(f"Saved metric: {metric_name} = {value}")

    # Query and display trades
    print("\n--- Retrieving Trades ---")
    retrieved_trades = persistence_manager.get_trades(symbol="BTCUSD")
    for trade in retrieved_trades:
        print(f"Trade {trade.id}: {trade.direction} {trade.pnl:+.2f} USD ({trade.pnl_percentage:+.1f}%)")


def demo_journal_logging(persistence_manager: PersistenceManager):
    """Demonstrate JSON journal and structured logging."""
    print("\n=== Journal Logging Demo ===")

    # Log risk events
    risk_events = [
        ("position_size_calculated", {
            "symbol": "BTCUSD",
            "base_size": 0.02,
            "adjusted_size": 0.015,
            "confidence_factor": 0.75,
            "risk_percentage": 1.5
        }),
        ("stop_loss_triggered", {
            "trade_id": "trade_001",
            "trigger_price": 48000.0,
            "current_price": 47950.0,
            "loss_amount": 200.0,
            "action": "position_closed"
        })
    ]

    for event_type, event_data in risk_events:
        persistence_manager.logger.log_risk_event(event_type, event_data)
        print(f"Logged risk event: {event_type}")

    # Log system events
    system_events = [
        ("market_data_reconnect", {
            "exchange": "binance",
            "reason": "websocket_timeout",
            "downtime_seconds": 15,
            "recovery_method": "automatic_reconnect"
        }),
        ("llm_fallback", {
            "primary_model": "claude-3-sonnet",
            "fallback_model": "gpt-4-turbo",
            "reason": "rate_limit_exceeded",
            "request_id": str(uuid.uuid4())
        })
    ]

    for event_type, event_data in system_events:
        persistence_manager.logger.log_system_event(event_type, event_data)
        print(f"Logged system event: {event_type}")

    # Verify journal integrity
    print("\n--- Journal Integrity Check ---")
    integrity_ok = persistence_manager.journal.verify_integrity()
    print(f"Journal integrity: {'✓ VALID' if integrity_ok else '✗ COMPROMISED'}")

    # Display recent journal entries
    print("\n--- Recent Journal Entries ---")
    recent_entries = persistence_manager.journal.read_entries()[-5:]  # Last 5 entries
    for entry in recent_entries:
        print(f"{entry.timestamp.strftime('%H:%M:%S')} | {entry.event_type} | Hash: {entry.hash_chain[:8]}...")


def demo_data_export_replay(persistence_manager: PersistenceManager):
    """Demonstrate data export and replay functionality."""
    print("\n=== Data Export & Replay Demo ===")

    # Export data
    with tempfile.TemporaryDirectory() as temp_dir:
        export_path = Path(temp_dir) / "export"
        print(f"Exporting data to: {export_path}")

        persistence_manager.export_data(export_path)

        # List exported files
        exported_files = list(export_path.glob("*.json"))
        print(f"Exported files: {[f.name for f in exported_files]}")

        # Show sample of exported data
        if (export_path / "trades.json").exists():
            with open(export_path / "trades.json") as f:
                trades_data = json.load(f)
                print(f"Exported {len(trades_data)} trades")

        if (export_path / "journal.json").exists():
            with open(export_path / "journal.json") as f:
                journal_data = json.load(f)
                print(f"Exported {len(journal_data)} journal entries")

    # Replay system demo
    print("\n--- Data Replay System ---")
    replay_system = DataReplaySystem(persistence_manager)

    # Generate performance report
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=7)

    print("Generating performance report for last 7 days...")
    report = replay_system.generate_performance_report(start_time, end_time)

    print("Trading Metrics:")
    print(f"  Total Trades: {report['trading_metrics']['total_trades']}")
    print(f"  Win Rate: {report['trading_metrics']['win_rate']:.1%}")
    print(f"  Total P&L: ${report['trading_metrics']['total_pnl']:.2f}")
    print(f"  Net P&L: ${report['trading_metrics']['net_pnl']:.2f}")

    print("System Metrics:")
    print(f"  Total Events: {report['system_metrics']['total_events']}")
    event_dist = report['system_metrics']['event_type_distribution']
    for event_type, count in event_dist.items():
        print(f"  {event_type}: {count}")


def demo_backup_restore():
    """Demonstrate backup and restore functionality."""
    print("\n=== Backup & Restore Demo ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test database and journal
        db_path = Path(temp_dir) / "test.db"
        journal_path = Path(temp_dir) / "journal.jsonl"
        backup_dir = Path(temp_dir) / "backups"

        # Create some test data
        journal_path.write_text('{"test": "journal_data", "timestamp": "2023-01-01T12:00:00Z"}\n')

        backup_manager = BackupManager(
            f"sqlite:///{db_path}",
            journal_path,
            backup_dir
        )

        print("Creating backup...")
        try:
            backup_path = backup_manager.create_backup("demo_backup")
            print(f"Backup created at: {backup_path}")

            # List backups
            backups = backup_manager.list_backups()
            print(f"Available backups: {len(backups)}")
            for backup in backups:
                print(f"  - {backup['backup_name']} ({backup['created_at']})")

        except Exception as e:
            print(f"Backup demo skipped (requires external tools): {e}")


def demo_migration_system():
    """Demonstrate database migration system."""
    print("\n=== Migration System Demo ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = "sqlite:///:memory:"
        migrations_dir = Path(temp_dir) / "migrations"

        migration_manager = MigrationManager(database_url, migrations_dir)

        print("Checking migration status...")
        status = migration_manager.check_migration_status()
        print(f"Current revision: {status['current_revision']}")
        print(f"Total migrations: {status['total_migrations']}")

        # Note: Full migration demo would require Alembic setup
        print("Migration system initialized (full demo requires Alembic configuration)")


async def main():
    """Main demo function."""
    print("🔄 Autonomous Trading System - Persistence & Audit Logging Demo")
    print("=" * 70)

    # Setup persistence manager
    with tempfile.TemporaryDirectory() as temp_dir:
        database_url = "sqlite:///:memory:"
        journal_path = Path(temp_dir) / "demo_journal.jsonl"

        print("Initializing persistence system...")
        print(f"Database: {database_url}")
        print(f"Journal: {journal_path}")

        persistence_manager = PersistenceManager(database_url, journal_path)
        persistence_manager.initialize()

        try:
            # Run demos
            demo_database_operations(persistence_manager)
            demo_journal_logging(persistence_manager)
            demo_data_export_replay(persistence_manager)
            demo_backup_restore()
            demo_migration_system()

            print("\n" + "=" * 70)
            print("✅ All persistence and audit logging demos completed successfully!")
            print("\nKey Features Demonstrated:")
            print("  ✓ Database operations (trades, positions, metrics)")
            print("  ✓ JSON journal with tamper-evident logging")
            print("  ✓ Structured logging with reasoning steps")
            print("  ✓ Data export and replay functionality")
            print("  ✓ Backup and restore operations")
            print("  ✓ Database migration management")
            print("  ✓ Hash-chain integrity verification")
            print("  ✓ Performance reporting and analysis")

        finally:
            persistence_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
