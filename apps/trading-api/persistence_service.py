"""
Persistence service layer that integrates SQLAlchemy with the trading API.
Provides high-level operations for data persistence and retrieval.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from database import (
    DatabaseManager,
    NotificationDataAccess,
    NotificationModel,
    SystemMetricModel,
    SystemMetricsDataAccess,
    TradeModel,
    TradingDataAccess,
)
from sqlalchemy import and_, select

logger = logging.getLogger(__name__)


class PersistenceService:
    """High-level persistence service for the trading API."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.trading_data = TradingDataAccess(self.db_manager)
        self.system_metrics_data = SystemMetricsDataAccess(self.db_manager)
        self.notification_data = NotificationDataAccess(self.db_manager)
        self._initialized = False

    async def initialize(self):
        """Initialize the persistence service."""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
            logger.info("Persistence service initialized successfully")

    async def close(self):
        """Close the persistence service."""
        if self._initialized:
            await self.db_manager.close()
            self._initialized = False
            logger.info("Persistence service closed")

    # Trading Operations
    async def create_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        confidence: float,
        pattern: Optional[str] = None,
        strategy: Optional[str] = None,
        timeframe: Optional[str] = None,
        entry_reason: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        **kwargs
    ) -> TradeModel:
        """Create a new trade record."""
        trade_data = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "confidence": confidence,
            "pattern": pattern,
            "strategy": strategy,
            "timeframe": timeframe,
            "entry_reason": entry_reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "status": "OPEN",
            "timestamp": datetime.now(UTC),
            **kwargs
        }

        trade = await self.trading_data.create_trade(trade_data)
        logger.info(f"Created new trade: {trade.id} - {symbol} {side} @ {entry_price}")
        return trade

    async def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: Optional[str] = None,
        fees: Optional[float] = None
    ) -> Optional[TradeModel]:
        """Close an existing trade."""
        # Calculate P&L and duration
        async with self.db_manager.get_session() as session:
            trade = await session.get(TradeModel, trade_id)
            if not trade or trade.status != "OPEN":
                return None

            # Calculate P&L based on side
            if trade.side == "LONG":
                pnl = (exit_price - trade.entry_price) * trade.quantity
            else:  # SHORT
                pnl = (trade.entry_price - exit_price) * trade.quantity

            # Subtract fees if provided
            if fees:
                pnl -= fees

            # Calculate duration
            duration = int((datetime.now(UTC) - trade.timestamp).total_seconds())

            update_data = {
                "exit_price": exit_price,
                "pnl": pnl,
                "status": "CLOSED",
                "exit_reason": exit_reason,
                "fees": fees or 0.0,
                "duration": duration
            }

            updated_trade = await self.trading_data.update_trade(trade_id, update_data)
            if updated_trade:
                logger.info(f"Closed trade: {trade_id} - P&L: {pnl:.2f}")
            return updated_trade

    async def get_trades_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        profit_loss_filter: Optional[str] = None,
        min_confidence: Optional[float] = None,
        search_text: Optional[str] = None
    ) -> tuple[list[TradeModel], int, bool]:
        """Get paginated trades with filtering."""
        offset = (page - 1) * page_size

        # Get trades with basic filters
        trades = await self.trading_data.get_trades(
            limit=page_size + 1,  # Get one extra to check if there are more
            offset=offset,
            symbol=symbol,
            status=status,
            date_from=date_from,
            date_to=date_to
        )

        # Apply additional filters in memory (could be optimized with database queries)
        filtered_trades = []
        for trade in trades:
            # Profit/loss filter
            if profit_loss_filter:
                if profit_loss_filter == "profit" and (not trade.pnl or trade.pnl <= 0):
                    continue
                elif profit_loss_filter == "loss" and (not trade.pnl or trade.pnl >= 0):
                    continue

            # Confidence filter
            if min_confidence and trade.confidence < min_confidence:
                continue

            # Search text filter
            if search_text:
                search_lower = search_text.lower()
                if (search_lower not in trade.symbol.lower() and
                    search_lower not in (trade.pattern or "").lower()):
                    continue

            filtered_trades.append(trade)

        # Check if there are more pages
        has_next = len(filtered_trades) > page_size
        if has_next:
            filtered_trades = filtered_trades[:-1]  # Remove the extra item

        # Get total count for this filter (simplified - could be optimized)
        total_count = len(filtered_trades) + offset
        if has_next:
            total_count += 1  # At least one more page

        return filtered_trades, total_count, has_next

    async def get_trading_performance(self) -> dict[str, Any]:
        """Get comprehensive trading performance metrics."""
        stats = await self.trading_data.get_trade_statistics()

        # Calculate additional metrics
        base_portfolio = 25000.0
        portfolio_value = base_portfolio + stats["total_pnl"]

        # Daily metrics
        today = datetime.now(UTC).date()
        daily_trades = await self.trading_data.get_trades(
            limit=1000,
            date_from=datetime.combine(today, datetime.min.time().replace(tzinfo=UTC))
        )

        daily_pnl = sum(trade.pnl or 0 for trade in daily_trades if trade.status == "CLOSED")
        daily_change_percent = (daily_pnl / base_portfolio * 100) if base_portfolio > 0 else 0

        # Drawdown calculation (simplified)
        peak_value = max(portfolio_value, base_portfolio)
        current_drawdown = ((peak_value - portfolio_value) / peak_value * 100) if peak_value > 0 else 0

        return {
            "total_pnl": stats["total_pnl"],
            "daily_pnl": daily_pnl,
            "win_rate": stats["win_rate"],
            "total_trades": stats["total_trades"],
            "active_positions": stats["active_positions"],
            "current_drawdown": current_drawdown,
            "max_drawdown": max(current_drawdown, 12.3),  # Should track historical max
            "portfolio_value": portfolio_value,
            "daily_change": daily_pnl,
            "daily_change_percent": daily_change_percent,
            "last_update": datetime.now(UTC)
        }

    # System Metrics Operations
    async def record_system_metrics(
        self,
        cpu_usage: float,
        memory_usage: float,
        disk_usage: float,
        network_latency: float,
        error_rate: float = 0.0,
        active_connections: int = 0,
        requests_per_minute: int = 0,
        **kwargs
    ) -> SystemMetricModel:
        """Record system performance metrics."""
        # Get current trading metrics
        stats = await self.trading_data.get_trade_statistics()
        performance = await self.get_trading_performance()

        metrics_data = {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "network_latency": network_latency,
            "error_rate": error_rate,
            "active_connections": active_connections,
            "requests_per_minute": requests_per_minute,
            "active_positions": stats["active_positions"],
            "daily_trades": len([t for t in await self.trading_data.get_trades(limit=1000)
                               if t.timestamp.date() == datetime.now(UTC).date()]),
            "daily_pnl": performance["daily_pnl"],
            "portfolio_value": performance["portfolio_value"],
            "database_healthy": True,  # Could add actual health checks
            "broker_healthy": True,
            "llm_healthy": True,
            **kwargs
        }

        metrics = await self.system_metrics_data.record_metrics(metrics_data)
        return metrics

    async def get_system_metrics_history(self, limit: int = 100) -> list[SystemMetricModel]:
        """Get recent system metrics history."""
        return await self.system_metrics_data.get_recent_metrics(limit)

    async def get_system_health_summary(self) -> dict[str, Any]:
        """Get current system health summary."""
        # Get latest metrics
        recent_metrics = await self.system_metrics_data.get_recent_metrics(1)
        if not recent_metrics:
            return {
                "status": "unknown",
                "cpu": 0,
                "memory": 0,
                "disk_usage": 0,
                "network_latency": 0,
                "error_rate": 0,
                "uptime": 0,
                "connections": {
                    "database": False,
                    "broker": False,
                    "llm": False
                },
                "last_update": datetime.now(UTC)
            }

        latest = recent_metrics[0]

        # Calculate uptime (simplified)
        uptime = int((datetime.now(UTC) - latest.timestamp).total_seconds())

        return {
            "status": "healthy" if latest.error_rate < 5 else "degraded",
            "cpu": latest.cpu_usage,
            "memory": latest.memory_usage,
            "disk_usage": latest.disk_usage,
            "network_latency": latest.network_latency,
            "error_rate": latest.error_rate,
            "uptime": uptime,
            "connections": {
                "database": latest.database_healthy,
                "broker": latest.broker_healthy,
                "llm": latest.llm_healthy
            },
            "last_update": latest.timestamp
        }

    # Notification Operations
    async def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        persistent: bool = False,
        source: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> NotificationModel:
        """Create a new notification."""
        notification_data = {
            "type": notification_type,
            "title": title,
            "message": message,
            "persistent": persistent,
            "source": source,
            "category": category,
            "severity": severity,
            "data": data,
            "user_id": user_id,
            "timestamp": datetime.now(UTC)
        }

        notification = await self.notification_data.create_notification(notification_data)
        logger.info(f"Created notification: {notification.id} - {title}")
        return notification

    async def get_notifications_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        notification_type: Optional[str] = None
    ) -> tuple[list[NotificationModel], int, bool]:
        """Get paginated notifications."""
        offset = (page - 1) * page_size

        notifications = await self.notification_data.get_notifications(
            limit=page_size + 1,
            offset=offset,
            unread_only=unread_only,
            notification_type=notification_type
        )

        has_next = len(notifications) > page_size
        if has_next:
            notifications = notifications[:-1]

        total_count = len(notifications) + offset
        if has_next:
            total_count += 1

        return notifications, total_count, has_next

    async def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        return await self.notification_data.mark_as_read(notification_id)

    async def get_unread_notification_count(self) -> int:
        """Get count of unread notifications."""
        return await self.notification_data.get_unread_count()

    # Data Migration and Seeding
    async def migrate_in_memory_data(self, trades_data: list[dict], metrics_data: list[dict], notifications_data: list[dict]):
        """Migrate existing in-memory data to the database."""
        logger.info("Starting data migration from in-memory storage to database...")

        # Migrate trades
        for trade_dict in trades_data:
            try:
                # Convert timestamp if it's a string
                if isinstance(trade_dict.get("timestamp"), str):
                    trade_dict["timestamp"] = datetime.fromisoformat(trade_dict["timestamp"].replace("Z", "+00:00"))

                # Map field names
                mapped_trade = {
                    "id": trade_dict.get("id"),
                    "timestamp": trade_dict.get("timestamp"),
                    "symbol": trade_dict.get("symbol"),
                    "side": trade_dict.get("side"),
                    "entry_price": trade_dict.get("entryPrice"),
                    "exit_price": trade_dict.get("exitPrice"),
                    "quantity": trade_dict.get("quantity"),
                    "pnl": trade_dict.get("pnl"),
                    "status": trade_dict.get("status"),
                    "pattern": trade_dict.get("pattern"),
                    "confidence": trade_dict.get("confidence", 0.0),
                    "fees": trade_dict.get("fees"),
                    "duration": trade_dict.get("duration")
                }

                await self.trading_data.create_trade(mapped_trade)
            except Exception as e:
                logger.error(f"Failed to migrate trade {trade_dict.get('id')}: {e}")

        # Migrate system metrics
        for metrics_dict in metrics_data:
            try:
                if isinstance(metrics_dict.get("timestamp"), str):
                    metrics_dict["timestamp"] = datetime.fromisoformat(metrics_dict["timestamp"].replace("Z", "+00:00"))

                mapped_metrics = {
                    "timestamp": metrics_dict.get("timestamp"),
                    "cpu_usage": metrics_dict.get("cpu", 0),
                    "memory_usage": metrics_dict.get("memory", 0),
                    "disk_usage": metrics_dict.get("diskUsage", 0),
                    "network_latency": metrics_dict.get("networkLatency", 0),
                    "error_rate": metrics_dict.get("errorRate", 0),
                    "active_connections": metrics_dict.get("activeConnections", 0),
                    "requests_per_minute": metrics_dict.get("requestsPerMinute", 0),
                    "active_positions": 0,
                    "daily_trades": 0,
                    "daily_pnl": 0.0,
                    "portfolio_value": 25000.0
                }

                await self.system_metrics_data.record_metrics(mapped_metrics)
            except Exception as e:
                logger.error(f"Failed to migrate system metrics: {e}")

        # Migrate notifications
        for notification_dict in notifications_data:
            try:
                if isinstance(notification_dict.get("timestamp"), str):
                    notification_dict["timestamp"] = datetime.fromisoformat(notification_dict["timestamp"].replace("Z", "+00:00"))

                mapped_notification = {
                    "id": notification_dict.get("id"),
                    "type": notification_dict.get("type"),
                    "title": notification_dict.get("title"),
                    "message": notification_dict.get("message"),
                    "timestamp": notification_dict.get("timestamp"),
                    "read": notification_dict.get("read", False),
                    "persistent": notification_dict.get("persistent", False),
                    "data": notification_dict.get("data")
                }

                await self.notification_data.create_notification(mapped_notification)
            except Exception as e:
                logger.error(f"Failed to migrate notification {notification_dict.get('id')}: {e}")

        logger.info("Data migration completed")

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to maintain database performance."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)

        async with self.db_manager.get_session() as session:
            # Clean up old system metrics (keep only recent data)
            old_metrics = await session.execute(
                select(SystemMetricModel).where(SystemMetricModel.timestamp < cutoff_date)
            )
            count = 0
            for metric in old_metrics.scalars():
                await session.delete(metric)
                count += 1

            logger.info(f"Cleaned up {count} old system metrics records")

            # Clean up old read notifications
            old_notifications = await session.execute(
                select(NotificationModel).where(
                    and_(
                        NotificationModel.timestamp < cutoff_date,
                        NotificationModel.read == True,
                        NotificationModel.persistent == False
                    )
                )
            )
            count = 0
            for notification in old_notifications.scalars():
                await session.delete(notification)
                count += 1

            logger.info(f"Cleaned up {count} old notification records")


# Global persistence service instance
persistence_service = PersistenceService()
