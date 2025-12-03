"""
Performance Repository
Handles database operations for performance metrics, learning results, and system analytics.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from apps.trading_api.database import get_async_session
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

    class PerformanceMetricModel(Base):
        """SQLAlchemy model for performance metrics"""

        __tablename__ = "performance_metrics"

        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            index=True,
        )

        # Trading performance metrics
        daily_pnl = Column(Float, nullable=False, default=0.0)
        total_trades = Column(Integer, nullable=False, default=0)
        winning_trades = Column(Integer, nullable=False, default=0)
        losing_trades = Column(Integer, nullable=False, default=0)
        win_rate = Column(Float, nullable=False, default=0.0)
        active_positions = Column(Integer, nullable=False, default=0)

        # Risk metrics
        max_drawdown = Column(Float, nullable=False, default=0.0)
        sharpe_ratio = Column(Float, nullable=False, default=0.0)
        sortino_ratio = Column(Float, nullable=False, default=0.0)
        calmar_ratio = Column(Float, nullable=False, default=0.0)

        # System metrics
        cpu_usage = Column(Float, nullable=True)
        memory_usage = Column(Float, nullable=True)
        disk_usage = Column(Float, nullable=True)
        network_latency = Column(Float, nullable=True)
        error_rate = Column(Float, nullable=False, default=0.0)
        active_connections = Column(Integer, nullable=False, default=0)
        requests_per_minute = Column(Integer, nullable=False, default=0)

        # Strategy performance breakdown
        strategy_performance = Column(JSON, nullable=True)
        pattern_performance = Column(JSON, nullable=True)

        created_at = Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )

    class LearningResultModel(Base):
        """SQLAlchemy model for learning results"""

        __tablename__ = "learning_results"

        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            index=True,
        )

        # Learning cycle information
        cycle_type = Column(
            String(50), nullable=False
        )  # 'CALIBRATION', 'OPTIMIZATION', 'ADAPTATION'
        trade_count = Column(Integer, nullable=False, default=0)
        learning_duration = Column(Float, nullable=True)  # Duration in seconds

        # Calibration results
        calibration_results = Column(JSON, nullable=True)
        performance_report = Column(JSON, nullable=True)

        # Strategy updates
        strategy_updates = Column(JSON, nullable=True)
        parameter_adjustments = Column(JSON, nullable=True)

        # Performance impact
        performance_impact = Column(JSON, nullable=True)
        accuracy_improvement = Column(Float, nullable=True)
        profit_improvement = Column(Float, nullable=True)

        # Learning metrics
        convergence_score = Column(Float, nullable=True)
        confidence_level = Column(Float, nullable=True)
        sample_size = Column(Integer, nullable=True)

        created_at = Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )

    class SystemHealthModel(Base):
        """SQLAlchemy model for system health monitoring"""

        __tablename__ = "system_health"

        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            index=True,
        )

        # System status
        status = Column(
            String(20), nullable=False, default="HEALTHY"
        )  # HEALTHY, WARNING, CRITICAL, OFFLINE
        uptime = Column(Float, nullable=False, default=0.0)  # Uptime in seconds

        # Component status
        trading_engine_status = Column(String(20), nullable=False, default="RUNNING")
        database_status = Column(String(20), nullable=False, default="CONNECTED")
        llm_service_status = Column(String(20), nullable=False, default="AVAILABLE")
        market_data_status = Column(String(20), nullable=False, default="STREAMING")

        # Resource utilization
        cpu_usage = Column(Float, nullable=False, default=0.0)
        memory_usage = Column(Float, nullable=False, default=0.0)
        disk_usage = Column(Float, nullable=False, default=0.0)
        network_io = Column(Float, nullable=False, default=0.0)

        # Error tracking
        error_count = Column(Integer, nullable=False, default=0)
        warning_count = Column(Integer, nullable=False, default=0)
        last_error = Column(Text, nullable=True)
        last_error_time = Column(DateTime(timezone=True), nullable=True)

        # Performance indicators
        response_time = Column(Float, nullable=True)
        throughput = Column(Float, nullable=True)
        queue_size = Column(Integer, nullable=False, default=0)

        created_at = Column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )


from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    and_,
    desc,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


class PerformanceRepository:
    """Repository for managing performance metrics and learning results"""

    def __init__(self):
        self._models_initialized = False

    async def _initialize_models(self):
        """Initialize database models if not already done"""
        if not self._models_initialized:
            async with get_async_session() as session:
                # Create tables if they don't exist
                async with session.begin():
                    await session.run_sync(Base.metadata.create_all)
            self._models_initialized = True

    async def save_performance_metrics(
        self, metrics: Dict[str, Any]
    ) -> Optional[PerformanceMetricModel]:
        """Save performance metrics to database"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                performance_metric = PerformanceMetricModel(
                    daily_pnl=metrics.get("daily_pnl", 0.0),
                    total_trades=metrics.get("total_trades", 0),
                    winning_trades=metrics.get("winning_trades", 0),
                    losing_trades=metrics.get("losing_trades", 0),
                    win_rate=metrics.get("win_rate", 0.0),
                    active_positions=metrics.get("active_positions", 0),
                    max_drawdown=metrics.get("max_drawdown", 0.0),
                    sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
                    sortino_ratio=metrics.get("sortino_ratio", 0.0),
                    calmar_ratio=metrics.get("calmar_ratio", 0.0),
                    cpu_usage=metrics.get("cpu_usage"),
                    memory_usage=metrics.get("memory_usage"),
                    disk_usage=metrics.get("disk_usage"),
                    network_latency=metrics.get("network_latency"),
                    error_rate=metrics.get("error_rate", 0.0),
                    active_connections=metrics.get("active_connections", 0),
                    requests_per_minute=metrics.get("requests_per_minute", 0),
                    strategy_performance=metrics.get("strategy_performance"),
                    pattern_performance=metrics.get("pattern_performance"),
                    timestamp=metrics.get("timestamp", datetime.now(timezone.utc)),
                )

                session.add(performance_metric)
                await session.commit()
                await session.refresh(performance_metric)

                return performance_metric

        except Exception as e:
            print(f"Error saving performance metrics: {e}")
            await session.rollback()
            return None

    async def save_learning_results(
        self,
        calibration_results: Optional[Dict[str, Any]] = None,
        performance_report: Optional[Dict[str, Any]] = None,
        cycle_type: str = "CALIBRATION",
        trade_count: int = 0,
        learning_duration: Optional[float] = None,
        strategy_updates: Optional[Dict[str, Any]] = None,
        parameter_adjustments: Optional[Dict[str, Any]] = None,
        performance_impact: Optional[Dict[str, Any]] = None,
        accuracy_improvement: Optional[float] = None,
        profit_improvement: Optional[float] = None,
        convergence_score: Optional[float] = None,
        confidence_level: Optional[float] = None,
        sample_size: Optional[int] = None,
    ) -> Optional[LearningResultModel]:
        """Save learning results to database"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                learning_result = LearningResultModel(
                    cycle_type=cycle_type,
                    trade_count=trade_count,
                    learning_duration=learning_duration,
                    calibration_results=calibration_results,
                    performance_report=performance_report,
                    strategy_updates=strategy_updates,
                    parameter_adjustments=parameter_adjustments,
                    performance_impact=performance_impact,
                    accuracy_improvement=accuracy_improvement,
                    profit_improvement=profit_improvement,
                    convergence_score=convergence_score,
                    confidence_level=confidence_level,
                    sample_size=sample_size,
                )

                session.add(learning_result)
                await session.commit()
                await session.refresh(learning_result)

                return learning_result

        except Exception as e:
            print(f"Error saving learning results: {e}")
            await session.rollback()
            return None

    async def save_system_health(
        self,
        status: str = "HEALTHY",
        uptime: float = 0.0,
        trading_engine_status: str = "RUNNING",
        database_status: str = "CONNECTED",
        llm_service_status: str = "AVAILABLE",
        market_data_status: str = "STREAMING",
        cpu_usage: float = 0.0,
        memory_usage: float = 0.0,
        disk_usage: float = 0.0,
        network_io: float = 0.0,
        error_count: int = 0,
        warning_count: int = 0,
        last_error: Optional[str] = None,
        last_error_time: Optional[datetime] = None,
        response_time: Optional[float] = None,
        throughput: Optional[float] = None,
        queue_size: int = 0,
    ) -> Optional[SystemHealthModel]:
        """Save system health metrics to database"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                system_health = SystemHealthModel(
                    status=status,
                    uptime=uptime,
                    trading_engine_status=trading_engine_status,
                    database_status=database_status,
                    llm_service_status=llm_service_status,
                    market_data_status=market_data_status,
                    cpu_usage=cpu_usage,
                    memory_usage=memory_usage,
                    disk_usage=disk_usage,
                    network_io=network_io,
                    error_count=error_count,
                    warning_count=warning_count,
                    last_error=last_error,
                    last_error_time=last_error_time,
                    response_time=response_time,
                    throughput=throughput,
                    queue_size=queue_size,
                )

                session.add(system_health)
                await session.commit()
                await session.refresh(system_health)

                return system_health

        except Exception as e:
            print(f"Error saving system health: {e}")
            await session.rollback()
            return None

    async def get_performance_metrics(
        self, hours: int = 24
    ) -> List[PerformanceMetricModel]:
        """Get performance metrics for the last N hours"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                start_time = datetime.now(timezone.utc) - timezone.timedelta(
                    hours=hours
                )

                stmt = (
                    select(PerformanceMetricModel)
                    .where(PerformanceMetricModel.timestamp >= start_time)
                    .order_by(desc(PerformanceMetricModel.timestamp))
                )

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting performance metrics: {e}")
            return []

    async def get_learning_results(
        self, days: int = 7, cycle_type: Optional[str] = None
    ) -> List[LearningResultModel]:
        """Get learning results for the last N days"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                start_time = datetime.now(timezone.utc) - timezone.timedelta(days=days)

                stmt = select(LearningResultModel).where(
                    LearningResultModel.timestamp >= start_time
                )

                if cycle_type:
                    stmt = stmt.where(LearningResultModel.cycle_type == cycle_type)

                stmt = stmt.order_by(desc(LearningResultModel.timestamp))

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting learning results: {e}")
            return []

    async def get_system_health(self, hours: int = 1) -> List[SystemHealthModel]:
        """Get system health metrics for the last N hours"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                start_time = datetime.now(timezone.utc) - timezone.timedelta(
                    hours=hours
                )

                stmt = (
                    select(SystemHealthModel)
                    .where(SystemHealthModel.timestamp >= start_time)
                    .order_by(desc(SystemHealthModel.timestamp))
                )

                result = await session.execute(stmt)
                return result.scalars().all()

        except Exception as e:
            print(f"Error getting system health: {e}")
            return []

    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get a comprehensive performance summary"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                start_time = datetime.now(timezone.utc) - timezone.timedelta(days=days)

                # Get average performance metrics
                stmt = select(
                    func.avg(PerformanceMetricModel.daily_pnl).label("avg_daily_pnl"),
                    func.avg(PerformanceMetricModel.win_rate).label("avg_win_rate"),
                    func.sum(PerformanceMetricModel.total_trades).label("total_trades"),
                    func.max(PerformanceMetricModel.max_drawdown).label("max_drawdown"),
                    func.avg(PerformanceMetricModel.sharpe_ratio).label(
                        "avg_sharpe_ratio"
                    ),
                    func.avg(PerformanceMetricModel.cpu_usage).label("avg_cpu_usage"),
                    func.avg(PerformanceMetricModel.memory_usage).label(
                        "avg_memory_usage"
                    ),
                    func.count(PerformanceMetricModel.id).label("data_points"),
                ).where(PerformanceMetricModel.timestamp >= start_time)

                result = await session.execute(stmt)
                row = result.first()

                # Get learning effectiveness
                learning_stmt = select(
                    func.avg(LearningResultModel.accuracy_improvement).label(
                        "avg_accuracy_improvement"
                    ),
                    func.avg(LearningResultModel.profit_improvement).label(
                        "avg_profit_improvement"
                    ),
                    func.avg(LearningResultModel.convergence_score).label(
                        "avg_convergence_score"
                    ),
                    func.count(LearningResultModel.id).label("learning_cycles"),
                ).where(
                    and_(
                        LearningResultModel.timestamp >= start_time,
                        LearningResultModel.accuracy_improvement.isnot(None),
                    )
                )

                learning_result = await session.execute(learning_stmt)
                learning_row = learning_result.first()

                # Get system availability
                health_stmt = select(
                    func.count(func.distinct(SystemHealthModel.status)).label(
                        "status_changes"
                    ),
                    func.avg(SystemHealthModel.cpu_usage).label("health_avg_cpu"),
                    func.avg(SystemHealthModel.memory_usage).label("health_avg_memory"),
                    func.sum(SystemHealthModel.error_count).label("total_errors"),
                ).where(SystemHealthModel.timestamp >= start_time)

                health_result = await session.execute(health_stmt)
                health_row = health_result.first()

                return {
                    "performance_summary": {
                        "avg_daily_pnl": float(row.avg_daily_pnl)
                        if row.avg_daily_pnl
                        else 0.0,
                        "avg_win_rate": float(row.avg_win_rate)
                        if row.avg_win_rate
                        else 0.0,
                        "total_trades": int(row.total_trades)
                        if row.total_trades
                        else 0,
                        "max_drawdown": float(row.max_drawdown)
                        if row.max_drawdown
                        else 0.0,
                        "avg_sharpe_ratio": float(row.avg_sharpe_ratio)
                        if row.avg_sharpe_ratio
                        else 0.0,
                        "data_points": int(row.data_points) if row.data_points else 0,
                    },
                    "learning_summary": {
                        "avg_accuracy_improvement": float(
                            learning_row.avg_accuracy_improvement
                        )
                        if learning_row.avg_accuracy_improvement
                        else 0.0,
                        "avg_profit_improvement": float(
                            learning_row.avg_profit_improvement
                        )
                        if learning_row.avg_profit_improvement
                        else 0.0,
                        "avg_convergence_score": float(
                            learning_row.avg_convergence_score
                        )
                        if learning_row.avg_convergence_score
                        else 0.0,
                        "learning_cycles": int(learning_row.learning_cycles)
                        if learning_row.learning_cycles
                        else 0,
                    },
                    "system_summary": {
                        "status_changes": int(health_row.status_changes)
                        if health_row.status_changes
                        else 0,
                        "health_avg_cpu": float(health_row.health_avg_cpu)
                        if health_row.health_avg_cpu
                        else 0.0,
                        "health_avg_memory": float(health_row.health_avg_memory)
                        if health_row.health_avg_memory
                        else 0.0,
                        "total_errors": int(health_row.total_errors)
                        if health_row.total_errors
                        else 0,
                    },
                }

        except Exception as e:
            print(f"Error getting performance summary: {e}")
            return {}

    async def cleanup_old_data(
        self,
        performance_days: int = 90,
        learning_days: int = 180,
        health_hours: int = 24,
    ) -> Dict[str, int]:
        """Clean up old data to manage database size"""
        await self._initialize_models()

        try:
            async with get_async_session() as session:
                cleanup_counts = {}

                # Clean up old performance metrics
                perf_cutoff = datetime.now(timezone.utc) - timezone.timedelta(
                    days=performance_days
                )
                perf_stmt = select(PerformanceMetricModel).where(
                    PerformanceMetricModel.timestamp < perf_cutoff
                )
                perf_result = await session.execute(perf_stmt)
                old_perf = perf_result.scalars().all()

                for metric in old_perf:
                    await session.delete(metric)
                cleanup_counts["performance_metrics"] = len(old_perf)

                # Clean up old learning results
                learn_cutoff = datetime.now(timezone.utc) - timezone.timedelta(
                    days=learning_days
                )
                learn_stmt = select(LearningResultModel).where(
                    LearningResultModel.timestamp < learn_cutoff
                )
                learn_result = await session.execute(learn_stmt)
                old_learn = learn_result.scalars().all()

                for result in old_learn:
                    await session.delete(result)
                cleanup_counts["learning_results"] = len(old_learn)

                # Clean up old system health data
                health_cutoff = datetime.now(timezone.utc) - timezone.timedelta(
                    hours=health_hours
                )
                health_stmt = select(SystemHealthModel).where(
                    SystemHealthModel.timestamp < health_cutoff
                )
                health_result = await session.execute(health_stmt)
                old_health = health_result.scalars().all()

                for health in old_health:
                    await session.delete(health)
                cleanup_counts["system_health"] = len(old_health)

                await session.commit()

                return cleanup_counts

        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            await session.rollback()
            return {}
