"""
Tests for persistence and audit logging system.

This module tests database operations, JSON journal functionality,
structured logging, and data integrity verification.
"""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import text

from libs.trading_models.enums import Direction, MarketRegime, OrderStatus
from libs.trading_models.migrations import (
    BackupManager,
    DataReplaySystem,
    MigrationManager,
)
from libs.trading_models.orders import ExecutionResult, OrderDecision
from libs.trading_models.persistence import (
    DatabaseManager,
    DecisionContext,
    JournalEntry,
    JSONJournal,
    MarketSnapshot,
    PerformanceMetric,
    PerformanceMetricModel,
    PersistenceManager,
    PositionRecord,
    PositionRecordModel,
    StructuredLogger,
    TradeRecordModel,
)
from libs.trading_models.signals import Signal


class TestDatabaseManager:
    """Test database manager functionality."""

    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        # Use in-memory SQLite for testing
        database_url = "sqlite:///:memory:"
        manager = DatabaseManager(database_url)
        manager.create_tables()
        yield manager
        manager.close()

    def test_create_tables(self, db_manager):
        """Test table creation."""
        # Tables should be created without errors
        with db_manager.get_session() as session:
            # Check that tables exist by querying them
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]

            expected_tables = ['trades', 'positions', 'performance_metrics', 'audit_logs']
            for table in expected_tables:
                assert table in table_names

    def test_session_management(self, db_manager):
        """Test database session management."""
        session = db_manager.get_session()
        assert session is not None

        # Session should be usable
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1

        session.close()


class TestJSONJournal:
    """Test JSON journal functionality."""

    @pytest.fixture
    def journal(self):
        """Create a test JSON journal."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"
            yield JSONJournal(journal_path)

    def test_append_entry(self, journal):
        """Test appending entries to journal."""
        event_data = {"test": "data", "value": 123}
        entry = journal.append("test_event", event_data, "session_123")

        assert entry.event_type == "test_event"
        assert entry.event_data == event_data
        assert entry.session_id == "session_123"
        assert entry.hash_chain is not None
        assert entry.previous_hash is None  # First entry

    def test_hash_chain_integrity(self, journal):
        """Test hash chain integrity."""
        # Add multiple entries
        entries = []
        for i in range(5):
            event_data = {"entry": i, "timestamp": datetime.now().isoformat()}
            entry = journal.append(f"event_{i}", event_data)
            entries.append(entry)

        # Verify hash chain
        assert journal.verify_integrity()

        # Check that each entry references the previous hash correctly
        for i in range(1, len(entries)):
            assert entries[i].previous_hash == entries[i-1].hash_chain

    def test_integrity_verification_failure(self, journal):
        """Test integrity verification with tampered data."""
        # Add some entries
        journal.append("event_1", {"data": "test1"})
        journal.append("event_2", {"data": "test2"})

        # Tamper with the journal file
        with open(journal.journal_path) as f:
            lines = f.readlines()

        # Modify the second entry
        if len(lines) >= 2:
            entry_data = json.loads(lines[1])
            entry_data['event_data']['data'] = 'tampered'
            lines[1] = json.dumps(entry_data) + '\n'

            with open(journal.journal_path, 'w') as f:
                f.writelines(lines)

            # Verification should fail
            assert not journal.verify_integrity()

    def test_read_entries_filtering(self, journal):
        """Test reading entries with filtering."""
        base_time = datetime.now(UTC)

        # Add entries with different timestamps and types
        for i in range(5):
            event_time = base_time + timedelta(minutes=i)
            with patch('libs.trading_models.persistence.datetime') as mock_datetime:
                mock_datetime.now.return_value = event_time
                mock_datetime.utcnow.return_value = event_time
                journal.append(f"type_{i % 2}", {"index": i})

        # Test time filtering
        start_time = base_time + timedelta(minutes=2)
        end_time = base_time + timedelta(minutes=3)  # Exclusive end to get only minutes 2 and 3
        filtered_entries = journal.read_entries(start_time=start_time, end_time=end_time)

        assert len(filtered_entries) == 2  # Should get entries at minutes 2 and 3

        # Test event type filtering
        type_filtered = journal.read_entries(event_type="type_0")
        assert len(type_filtered) == 3  # Entries 0, 2, 4

    def test_empty_journal_integrity(self, journal):
        """Test integrity verification on empty journal."""
        assert journal.verify_integrity()  # Empty journal should be valid


class TestStructuredLogger:
    """Test structured logging functionality."""

    @pytest.fixture
    def logger_setup(self):
        """Set up structured logger with mocked dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"
            journal = JSONJournal(journal_path)

            db_manager = Mock()
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            db_manager.get_session.return_value = mock_context_manager

            logger = StructuredLogger(journal, db_manager)
            yield logger, journal, mock_session

    def test_log_trading_decision(self, logger_setup):
        """Test logging trading decisions."""
        logger, journal, mock_session = logger_setup

        # Create test data
        market_snapshot = MarketSnapshot(
            symbol="BTCUSD",
            timestamp=datetime.now(UTC),
            price=50000.0,
            volume=1000.0,
            indicators={"rsi": 65.0, "ema_20": 49500.0},
            patterns=["bullish_engulfing"],
            regime=MarketRegime.BULL
        )

        signal = Signal(
            signal_id="signal_123",
            symbol="BTCUSD",
            direction=Direction.LONG,
            confidence=0.85,
            confluence_score=85.0,
            market_regime=MarketRegime.BULL,
            primary_timeframe="1h",
            reasoning="Strong bullish momentum with RSI confirmation",
            timeframe_analysis={},
            llm_analysis=None,
            timestamp=datetime.now(UTC)
        )

        decision_context = DecisionContext(
            signal=signal,
            market_snapshot=market_snapshot,
            risk_assessment={"position_size": 0.02, "stop_loss": 48000.0},
            reasoning_steps=["Analyze indicators", "Check patterns", "Assess risk"],
            confidence_factors={"technical": 0.8, "fundamental": 0.7}
        )

        from decimal import Decimal
        order_decision = OrderDecision(
            signal_id="signal_123",
            symbol="BTCUSD",
            direction=Direction.LONG,
            order_type="market",
            base_quantity=Decimal("0.1"),
            risk_adjusted_quantity=Decimal("0.1"),
            max_position_value=Decimal("5000.0"),
            entry_price=Decimal("50000.0"),
            stop_loss=Decimal("48000.0"),
            take_profit=Decimal("55000.0"),
            risk_amount=Decimal("1000.0"),
            risk_percentage=2.0,
            portfolio_value=Decimal("50000.0"),
            available_margin=Decimal("10000.0"),
            confidence_score=0.85,
            confluence_score=85.0,
            risk_reward_ratio=2.5,
            decision_reason="High confidence bullish signal",
            timeframe_context="1h"
        )

        # Log the decision
        logger.log_trading_decision(decision_context, order_decision)

        # Verify journal entry
        entries = journal.read_entries()
        assert len(entries) == 1
        assert entries[0].event_type == "trading_decision"
        assert "decision_context" in entries[0].event_data
        assert "order_decision" in entries[0].event_data

        # Verify database call
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_log_execution_result(self, logger_setup):
        """Test logging execution results."""
        logger, journal, mock_session = logger_setup

        from decimal import Decimal
        order_decision = OrderDecision(
            signal_id="signal_test",
            symbol="BTCUSD",
            direction=Direction.LONG,
            order_type="market",
            base_quantity=Decimal("0.1"),
            risk_adjusted_quantity=Decimal("0.1"),
            max_position_value=Decimal("5000.0"),
            entry_price=Decimal("50000.0"),
            stop_loss=Decimal("48000.0"),
            risk_amount=Decimal("1000.0"),
            risk_percentage=2.0,
            portfolio_value=Decimal("50000.0"),
            available_margin=Decimal("10000.0"),
            confidence_score=0.8,
            confluence_score=80.0,
            risk_reward_ratio=2.0,
            decision_reason="Test order",
            timeframe_context="1h"
        )

        execution_result = ExecutionResult(
            decision_id="decision_test",
            order_id="order_123",
            status="filled",
            submitted_at=datetime.now(UTC),
            filled_quantity=Decimal("0.1"),
            average_price=Decimal("50050.0"),
            commission=Decimal("25.0")
        )

        logger.log_execution_result(order_decision, execution_result)

        # Verify logging
        entries = journal.read_entries()
        assert len(entries) == 1
        assert entries[0].event_type == "execution_result"

    def test_log_risk_event(self, logger_setup):
        """Test logging risk events."""
        logger, journal, mock_session = logger_setup

        risk_data = {
            "event": "drawdown_limit_exceeded",
            "current_drawdown": 0.12,
            "limit": 0.10,
            "action": "safe_mode_activated"
        }

        logger.log_risk_event("drawdown_protection", risk_data)

        entries = journal.read_entries()
        assert len(entries) == 1
        assert entries[0].event_type == "risk_event"
        assert entries[0].event_data["risk_event_type"] == "drawdown_protection"

    def test_log_system_event(self, logger_setup):
        """Test logging system events."""
        logger, journal, mock_session = logger_setup

        system_data = {
            "component": "market_data_ingestion",
            "error": "WebSocket connection lost",
            "retry_count": 3,
            "recovery_action": "switch_to_rest_api"
        }

        logger.log_system_event("connection_failure", system_data)

        entries = journal.read_entries()
        assert len(entries) == 1
        assert entries[0].event_type == "system_event"


class TestPersistenceManager:
    """Test main persistence manager."""

    @pytest.fixture
    def persistence_manager(self):
        """Create a test persistence manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = "sqlite:///:memory:"
            journal_path = Path(temp_dir) / "test_journal.jsonl"

            manager = PersistenceManager(database_url, journal_path)
            manager.initialize()
            yield manager
            manager.close()

    def test_save_and_retrieve_trade(self, persistence_manager):
        """Test saving and retrieving trade records."""
        trade_data = TradeRecordModel(
            id="trade_123",
            symbol="BTCUSD",
            direction=Direction.LONG,
            entry_price=50000.0,
            exit_price=55000.0,
            quantity=0.1,
            entry_time=datetime.now(UTC),
            exit_time=datetime.now(UTC) + timedelta(hours=2),
            pnl=500.0,
            pnl_percentage=10.0,
            fees=25.0,
            status=OrderStatus.FILLED,
            stop_loss=48000.0,
            take_profit=55000.0,
            pattern_id="bullish_engulfing_001",
            confidence_score=0.85,
            reasoning="Strong bullish momentum",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        # Save trade
        persistence_manager.save_trade(trade_data)

        # Retrieve trades
        trades = persistence_manager.get_trades(symbol="BTCUSD")
        assert len(trades) == 1
        assert trades[0].id == "trade_123"
        assert trades[0].symbol == "BTCUSD"
        assert trades[0].pnl == 500.0

    def test_save_position_snapshot(self, persistence_manager):
        """Test saving position snapshots."""
        position_data = PositionRecordModel(
            id="position_123",
            trade_id="trade_123",
            symbol="BTCUSD",
            quantity=0.1,
            average_price=50000.0,
            current_price=51000.0,
            unrealized_pnl=100.0,
            unrealized_pnl_percentage=2.0,
            margin_used=1000.0,
            timestamp=datetime.now(UTC)
        )

        persistence_manager.save_position_snapshot(position_data)

        # Verify saved (would need additional query method in real implementation)
        with persistence_manager.db_manager.get_session() as session:
            positions = session.query(PositionRecord).all()
            assert len(positions) == 1
            assert positions[0].id == "position_123"

    def test_save_performance_metric(self, persistence_manager):
        """Test saving performance metrics."""
        metric_data = PerformanceMetricModel(
            id="metric_123",
            metric_name="win_rate",
            metric_value=0.65,
            period_start=datetime.now(UTC) - timedelta(days=30),
            period_end=datetime.now(UTC),
            symbol="BTCUSD",
            pattern_id="bullish_engulfing",
            timeframe="1h",
            timestamp=datetime.now(UTC)
        )

        persistence_manager.save_performance_metric(metric_data)

        # Verify saved
        with persistence_manager.db_manager.get_session() as session:
            metrics = session.query(PerformanceMetric).all()
            assert len(metrics) == 1
            assert metrics[0].metric_name == "win_rate"
            assert metrics[0].metric_value == 0.65

    def test_export_data(self, persistence_manager):
        """Test data export functionality."""
        # Add some test data
        trade_data = TradeRecordModel(
            id="trade_export_test",
            symbol="BTCUSD",
            direction=Direction.LONG,
            entry_price=50000.0,
            quantity=0.1,
            entry_time=datetime.now(UTC),
            status=OrderStatus.OPEN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        persistence_manager.save_trade(trade_data)

        # Add journal entry
        persistence_manager.journal.append("test_event", {"test": "data"})

        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "export"
            persistence_manager.export_data(export_path)

            # Check exported files
            assert (export_path / "trades.json").exists()
            assert (export_path / "journal.json").exists()
            assert (export_path / "metrics.json").exists()

            # Verify content
            with open(export_path / "trades.json") as f:
                trades_data = json.load(f)
                assert len(trades_data) == 1
                assert trades_data[0]["id"] == "trade_export_test"


class TestMigrationManager:
    """Test database migration management."""

    @pytest.fixture
    def migration_manager(self):
        """Create a test migration manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = "sqlite:///:memory:"
            migrations_dir = Path(temp_dir) / "migrations"

            manager = MigrationManager(database_url, migrations_dir)
            yield manager

    def test_create_alembic_config(self, migration_manager):
        """Test Alembic configuration creation."""
        assert migration_manager.alembic_ini_path.exists()

        # Check config content
        with open(migration_manager.alembic_ini_path) as f:
            config_content = f.read()
            assert "script_location" in config_content
            assert migration_manager.database_url in config_content

    def test_check_migration_status(self, migration_manager):
        """Test migration status checking."""
        status = migration_manager.check_migration_status()

        assert "current_revision" in status
        assert "total_migrations" in status
        assert "pending_migrations" in status
        assert isinstance(status["total_migrations"], int)


class TestBackupManager:
    """Test backup and restore functionality."""

    @pytest.fixture
    def backup_manager(self):
        """Create a test backup manager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = "sqlite:///test.db"
            journal_path = Path(temp_dir) / "journal.jsonl"
            backup_dir = Path(temp_dir) / "backups"

            # Create test journal
            journal_path.write_text('{"test": "data"}\n')

            manager = BackupManager(database_url, journal_path, backup_dir)
            yield manager

    def test_list_backups_empty(self, backup_manager):
        """Test listing backups when none exist."""
        backups = backup_manager.list_backups()
        assert backups == []

    def test_backup_metadata_creation(self, backup_manager):
        """Test backup metadata creation."""
        # Mock the database backup to avoid external dependencies
        with patch.object(backup_manager, '_backup_database'):
            backup_path = backup_manager.create_backup("test_backup")

            metadata_path = backup_path / "metadata.json"
            assert metadata_path.exists()

            with open(metadata_path) as f:
                metadata = json.load(f)

            assert metadata["backup_name"] == "test_backup"
            assert metadata["backup_type"] == "full"
            assert "created_at" in metadata


class TestDataReplaySystem:
    """Test data replay and analysis functionality."""

    @pytest.fixture
    def replay_system(self):
        """Create a test replay system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = "sqlite:///:memory:"
            journal_path = Path(temp_dir) / "test_journal.jsonl"

            persistence_manager = PersistenceManager(database_url, journal_path)
            persistence_manager.initialize()

            replay_system = DataReplaySystem(persistence_manager)
            yield replay_system, persistence_manager

            persistence_manager.close()

    def test_replay_trading_session(self, replay_system):
        """Test replaying a trading session."""
        replay_system_obj, persistence_manager = replay_system

        session_id = "test_session_123"

        # Add test journal entries
        persistence_manager.journal.append("event_1", {"data": "test1"}, session_id)
        persistence_manager.journal.append("event_2", {"data": "test2"}, session_id)
        persistence_manager.journal.append("event_3", {"data": "test3"}, "other_session")

        # Replay the session
        replay_data = replay_system_obj.replay_trading_session(session_id)

        assert replay_data["session_id"] == session_id
        assert replay_data["total_events"] == 2  # Only events from target session
        assert len(replay_data["events"]) == 2

    def test_replay_nonexistent_session(self, replay_system):
        """Test replaying a non-existent session."""
        replay_system_obj, _ = replay_system

        with pytest.raises(ValueError, match="No entries found for session"):
            replay_system_obj.replay_trading_session("nonexistent_session")

    def test_generate_performance_report(self, replay_system):
        """Test generating performance reports."""
        replay_system_obj, persistence_manager = replay_system

        # Add test trade data
        start_time = datetime.now(UTC) - timedelta(days=1)
        end_time = datetime.now(UTC)

        trade_data = TradeRecordModel(
            id="report_test_trade",
            symbol="BTCUSD",
            direction=Direction.LONG,
            entry_price=50000.0,
            exit_price=55000.0,
            quantity=0.1,
            entry_time=start_time + timedelta(hours=1),
            exit_time=start_time + timedelta(hours=3),
            pnl=500.0,
            fees=25.0,
            status=OrderStatus.FILLED,
            created_at=start_time,
            updated_at=start_time
        )
        persistence_manager.save_trade(trade_data)

        # Add journal entries within the time range
        entry_time = start_time + timedelta(hours=2)
        with patch('libs.trading_models.persistence.datetime') as mock_datetime:
            mock_datetime.now.return_value = entry_time
            persistence_manager.journal.append("trading_decision", {"test": "decision"})
            persistence_manager.journal.append("execution_result", {"test": "execution"})

        # Generate report
        report = replay_system_obj.generate_performance_report(start_time, end_time)

        assert report["trading_metrics"]["total_trades"] == 1
        assert report["trading_metrics"]["winning_trades"] == 1
        assert report["trading_metrics"]["total_pnl"] == 500.0
        assert report["system_metrics"]["total_events"] == 2


class TestDataIntegrity:
    """Test data integrity and validation."""

    def test_journal_entry_validation(self):
        """Test journal entry data validation."""
        # Valid entry
        entry = JournalEntry(
            event_type="test_event",
            event_data={"test": "data"},
            hash_chain="test_hash"
        )
        assert entry.event_type == "test_event"

        # Test timezone handling
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        entry_with_naive_time = JournalEntry(
            timestamp=naive_time,
            event_type="test",
            event_data={},
            hash_chain="hash"
        )
        assert entry_with_naive_time.timestamp.tzinfo == UTC

    def test_trade_record_validation(self):
        """Test trade record data validation."""
        trade = TradeRecordModel(
            id="test_trade",
            symbol="BTCUSD",
            direction=Direction.LONG,
            entry_price=50000.0,
            quantity=0.1,
            entry_time=datetime.now(UTC),
            status=OrderStatus.OPEN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )

        assert trade.symbol == "BTCUSD"
        assert trade.direction == Direction.LONG
        assert trade.entry_price == 50000.0

    def test_hash_chain_calculation(self):
        """Test hash chain calculation consistency."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "hash_test.jsonl"
            journal = JSONJournal(journal_path)

            # Add entries and verify hash consistency
            entry1 = journal.append("event_1", {"data": "test1"})
            entry2 = journal.append("event_2", {"data": "test2"})

            # Hash should be deterministic
            assert entry1.hash_chain is not None
            assert entry2.previous_hash == entry1.hash_chain

            # Verify integrity
            assert journal.verify_integrity()


class TestPersistenceEdgeCases:
    """Test edge cases and error conditions for better coverage."""

    def test_journal_with_corrupted_last_entry(self):
        """Test journal initialization with corrupted last entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "corrupted_journal.jsonl"

            # Create a journal with corrupted last entry
            with open(journal_path, 'w') as f:
                f.write('{"valid": "entry"}\n')
                f.write('invalid json line\n')  # Corrupted entry

            # Should handle corruption gracefully
            journal = JSONJournal(journal_path)
            assert journal._last_hash is None  # Should fallback gracefully

    def test_journal_io_error_handling(self):
        """Test journal IO error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"
            journal = JSONJournal(journal_path)

            # Add an entry first
            journal.append("test_event", {"data": "test"})

            # Make the file readonly to trigger IO error
            import os
            os.chmod(journal_path, 0o444)

            try:
                # This should handle the IO error gracefully
                journal.append("another_event", {"data": "test2"})
            except PermissionError:
                # Expected on Windows
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(journal_path, 0o644)

    def test_persistence_manager_integrity_check_failure(self):
        """Test persistence manager when integrity check fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = "sqlite:///:memory:"
            journal_path = Path(temp_dir) / "test_journal.jsonl"

            # Create a journal with tampered data
            with open(journal_path, 'w') as f:
                f.write('{"id":"test","timestamp":"2023-01-01T00:00:00Z","event_type":"test","event_data":{},"session_id":null,"hash_chain":"invalid_hash","previous_hash":null}\n')

            manager = PersistenceManager(database_url, journal_path)

            # Should raise RuntimeError due to integrity failure
            with pytest.raises(RuntimeError, match="Journal integrity verification failed"):
                manager.initialize()

    def test_database_session_error_handling(self):
        """Test database session error handling."""
        # Use invalid database URL to trigger connection error
        database_url = "sqlite:///invalid/path/that/does/not/exist/test.db"

        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"

            try:
                manager = PersistenceManager(database_url, journal_path)
                # This might fail, which is expected for invalid paths
            except Exception:
                # Expected for invalid database paths
                pass

    def test_journal_previous_hash_mismatch(self):
        """Test journal with previous hash mismatch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"
            journal = JSONJournal(journal_path)

            # Create entries manually with wrong previous hash
            entry1_data = {
                'id': 'test1',
                'timestamp': '2023-01-01T00:00:00Z',
                'event_type': 'test',
                'event_data': {},
                'session_id': None,
                'hash_chain': 'hash1',
                'previous_hash': None
            }

            entry2_data = {
                'id': 'test2',
                'timestamp': '2023-01-01T00:01:00Z',
                'event_type': 'test',
                'event_data': {},
                'session_id': None,
                'hash_chain': 'hash2',
                'previous_hash': 'wrong_hash'  # Wrong previous hash
            }

            with open(journal_path, 'w') as f:
                f.write(json.dumps(entry1_data) + '\n')
                f.write(json.dumps(entry2_data) + '\n')

            # Should fail verification due to hash mismatch
            assert not journal.verify_integrity()

    def test_structured_logger_edge_cases(self):
        """Test structured logger edge cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            journal_path = Path(temp_dir) / "test_journal.jsonl"
            journal = JSONJournal(journal_path)

            db_manager = Mock()
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_session)
            mock_context_manager.__exit__ = Mock(return_value=None)
            db_manager.get_session.return_value = mock_context_manager

            logger = StructuredLogger(journal, db_manager)

            # Test logging with None values
            logger.log_system_event("test_event", None)
            logger.log_risk_event("test_risk", {"data": None})

            # Verify entries were created
            entries = journal.read_entries()
            assert len(entries) >= 2


if __name__ == "__main__":
    pytest.main([__file__])
