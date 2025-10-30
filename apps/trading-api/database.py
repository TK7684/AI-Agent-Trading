"""
Database models and persistence layer for the trading API.
Provides SQLAlchemy models and database operations for trading history and system metrics.
"""

import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    and_,
    desc,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://trading_user:trading_pass@localhost:5432/trading_db"
)

# For development, fall back to SQLite
if "postgresql" not in DATABASE_URL.lower():
    DATABASE_URL = "sqlite+aiosqlite:///./trading.db"

Base = declarative_base()

# Database Models
class TradeModel(Base):
    """SQLAlchemy model for trading records."""
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # OPEN, CLOSED, CANCELLED
    pattern = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    fees = Column(Float, nullable=True, default=0.0)
    duration = Column(Integer, nullable=True)  # Duration in seconds

    # Additional trading metadata
    strategy = Column(String(50), nullable=True)
    timeframe = Column(String(10), nullable=True)
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Indexes for performance
    __table_args__ = (
        Index('idx_trades_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_trades_status_timestamp', 'status', 'timestamp'),
        Index('idx_trades_pnl', 'pnl'),
    )


class SystemMetricModel(Base):
    """SQLAlchemy model for system performance metrics."""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    # System performance metrics
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    network_latency = Column(Float, nullable=False)
    error_rate = Column(Float, nullable=False, default=0.0)
    active_connections = Column(Integer, nullable=False, default=0)
    requests_per_minute = Column(Integer, nullable=False, default=0)

    # Trading system specific metrics
    active_positions = Column(Integer, nullable=False, default=0)
    daily_trades = Column(Integer, nullable=False, default=0)
    daily_pnl = Column(Float, nullable=False, default=0.0)
    portfolio_value = Column(Float, nullable=False, default=0.0)

    # Service health indicators
    database_healthy = Column(Boolean, nullable=False, default=True)
    broker_healthy = Column(Boolean, nullable=False, default=True)
    llm_healthy = Column(Boolean, nullable=False, default=True)

    # Additional metadata
    metric_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_system_metrics_timestamp', 'timestamp'),
    )


class NotificationModel(Base):
    """SQLAlchemy model for system notifications and alerts."""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(20), nullable=False, index=True)  # info, warning, error, success
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)
    read = Column(Boolean, nullable=False, default=False, index=True)
    persistent = Column(Boolean, nullable=False, default=False)

    # Notification source and context
    source = Column(String(50), nullable=True)  # system, trading, user
    category = Column(String(50), nullable=True)  # alert, trade, system, error
    severity = Column(String(20), nullable=True)  # low, medium, high, critical

    # Additional data as JSON
    data = Column(JSON, nullable=True)

    # User association (for future multi-user support)
    user_id = Column(String, nullable=True, index=True)

    __table_args__ = (
        Index('idx_notifications_type_timestamp', 'type', 'timestamp'),
        Index('idx_notifications_read_timestamp', 'read', 'timestamp'),
    )


class TradingSessionModel(Base):
    """SQLAlchemy model for trading sessions and agent activity."""
    __tablename__ = "trading_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    start_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, STOPPED, PAUSED, ERROR

    # Session configuration
    symbols = Column(JSON, nullable=True)  # List of trading symbols
    timeframes = Column(JSON, nullable=True)  # List of timeframes
    strategy_config = Column(JSON, nullable=True)  # Strategy parameters
    risk_config = Column(JSON, nullable=True)  # Risk management settings

    # Session statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    total_pnl = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)

    # Agent version and metadata
    agent_version = Column(String(20), nullable=True)
    metric_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_trading_sessions_start_time', 'start_time'),
        Index('idx_trading_sessions_status', 'status'),
    )


class PerformanceSnapshotModel(Base):
    """SQLAlchemy model for periodic performance snapshots."""
    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    # Portfolio metrics
    total_pnl = Column(Float, nullable=False, default=0.0)
    daily_pnl = Column(Float, nullable=False, default=0.0)
    portfolio_value = Column(Float, nullable=False, default=0.0)
    daily_change_percent = Column(Float, nullable=False, default=0.0)

    # Trading statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)

    # Risk metrics
    current_drawdown = Column(Float, nullable=False, default=0.0)
    max_drawdown = Column(Float, nullable=False, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)

    # Position information
    active_positions = Column(Integer, nullable=False, default=0)
    total_exposure = Column(Float, nullable=False, default=0.0)

    # Session reference
    session_id = Column(String, ForeignKey('trading_sessions.id'), nullable=True)

    __table_args__ = (
        Index('idx_performance_snapshots_timestamp', 'timestamp'),
    )


# Database Engine and Session Management
class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None

    async def initialize(self):
        """Initialize the database engine and create tables."""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Data Access Layer
class TradingDataAccess:
    """Data access layer for trading operations."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def create_trade(self, trade_data: dict[str, Any]) -> TradeModel:
        """Create a new trade record."""
        async with self.db_manager.get_session() as session:
            trade = TradeModel(**trade_data)
            session.add(trade)
            await session.flush()
            await session.refresh(trade)
            return trade

    async def update_trade(self, trade_id: str, update_data: dict[str, Any]) -> Optional[TradeModel]:
        """Update an existing trade record."""
        async with self.db_manager.get_session() as session:
            trade = await session.get(TradeModel, trade_id)
            if trade:
                for key, value in update_data.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                trade.updated_at = datetime.now(UTC)
                await session.flush()
                await session.refresh(trade)
            return trade

    async def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> list[TradeModel]:
        """Get trades with filtering and pagination."""
        async with self.db_manager.get_session() as session:
            query = select(TradeModel)

            if symbol:
                query = query.filter(TradeModel.symbol == symbol)
            if status:
                query = query.filter(TradeModel.status == status)
            if date_from:
                query = query.filter(TradeModel.timestamp >= date_from)
            if date_to:
                query = query.filter(TradeModel.timestamp <= date_to)

            query = query.order_by(desc(TradeModel.timestamp))
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_trade_statistics(self) -> dict[str, Any]:
        """Get comprehensive trading statistics."""
        async with self.db_manager.get_session() as session:
            # Total trades
            total_trades_result = await session.execute(
                select(func.count(TradeModel.id))
            )
            total_trades = total_trades_result.scalar() or 0

            # Total P&L
            total_pnl_result = await session.execute(
                select(func.sum(TradeModel.pnl)).where(TradeModel.status == "CLOSED")
            )
            total_pnl = total_pnl_result.scalar() or 0.0

            # Win rate
            winning_trades_result = await session.execute(
                select(func.count(TradeModel.id)).where(
                    and_(TradeModel.status == "CLOSED", TradeModel.pnl > 0)
                )
            )
            winning_trades = winning_trades_result.scalar() or 0

            closed_trades_result = await session.execute(
                select(func.count(TradeModel.id)).where(TradeModel.status == "CLOSED")
            )
            closed_trades = closed_trades_result.scalar() or 0

            win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0

            # Active positions
            active_positions_result = await session.execute(
                select(func.count(TradeModel.id)).where(TradeModel.status == "OPEN")
            )
            active_positions = active_positions_result.scalar() or 0

            return {
                "total_trades": total_trades,
                "closed_trades": closed_trades,
                "active_positions": active_positions,
                "total_pnl": total_pnl,
                "winning_trades": winning_trades,
                "win_rate": win_rate
            }


class SystemMetricsDataAccess:
    """Data access layer for system metrics."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def record_metrics(self, metrics_data: dict[str, Any]) -> SystemMetricModel:
        """Record system metrics."""
        async with self.db_manager.get_session() as session:
            metrics = SystemMetricModel(**metrics_data)
            session.add(metrics)
            await session.flush()
            await session.refresh(metrics)
            return metrics

    async def get_recent_metrics(self, limit: int = 100) -> list[SystemMetricModel]:
        """Get recent system metrics."""
        async with self.db_manager.get_session() as session:
            query = select(SystemMetricModel).order_by(desc(SystemMetricModel.timestamp)).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_metrics_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get system metrics summary for the specified time period."""
        async with self.db_manager.get_session() as session:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

            # Average metrics
            avg_metrics_result = await session.execute(
                select(
                    func.avg(SystemMetricModel.cpu_usage).label('avg_cpu'),
                    func.avg(SystemMetricModel.memory_usage).label('avg_memory'),
                    func.avg(SystemMetricModel.disk_usage).label('avg_disk'),
                    func.avg(SystemMetricModel.network_latency).label('avg_latency'),
                    func.avg(SystemMetricModel.error_rate).label('avg_error_rate'),
                ).where(SystemMetricModel.timestamp >= cutoff_time)
            )

            avg_metrics = avg_metrics_result.first()

            return {
                "avg_cpu": avg_metrics.avg_cpu or 0,
                "avg_memory": avg_metrics.avg_memory or 0,
                "avg_disk": avg_metrics.avg_disk or 0,
                "avg_latency": avg_metrics.avg_latency or 0,
                "avg_error_rate": avg_metrics.avg_error_rate or 0,
                "period_hours": hours
            }


class NotificationDataAccess:
    """Data access layer for notifications."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def create_notification(self, notification_data: dict[str, Any]) -> NotificationModel:
        """Create a new notification."""
        async with self.db_manager.get_session() as session:
            notification = NotificationModel(**notification_data)
            session.add(notification)
            await session.flush()
            await session.refresh(notification)
            return notification

    async def get_notifications(
        self,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: Optional[str] = None
    ) -> list[NotificationModel]:
        """Get notifications with filtering and pagination."""
        async with self.db_manager.get_session() as session:
            query = select(NotificationModel)

            if unread_only:
                query = query.filter(NotificationModel.read == False)
            if notification_type:
                query = query.filter(NotificationModel.type == notification_type)

            query = query.order_by(desc(NotificationModel.timestamp))
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()

    async def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        async with self.db_manager.get_session() as session:
            notification = await session.get(NotificationModel, notification_id)
            if notification:
                notification.read = True
                return True
            return False

    async def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(func.count(NotificationModel.id)).where(NotificationModel.read == False)
            )
            return result.scalar() or 0


# Global database manager instance
db_manager = DatabaseManager()
trading_data = TradingDataAccess(db_manager)
system_metrics_data = SystemMetricsDataAccess(db_manager)
notification_data = NotificationDataAccess(db_manager)
