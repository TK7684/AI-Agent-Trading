"""
Persistence and audit logging system for the autonomous trading system.

This module provides database models, JSON journal logging, and audit trail
functionality with tamper-evident logging and hash-chain verification.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional, Union

import structlog
from pydantic import Field, field_validator
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

from .base import BaseModel as TradingBaseModel
from .enums import Direction, MarketRegime, OrderStatus
from .orders import ExecutionResult, OrderDecision
from .signals import Signal

logger = structlog.get_logger(__name__)

# Database Models
Base = declarative_base()
metadata = MetaData()


class TradeRecord(Base):
    """Database model for completed trades."""
    __tablename__ = "trades"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False)  # LONG/SHORT
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)
    status = Column(String, nullable=False)  # OPEN/CLOSED/CANCELLED
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    pattern_id = Column(String, nullable=True, index=True)
    confidence_score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    trade_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    positions = relationship("PositionRecord", back_populates="trade")

    __table_args__ = (
        Index('idx_trades_symbol_time', 'symbol', 'entry_time'),
        Index('idx_trades_pattern_time', 'pattern_id', 'entry_time'),
    )


class PositionRecord(Base):
    """Database model for position snapshots."""
    __tablename__ = "positions"

    id = Column(String, primary_key=True)
    trade_id = Column(String, ForeignKey("trades.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    unrealized_pnl_percentage = Column(Float, nullable=False)
    margin_used = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    position_metadata = Column(JSON, nullable=True)

    # Relationships
    trade = relationship("TradeRecord", back_populates="positions")

    __table_args__ = (
        Index('idx_positions_symbol_time', 'symbol', 'timestamp'),
    )


class PerformanceMetric(Base):
    """Database model for performance metrics."""
    __tablename__ = "performance_metrics"

    id = Column(String, primary_key=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(String, nullable=True, index=True)
    pattern_id = Column(String, nullable=True, index=True)
    timeframe = Column(String, nullable=True)
    metric_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_metrics_name_time', 'metric_name', 'timestamp'),
        Index('idx_metrics_pattern_time', 'pattern_id', 'timestamp'),
    )


class AuditLog(Base):
    """Database model for audit trail entries."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    user_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    hash_chain = Column(String, nullable=False)  # For tamper evidence
    previous_hash = Column(String, nullable=True)

    __table_args__ = (
        Index('idx_audit_type_time', 'event_type', 'timestamp'),
    )


# Pydantic Models for API/Serialization
class TradeRecordModel(TradingBaseModel):
    """Pydantic model for trade records."""
    id: str
    symbol: str
    direction: Direction
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    fees: float = 0.0
    status: OrderStatus
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pattern_id: Optional[str] = None
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None
    trade_metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class PositionRecordModel(TradingBaseModel):
    """Pydantic model for position records."""
    id: str
    trade_id: str
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    margin_used: float
    timestamp: datetime
    position_metadata: Optional[dict[str, Any]] = None


class PerformanceMetricModel(TradingBaseModel):
    """Pydantic model for performance metrics."""
    id: str
    metric_name: str
    metric_value: float
    period_start: datetime
    period_end: datetime
    symbol: Optional[str] = None
    pattern_id: Optional[str] = None
    timeframe: Optional[str] = None
    metric_metadata: Optional[dict[str, Any]] = None
    timestamp: datetime


class AuditLogModel(TradingBaseModel):
    """Pydantic model for audit log entries."""
    id: str
    event_type: str
    event_data: dict[str, Any]
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime
    hash_chain: str
    previous_hash: Optional[str] = None


class JournalEntry(TradingBaseModel):
    """Model for JSON journal entries."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    event_data: dict[str, Any]
    session_id: Optional[str] = None
    hash_chain: str
    previous_hash: Optional[str] = None

    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_timezone(cls, v):
        from datetime import datetime as dt
        if isinstance(v, dt) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class MarketSnapshot(TradingBaseModel):
    """Model for market data snapshots in audit logs."""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    indicators: dict[str, float]
    patterns: list[str]
    regime: MarketRegime


class DecisionContext(TradingBaseModel):
    """Model for trading decision context in audit logs."""
    signal: Signal
    market_snapshot: MarketSnapshot
    risk_assessment: dict[str, Any]
    reasoning_steps: list[str]
    confidence_factors: dict[str, float]
    llm_analysis: Optional[dict[str, Any]] = None


class InitializationResult(TradingBaseModel):
    """Result of database initialization."""
    success: bool
    tables_created: list[str]
    tables_skipped: list[str]
    errors: list[str]
    duration_ms: float


class SchemaVersion(TradingBaseModel):
    """Schema version information."""
    current_version: str
    expected_version: str
    compatible: bool
    migration_needed: bool


class DatabaseManager:
    """Manages database connections and operations."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables (legacy method for compatibility)."""
        Base.metadata.create_all(bind=self.engine)

    def create_tables_safe(self) -> bool:
        """
        Create tables safely (idempotent operation).

        Returns:
            True if successful
        """
        try:
            result = self.initialize_schema()
            if result.success:
                logger.info("Database tables created successfully",
                          tables_created=len(result.tables_created),
                          tables_skipped=len(result.tables_skipped))
                return True
            else:
                logger.error("Failed to create database tables", errors=result.errors)
                return False
        except Exception as e:
            logger.error("Error creating tables safely", error=str(e))
            return False

    def create_tables_safe(self) -> bool:
        """
        Create tables safely (idempotent operation).

        Returns:
            True if successful
        """
        try:
            Base.metadata.create_all(bind=self.engine, checkfirst=True)
            logger.info("Database tables created successfully")
            return True
        except Exception as e:
            logger.error("Error creating tables", error=str(e))
            return False

    def initialize_schema(self) -> InitializationResult:
        """
        Initialize database schema with detailed reporting.

        Returns:
            InitializationResult with details about the operation
        """
        import time

        from sqlalchemy import inspect

        start_time = time.time()
        tables_created = []
        tables_skipped = []
        errors = []

        try:
            inspector = inspect(self.engine)
            existing_tables = set(inspector.get_table_names())

            # Get all tables from metadata
            expected_tables = set(Base.metadata.tables.keys())

            # Identify which tables need to be created
            tables_to_create = expected_tables - existing_tables
            tables_skipped = list(existing_tables & expected_tables)

            if tables_to_create:
                logger.info(f"Creating {len(tables_to_create)} tables", tables=list(tables_to_create))

                # Create only missing tables
                Base.metadata.create_all(bind=self.engine, checkfirst=True)

                # Verify creation
                inspector = inspect(self.engine)
                new_tables = set(inspector.get_table_names())
                tables_created = list(tables_to_create & new_tables)

                logger.info(f"Created {len(tables_created)} tables successfully")
            else:
                logger.info("All tables already exist, skipping creation")

            duration_ms = (time.time() - start_time) * 1000

            return InitializationResult(
                success=True,
                tables_created=tables_created,
                tables_skipped=tables_skipped,
                errors=errors,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            errors.append(error_msg)

            logger.error("Schema initialization failed", error=error_msg)

            return InitializationResult(
                success=False,
                tables_created=tables_created,
                tables_skipped=tables_skipped,
                errors=errors,
                duration_ms=duration_ms
            )

    def validate_schema_version(self) -> SchemaVersion:
        """
        Validate schema version compatibility.

        Returns:
            SchemaVersion with compatibility information
        """
        # For now, we'll use a simple version check
        # In a production system, this would check a schema_version table

        try:
            from sqlalchemy import inspect

            inspector = inspect(self.engine)
            existing_tables = set(inspector.get_table_names())
            expected_tables = set(Base.metadata.tables.keys())

            # Check if all expected tables exist
            compatible = expected_tables.issubset(existing_tables)
            migration_needed = not compatible

            return SchemaVersion(
                current_version=self.SCHEMA_VERSION,
                expected_version=self.SCHEMA_VERSION,
                compatible=compatible,
                migration_needed=migration_needed
            )

        except Exception as e:
            logger.error("Schema version validation failed", error=str(e))
            return SchemaVersion(
                current_version="unknown",
                expected_version=self.SCHEMA_VERSION,
                compatible=False,
                migration_needed=True
            )

    def migrate_if_needed(self) -> dict[str, Any]:
        """
        Perform schema migration if needed.

        Returns:
            Dictionary with migration results
        """
        schema_version = self.validate_schema_version()

        if not schema_version.migration_needed:
            return {
                "migration_performed": False,
                "reason": "Schema is up to date"
            }

        # Perform migration by creating missing tables
        result = self.initialize_schema()

        return {
            "migration_performed": True,
            "success": result.success,
            "tables_created": result.tables_created,
            "errors": result.errors
        }

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error("Database connection test failed", error=str(e))
            return False

    def initialize_with_validation(self) -> InitializationResult:
        """
        Initialize schema with connection validation first.

        Returns:
            InitializationResult with validation and initialization details
        """
        # Test connection first
        if not self.test_connection():
            return InitializationResult(
                success=False,
                tables_created=[],
                tables_skipped=[],
                errors=["Database connection failed"],
                duration_ms=0.0
            )

        # Proceed with schema initialization
        return self.initialize_schema()

    def close(self):
        """Close database connections."""
        self.engine.dispose()


class JSONJournal:
    """Append-only JSON journal for audit trail."""

    def __init__(self, journal_path: Union[str, Path]):
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash: Optional[str] = None
        self._load_last_hash()

    def _load_last_hash(self):
        """Load the last hash from the journal file."""
        if self.journal_path.exists():
            try:
                with open(self.journal_path) as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1].strip())
                        self._last_hash = last_entry.get('hash_chain')
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to load last hash from journal", error=str(e))

    def _calculate_hash(self, entry_data: dict[str, Any], previous_hash: Optional[str]) -> str:
        """Calculate hash for tamper-evident logging."""
        # Create a consistent hash input by serializing the data
        hash_data = {
            'id': entry_data['id'],
            'timestamp': entry_data['timestamp'] if isinstance(entry_data['timestamp'], str) else entry_data['timestamp'].isoformat(),
            'event_type': entry_data['event_type'],
            'event_data': entry_data['event_data'],
            'session_id': entry_data.get('session_id')
        }
        hash_input = json.dumps(hash_data, sort_keys=True, default=str)
        if previous_hash:
            hash_input = f"{previous_hash}:{hash_input}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def append(self, event_type: str, event_data: dict[str, Any],
               session_id: Optional[str] = None) -> JournalEntry:
        """Append an entry to the journal."""
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(UTC)

        # Calculate hash chain
        hash_data = {
            'id': entry_id,
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'event_data': event_data,
            'session_id': session_id
        }

        hash_chain = self._calculate_hash(hash_data, self._last_hash)

        entry = JournalEntry(
            id=entry_id,
            timestamp=timestamp,
            event_type=event_type,
            event_data=event_data,
            session_id=session_id,
            hash_chain=hash_chain,
            previous_hash=self._last_hash
        )

        # Write to file - use the same hash_data format for consistency
        file_entry = {
            'id': entry_id,
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'event_data': event_data,
            'session_id': session_id,
            'hash_chain': hash_chain,
            'previous_hash': self._last_hash
        }
        with open(self.journal_path, 'a') as f:
            f.write(json.dumps(file_entry, default=str) + '\n')

        self._last_hash = hash_chain
        return entry

    def verify_integrity(self) -> bool:
        """Verify the integrity of the journal using hash chains."""
        if not self.journal_path.exists():
            return True

        try:
            with open(self.journal_path) as f:
                lines = f.readlines()

            previous_hash = None
            for line in lines:
                entry_data = json.loads(line.strip())

                # Recalculate hash using the same method as when creating
                # Remove hash_chain and previous_hash from entry_data for hash calculation
                hash_data = {k: v for k, v in entry_data.items()
                           if k not in ['hash_chain', 'previous_hash']}
                expected_hash = self._calculate_hash(hash_data, previous_hash)

                if entry_data['hash_chain'] != expected_hash:
                    logger.error("Hash chain verification failed",
                               entry_id=entry_data['id'],
                               expected=expected_hash,
                               actual=entry_data['hash_chain'])
                    return False

                if entry_data.get('previous_hash') != previous_hash:
                    logger.error("Previous hash mismatch",
                               entry_id=entry_data['id'],
                               expected=previous_hash,
                               actual=entry_data.get('previous_hash'))
                    return False

                previous_hash = entry_data['hash_chain']

            return True

        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to verify journal integrity", error=str(e))
            return False

    def read_entries(self, start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    event_type: Optional[str] = None) -> list[JournalEntry]:
        """Read entries from the journal with optional filtering."""
        if not self.journal_path.exists():
            return []

        entries = []
        try:
            with open(self.journal_path) as f:
                for line in f:
                    entry_data = json.loads(line.strip())
                    entry = JournalEntry(**entry_data)

                    # Apply filters
                    if start_time and entry.timestamp < start_time:
                        continue
                    if end_time and entry.timestamp > end_time:
                        continue
                    if event_type and entry.event_type != event_type:
                        continue

                    entries.append(entry)

        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read journal entries", error=str(e))

        return entries


class StructuredLogger:
    """Structured logger with reasoning steps and market snapshots."""

    def __init__(self, journal: JSONJournal, db_manager: DatabaseManager):
        self.journal = journal
        self.db_manager = db_manager
        self.session_id = str(uuid.uuid4())

    def log_trading_decision(self, decision_context: DecisionContext,
                           order_decision: OrderDecision) -> None:
        """Log a trading decision with full context."""
        event_data = {
            'decision_context': decision_context.model_dump(),
            'order_decision': order_decision.model_dump(),
            'decision_id': str(uuid.uuid4())
        }

        # Log to journal
        self.journal.append('trading_decision', event_data, self.session_id)

        # Log to database
        with self.db_manager.get_session() as session:
            audit_entry = AuditLog(
                id=str(uuid.uuid4()),
                event_type='trading_decision',
                event_data=event_data,
                session_id=self.session_id,
                hash_chain=self.journal._last_hash or '',
                previous_hash=None
            )
            session.add(audit_entry)
            session.commit()

    def log_execution_result(self, order_decision: OrderDecision,
                           execution_result: ExecutionResult) -> None:
        """Log order execution results."""
        event_data = {
            'order_decision': order_decision.model_dump(),
            'execution_result': execution_result.model_dump(),
            'execution_id': str(uuid.uuid4())
        }

        self.journal.append('execution_result', event_data, self.session_id)

        with self.db_manager.get_session() as session:
            audit_entry = AuditLog(
                id=str(uuid.uuid4()),
                event_type='execution_result',
                event_data=event_data,
                session_id=self.session_id,
                hash_chain=self.journal._last_hash or '',
                previous_hash=None
            )
            session.add(audit_entry)
            session.commit()

    def log_risk_event(self, event_type: str, risk_data: dict[str, Any]) -> None:
        """Log risk management events."""
        event_data = {
            'risk_event_type': event_type,
            'risk_data': risk_data,
            'timestamp': datetime.now(UTC).isoformat()
        }

        self.journal.append('risk_event', event_data, self.session_id)

    def log_system_event(self, event_type: str, system_data: dict[str, Any]) -> None:
        """Log system events and errors."""
        event_data = {
            'system_event_type': event_type,
            'system_data': system_data,
            'timestamp': datetime.now(UTC).isoformat()
        }

        self.journal.append('system_event', event_data, self.session_id)


class PersistenceManager:
    """Main persistence manager coordinating all persistence operations."""

    def __init__(self, database_url: str, journal_path: Union[str, Path]):
        self.db_manager = DatabaseManager(database_url)
        self.journal = JSONJournal(journal_path)
        self.logger = StructuredLogger(self.journal, self.db_manager)

    def initialize(self):
        """Initialize the persistence system."""
        self.db_manager.create_tables()

        # Verify journal integrity on startup
        if not self.journal.verify_integrity():
            raise RuntimeError("Journal integrity verification failed")

    def save_trade(self, trade_data: TradeRecordModel) -> None:
        """Save a trade record to the database."""
        with self.db_manager.get_session() as session:
            trade_record = TradeRecord(
                id=trade_data.id,
                symbol=trade_data.symbol,
                direction=trade_data.direction.value if hasattr(trade_data.direction, 'value') else trade_data.direction,
                entry_price=trade_data.entry_price,
                exit_price=trade_data.exit_price,
                quantity=trade_data.quantity,
                entry_time=trade_data.entry_time,
                exit_time=trade_data.exit_time,
                pnl=trade_data.pnl,
                pnl_percentage=trade_data.pnl_percentage,
                fees=trade_data.fees,
                status=trade_data.status.value if hasattr(trade_data.status, 'value') else trade_data.status,
                stop_loss=trade_data.stop_loss,
                take_profit=trade_data.take_profit,
                pattern_id=trade_data.pattern_id,
                confidence_score=trade_data.confidence_score,
                reasoning=trade_data.reasoning,
                trade_metadata=trade_data.trade_metadata,
                created_at=trade_data.created_at,
                updated_at=trade_data.updated_at
            )
            session.add(trade_record)
            session.commit()

    def save_position_snapshot(self, position_data: PositionRecordModel) -> None:
        """Save a position snapshot to the database."""
        with self.db_manager.get_session() as session:
            position_record = PositionRecord(
                id=position_data.id,
                trade_id=position_data.trade_id,
                symbol=position_data.symbol,
                quantity=position_data.quantity,
                average_price=position_data.average_price,
                current_price=position_data.current_price,
                unrealized_pnl=position_data.unrealized_pnl,
                unrealized_pnl_percentage=position_data.unrealized_pnl_percentage,
                margin_used=position_data.margin_used,
                timestamp=position_data.timestamp,
                position_metadata=position_data.position_metadata
            )
            session.add(position_record)
            session.commit()

    def save_performance_metric(self, metric_data: PerformanceMetricModel) -> None:
        """Save a performance metric to the database."""
        with self.db_manager.get_session() as session:
            metric_record = PerformanceMetric(
                id=metric_data.id,
                metric_name=metric_data.metric_name,
                metric_value=metric_data.metric_value,
                period_start=metric_data.period_start,
                period_end=metric_data.period_end,
                symbol=metric_data.symbol,
                pattern_id=metric_data.pattern_id,
                timeframe=metric_data.timeframe,
                metric_metadata=metric_data.metric_metadata,
                timestamp=metric_data.timestamp
            )
            session.add(metric_record)
            session.commit()

    def get_trades(self, symbol: Optional[str] = None,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None) -> list[TradeRecordModel]:
        """Retrieve trade records with optional filtering."""
        with self.db_manager.get_session() as session:
            query = session.query(TradeRecord)

            if symbol:
                query = query.filter(TradeRecord.symbol == symbol)
            if start_time:
                query = query.filter(TradeRecord.entry_time >= start_time)
            if end_time:
                query = query.filter(TradeRecord.entry_time <= end_time)

            trades = query.order_by(TradeRecord.entry_time.desc()).all()

            return [
                TradeRecordModel(
                    id=trade.id,
                    symbol=trade.symbol,
                    direction=Direction(trade.direction),
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    quantity=trade.quantity,
                    entry_time=trade.entry_time,
                    exit_time=trade.exit_time,
                    pnl=trade.pnl,
                    pnl_percentage=trade.pnl_percentage,
                    fees=trade.fees,
                    status=OrderStatus(trade.status),
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    pattern_id=trade.pattern_id,
                    confidence_score=trade.confidence_score,
                    reasoning=trade.reasoning,
                    trade_metadata=trade.trade_metadata,
                    created_at=trade.created_at,
                    updated_at=trade.updated_at
                ) for trade in trades
            ]

    def export_data(self, output_path: Union[str, Path],
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> None:
        """Export data for debugging and analysis."""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export trades
        trades = self.get_trades(start_time=start_time, end_time=end_time)
        with open(output_path / 'trades.json', 'w') as f:
            json.dump([trade.model_dump() for trade in trades], f, indent=2, default=str)

        # Export journal entries
        journal_entries = self.journal.read_entries(start_time=start_time, end_time=end_time)
        with open(output_path / 'journal.json', 'w') as f:
            json.dump([entry.model_dump() for entry in journal_entries], f, indent=2, default=str)

        # Export performance metrics
        with self.db_manager.get_session() as session:
            query = session.query(PerformanceMetric)
            if start_time:
                query = query.filter(PerformanceMetric.timestamp >= start_time)
            if end_time:
                query = query.filter(PerformanceMetric.timestamp <= end_time)

            metrics = query.all()
            metrics_data = [
                {
                    'id': metric.id,
                    'metric_name': metric.metric_name,
                    'metric_value': metric.metric_value,
                    'period_start': metric.period_start.isoformat(),
                    'period_end': metric.period_end.isoformat(),
                    'symbol': metric.symbol,
                    'pattern_id': metric.pattern_id,
                    'timeframe': metric.timeframe,
                    'metric_metadata': metric.metric_metadata,
                    'timestamp': metric.timestamp.isoformat()
                } for metric in metrics
            ]

            with open(output_path / 'metrics.json', 'w') as f:
                json.dump(metrics_data, f, indent=2)

    def close(self):
        """Close all connections and cleanup."""
        self.db_manager.close()
