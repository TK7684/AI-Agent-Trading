"""
Trade Repository
Handles database operations for trade records, performance tracking, and historical data.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from apps.trading_api.database import TradeModel, get_async_session
except ImportError:
    # Fallback for standalone usage
    from sqlalchemy import (
        JSON,
        Boolean,
        Column,
        DateTime,
        Float,
        Integer,
        String,
        Text,
        and_,
        desc,
        func,
        select,
    )
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = "sqlite+aiosqlite:///./trading.db"

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_async_session():
        async with async_session() as session:
            yield session

    Base = declarative_base()

    class TradeModel(Base):
        __tablename__ = "trades"
        id = Column(String, primary_key=True)
        timestamp = Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
        )
        symbol = Column(String(20), nullable=False, index=True)
        side = Column(String(10), nullable=False)
        entry_price = Column(Float, nullable=False)
        exit_price = Column(Float, nullable=True)
        quantity = Column(Float, nullable=False)
        pnl = Column(Float, nullable=True)
        status = Column(String(20), nullable=False, default="OPEN", index=True)
        pattern = Column(String(50), nullable=True)
        confidence = Column(Float, nullable=False, default=0.0)
        fees = Column(Float, nullable=True, default=0.0)
        duration = Column(Integer, nullable=True)
        strategy = Column(String(50), nullable=True)
        timeframe = Column(String(10), nullable=True)
        entry_reason = Column(Text, nullable=True)
        exit_reason = Column(Text, nullable=True)
        risk_reward_ratio = Column(Float, nullable=True)
        stop_loss = Column(Float, nullable=True)
        take_profit = Column(Float, nullable=True)
        created_at = Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )
        updated_at = Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


# Initialize database tables synchronously on import
async def init_trade_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except:
        pass  # Database might already exist


def init_database():
    """Initialize database synchronously"""
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a task
            loop.create_task(init_trade_db())
        else:
            # If no loop running, run directly
            asyncio.run(init_trade_db())
    except:
        pass  # May not be in async context


# Initialize on import
init_database()


class TradeRepository:
    """Repository for managing trade records in the database"""

    def __init__(self):
        self._session_pool = None

    async def get_session(self) -> AsyncSession:
        """Get a database session from the pool"""
        if not self._session_pool:
            self._session_pool = get_async_session()
        async with self._session_pool() as session:
            yield session

    async def create_trade(
        self,
        position_id: str,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        pattern: str,
        strategy: str,
        timeframe: str,
        entry_reason: str,
        risk_reward_ratio: float,
    ) -> Optional[TradeModel]:
        """Create a new trade record"""
        try:
            async with get_async_session() as session:
                trade = TradeModel(
                    id=position_id,
                    symbol=symbol,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    pattern=pattern,
                    strategy=strategy,
                    timeframe=timeframe,
                    entry_reason=entry_reason,
                    risk_reward_ratio=risk_reward_ratio,
                    status="OPEN",
                )

                session.add(trade)
                await session.commit()
                await session.refresh(trade)

                return trade

        except Exception as e:
            print(f"Error creating trade: {e}")
            await session.rollback()
            return None

    async def close_trade(
        self,
        position_id: str,
        exit_price: float,
        final_pnl: float,
        exit_reason: str,
        duration: int,
    ) -> Optional[TradeModel]:
        """Close a trade record"""
        try:
            async with get_async_session() as session:
                # Get the trade
                stmt = select(TradeModel).where(TradeModel.id == position_id)
                result = await session.execute(stmt)
                trade = result.scalar_one_or_none()

                if not trade:
                    print(f"Trade not found: {position_id}")
                    return None

                # Update trade
                trade.exit_price = exit_price
                trade.pnl = final_pnl
                trade.exit_reason = exit_reason
                trade.duration = duration
                trade.status = "CLOSED"
                trade.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(trade)

                return trade

        except Exception as e:
            print(f"Error closing trade: {e}")
            await session.rollback()
            return None

    async def get_trade(self, position_id: str) -> Optional[TradeModel]:
        """Get a single trade by ID"""
        try:
            async with get_async_session() as session:
                stmt = select(TradeModel).where(TradeModel.id == position_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        except Exception as e:
            print(f"Error getting trade {position_id}: {e}")
            return None

    async def get_open_trades(self) -> List[TradeModel]:
        """Get all open trades"""
        try:
            async with get_async_session() as session:
                stmt = (
                    select(TradeModel)
                    .where(TradeModel.status == "OPEN")
                    .order_by(desc(TradeModel.created_at))
                )
                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting open trades: {e}")
            return []

    async def get_trades_by_symbol(
        self, symbol: str, limit: int = 100, status: Optional[str] = None
    ) -> List[TradeModel]:
        """Get trades for a specific symbol"""
        try:
            async with get_async_session() as session:
                stmt = select(TradeModel).where(TradeModel.symbol == symbol)

                if status:
                    stmt = stmt.where(TradeModel.status == status)

                stmt = stmt.order_by(desc(TradeModel.created_at)).limit(limit)

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting trades for {symbol}: {e}")
            return []

    async def get_trades_by_strategy(
        self, strategy: str, limit: int = 100
    ) -> List[TradeModel]:
        """Get trades for a specific strategy"""
        try:
            async with get_async_session() as session:
                stmt = (
                    select(TradeModel)
                    .where(TradeModel.strategy == strategy)
                    .order_by(desc(TradeModel.created_at))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting trades for strategy {strategy}: {e}")
            return []

    async def get_trades_by_pattern(
        self, pattern: str, limit: int = 100
    ) -> List[TradeModel]:
        """Get trades for a specific pattern"""
        try:
            async with get_async_session() as session:
                stmt = (
                    select(TradeModel)
                    .where(TradeModel.pattern == pattern)
                    .order_by(desc(TradeModel.created_at))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting trades for pattern {pattern}: {e}")
            return []

    async def get_trades_in_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[TradeModel]:
        """Get trades within a date range"""
        try:
            async with get_async_session() as session:
                stmt = (
                    select(TradeModel)
                    .where(
                        and_(
                            TradeModel.created_at >= start_date,
                            TradeModel.created_at <= end_date,
                        )
                    )
                    .order_by(desc(TradeModel.created_at))
                )

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting trades in date range: {e}")
            return []

    async def get_recent_performance(
        self, days: int = 30, strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get recent performance statistics"""
        try:
            async with get_async_session() as session:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Base query
                base_query = select(TradeModel).where(
                    and_(
                        TradeModel.status == "CLOSED",
                        TradeModel.created_at >= start_date,
                    )
                )

                if strategy:
                    base_query = base_query.where(TradeModel.strategy == strategy)

                # Get all trades
                stmt = base_query.order_by(desc(TradeModel.created_at))
                result = await session.execute(stmt)
                trades = result.scalars().all()

                if not trades:
                    return {
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "win_rate": 0.0,
                        "total_pnl": 0.0,
                        "average_win": 0.0,
                        "average_loss": 0.0,
                        "profit_factor": 0.0,
                        "max_drawdown": 0.0,
                        "sharpe_ratio": 0.0,
                    }

                # Calculate statistics
                total_trades = len(trades)
                winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
                losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

                total_pnl = sum(t.pnl or 0 for t in trades)
                win_rate = len(winning_trades) / total_trades

                average_win = (
                    sum(t.pnl for t in winning_trades) / len(winning_trades)
                    if winning_trades
                    else 0
                )
                average_loss = (
                    sum(t.pnl for t in losing_trades) / len(losing_trades)
                    if losing_trades
                    else 0
                )

                profit_factor = (
                    abs(
                        sum(t.pnl for t in winning_trades)
                        / sum(t.pnl for t in losing_trades)
                    )
                    if losing_trades
                    else float("inf")
                )

                # Calculate maximum drawdown
                cumulative_pnl = []
                running_total = 0
                for trade in sorted(trades, key=lambda x: x.created_at):
                    running_total += trade.pnl or 0
                    cumulative_pnl.append(running_total)

                max_drawdown = 0
                peak = cumulative_pnl[0] if cumulative_pnl else 0

                for pnl in cumulative_pnl:
                    if pnl > peak:
                        peak = pnl
                    drawdown = peak - pnl
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown

                # Calculate Sharpe ratio (simplified)
                returns = [t.pnl for t in trades if t.pnl]
                if returns:
                    avg_return = sum(returns) / len(returns)
                    variance = sum((r - avg_return) ** 2 for r in returns) / len(
                        returns
                    )
                    sharpe_ratio = avg_return / (variance**0.5) if variance > 0 else 0
                else:
                    sharpe_ratio = 0

                return {
                    "total_trades": total_trades,
                    "winning_trades": len(winning_trades),
                    "losing_trades": len(losing_trades),
                    "win_rate": win_rate,
                    "total_pnl": total_pnl,
                    "average_win": average_win,
                    "average_loss": average_loss,
                    "profit_factor": profit_factor,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                }

        except Exception as e:
            print(f"Error calculating recent performance: {e}")
            return {}

    async def get_strategy_performance(
        self, days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by strategy"""
        try:
            async with get_async_session() as session:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Get performance by strategy
                stmt = (
                    select(
                        TradeModel.strategy,
                        func.count(TradeModel.id).label("total_trades"),
                        func.sum(func.case([(TradeModel.pnl > 0, 1)], else_=0)).label(
                            "wins"
                        ),
                        func.sum(TradeModel.pnl).label("total_pnl"),
                        func.avg(
                            func.case(
                                [(TradeModel.pnl > 0, TradeModel.pnl)], else_=null()
                            )
                        ).label("avg_win"),
                        func.avg(
                            func.case(
                                [(TradeModel.pnl < 0, TradeModel.pnl)], else_=null()
                            )
                        ).label("avg_loss"),
                    )
                    .where(
                        and_(
                            TradeModel.status == "CLOSED",
                            TradeModel.created_at >= start_date,
                        )
                    )
                    .group_by(TradeModel.strategy)
                )

                result = await session.execute(stmt)
                rows = result.fetchall()

                strategy_performance = {}

                for row in rows:
                    if not row.strategy:
                        continue

                    win_rate = (
                        row.wins / row.total_trades if row.total_trades > 0 else 0
                    )
                    profit_factor = (
                        abs(row.avg_win / row.avg_loss)
                        if row.avg_loss and row.avg_loss != 0
                        else float("inf")
                    )

                    strategy_performance[row.strategy] = {
                        "total_trades": row.total_trades,
                        "wins": row.wins,
                        "win_rate": win_rate,
                        "total_pnl": row.total_pnl or 0,
                        "average_win": row.avg_win or 0,
                        "average_loss": row.avg_loss or 0,
                        "profit_factor": profit_factor,
                    }

                return strategy_performance

        except Exception as e:
            print(f"Error getting strategy performance: {e}")
            return {}

    async def get_pattern_performance(
        self, days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by pattern"""
        try:
            async with get_async_session() as session:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Get performance by pattern
                stmt = (
                    select(
                        TradeModel.pattern,
                        func.count(TradeModel.id).label("total_trades"),
                        func.sum(func.case([(TradeModel.pnl > 0, 1)], else_=0)).label(
                            "wins"
                        ),
                        func.sum(TradeModel.pnl).label("total_pnl"),
                        func.avg(
                            func.case(
                                [(TradeModel.pnl > 0, TradeModel.pnl)], else_=null()
                            )
                        ).label("avg_win"),
                        func.avg(
                            func.case(
                                [(TradeModel.pnl < 0, TradeModel.pnl)], else_=null()
                            )
                        ).label("avg_loss"),
                    )
                    .where(
                        and_(
                            TradeModel.status == "CLOSED",
                            TradeModel.created_at >= start_date,
                        )
                    )
                    .group_by(TradeModel.pattern)
                )

                result = await session.execute(stmt)
                rows = result.fetchall()

                pattern_performance = {}

                for row in rows:
                    if not row.pattern:
                        continue

                    win_rate = (
                        row.wins / row.total_trades if row.total_trades > 0 else 0
                    )
                    profit_factor = (
                        abs(row.avg_win / row.avg_loss)
                        if row.avg_loss and row.avg_loss != 0
                        else float("inf")
                    )

                    pattern_performance[row.pattern] = {
                        "total_trades": row.total_trades,
                        "wins": row.wins,
                        "win_rate": win_rate,
                        "total_pnl": row.total_pnl or 0,
                        "average_win": row.avg_win or 0,
                        "average_loss": row.avg_loss or 0,
                        "profit_factor": profit_factor,
                    }

                return pattern_performance

        except Exception as e:
            print(f"Error getting pattern performance: {e}")
            return {}

    async def update_trade_status(
        self, position_id: str, status: str
    ) -> Optional[TradeModel]:
        """Update trade status"""
        try:
            async with get_async_session() as session:
                stmt = select(TradeModel).where(TradeModel.id == position_id)
                result = await session.execute(stmt)
                trade = result.scalar_one_or_none()

                if not trade:
                    return None

                trade.status = status
                trade.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(trade)

                return trade

        except Exception as e:
            print(f"Error updating trade status: {e}")
            await session.rollback()
            return None

    async def delete_old_trades(self, days_to_keep: int = 90) -> int:
        """Delete old trade records to manage database size"""
        try:
            async with get_async_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

                stmt = select(TradeModel).where(TradeModel.created_at < cutoff_date)
                result = await session.execute(stmt)
                old_trades = result.scalars().all()

                count = len(old_trades)

                for trade in old_trades:
                    await session.delete(trade)

                await session.commit()

                return count

        except Exception as e:
            print(f"Error deleting old trades: {e}")
            await session.rollback()
            return 0

    async def get_daily_performance(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """Get daily performance breakdown"""
        try:
            async with get_async_session() as session:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)

                # Group trades by date
                stmt = (
                    select(
                        func.date(TradeModel.created_at).label("trade_date"),
                        func.count(TradeModel.id).label("total_trades"),
                        func.sum(func.case([(TradeModel.pnl > 0, 1)], else_=0)).label(
                            "wins"
                        ),
                        func.sum(TradeModel.pnl).label("total_pnl"),
                    )
                    .where(
                        and_(
                            TradeModel.status == "CLOSED",
                            TradeModel.created_at >= start_date,
                        )
                    )
                    .group_by(func.date(TradeModel.created_at))
                    .order_by(func.date(TradeModel.created_at))
                )

                result = await session.execute(stmt)
                rows = result.fetchall()

                daily_performance = {}

                for row in rows:
                    win_rate = (
                        row.wins / row.total_trades if row.total_trades > 0 else 0
                    )

                    daily_performance[str(row.trade_date)] = {
                        "total_trades": row.total_trades,
                        "wins": row.wins,
                        "win_rate": win_rate,
                        "total_pnl": row.total_pnl or 0,
                    }

                return daily_performance

        except Exception as e:
            print(f"Error getting daily performance: {e}")
            return {}
