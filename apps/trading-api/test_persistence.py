#!/usr/bin/env python3
"""
Test script for the SQLAlchemy persistence layer.
Run this to verify the database setup and basic operations work.
"""

import asyncio
import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

from persistence_service import persistence_service


async def test_persistence_layer():
    """Test the persistence layer functionality."""
    print("Testing SQLAlchemy persistence layer...")

    try:
        # Initialize the persistence service
        await persistence_service.initialize()
        print("✓ Database initialized successfully")

        # Test creating a trade
        trade = await persistence_service.create_trade(
            symbol="BTCUSDT",
            side="LONG",
            entry_price=45000.0,
            quantity=0.1,
            confidence=0.85,
            pattern="breakout",
            strategy="momentum",
            timeframe="1h",
            entry_reason="Strong bullish breakout above resistance"
        )
        print(f"✓ Created trade: {trade.id}")

        # Test getting trades
        trades, total, has_next = await persistence_service.get_trades_paginated(page=1, page_size=10)
        print(f"✓ Retrieved {len(trades)} trades (total: {total})")

        # Test closing the trade
        closed_trade = await persistence_service.close_trade(
            trade_id=trade.id,
            exit_price=45500.0,
            exit_reason="Take profit hit",
            fees=2.5
        )
        if closed_trade:
            print(f"✓ Closed trade with P&L: ${closed_trade.pnl:.2f}")

        # Test performance metrics
        performance = await persistence_service.get_trading_performance()
        print(f"✓ Performance metrics - Total P&L: ${performance['total_pnl']:.2f}")

        # Test system metrics
        metrics = await persistence_service.record_system_metrics(
            cpu_usage=25.5,
            memory_usage=60.2,
            disk_usage=45.0,
            network_latency=50.0,
            error_rate=0.1
        )
        print(f"✓ Recorded system metrics at {metrics.timestamp}")

        # Test notifications
        notification = await persistence_service.create_notification(
            notification_type="info",
            title="Test Notification",
            message="This is a test notification from the persistence layer",
            source="test",
            category="system"
        )
        print(f"✓ Created notification: {notification.id}")

        # Test getting notifications
        notifications, total, has_next = await persistence_service.get_notifications_paginated(
            page=1, page_size=10
        )
        print(f"✓ Retrieved {len(notifications)} notifications")

        # Test marking notification as read
        success = await persistence_service.mark_notification_read(notification.id)
        if success:
            print("✓ Marked notification as read")

        # Test unread count
        unread_count = await persistence_service.get_unread_notification_count()
        print(f"✓ Unread notifications: {unread_count}")

        # Test system health
        health = await persistence_service.get_system_health_summary()
        print(f"✓ System health status: {health['status']}")

        print("\n🎉 All persistence layer tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        await persistence_service.close()
        print("✓ Database connection closed")

    return True


async def main():
    """Main test function."""
    print("SQLAlchemy Persistence Layer Test")
    print("=" * 40)

    success = await test_persistence_layer()

    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
