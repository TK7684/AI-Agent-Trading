"""
Database migration and backup system for the autonomous trading system.

This module provides database migration management using Alembic and
backup/restore functionality for data protection.
"""

import gzip
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import structlog
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from .persistence import PersistenceManager

logger = structlog.get_logger(__name__)


class MigrationManager:
    """Manages database migrations using Alembic."""

    def __init__(self, database_url: str, migrations_dir: Optional[Path] = None):
        self.database_url = database_url
        self.migrations_dir = migrations_dir or Path("migrations")
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Create alembic.ini if it doesn't exist
        self.alembic_ini_path = self.migrations_dir / "alembic.ini"
        self._create_alembic_config()

        self.alembic_cfg = Config(str(self.alembic_ini_path))
        self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    def _create_alembic_config(self):
        """Create alembic.ini configuration file."""
        if self.alembic_ini_path.exists():
            return

        alembic_ini_content = f"""# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = {self.migrations_dir}

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# file_template = %%Y%%m%%d_%%H%%M_%%%(rev)s_%%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version number format
version_num_format = %04d

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = {self.database_url}


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

        with open(self.alembic_ini_path, 'w') as f:
            f.write(alembic_ini_content)

    def initialize_migrations(self):
        """Initialize Alembic migrations directory."""
        try:
            command.init(self.alembic_cfg, str(self.migrations_dir))
            logger.info("Initialized Alembic migrations directory")
        except Exception as e:
            if "already exists" in str(e):
                logger.info("Migrations directory already exists")
            else:
                logger.error("Failed to initialize migrations", error=str(e))
                raise

    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration."""
        try:
            revision = command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=autogenerate
            )
            logger.info("Created migration", revision=revision.revision, message=message)
            return revision.revision
        except Exception as e:
            logger.error("Failed to create migration", error=str(e))
            raise

    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to specified revision."""
        try:
            command.upgrade(self.alembic_cfg, revision)
            logger.info("Database upgraded", revision=revision)
        except Exception as e:
            logger.error("Failed to upgrade database", error=str(e))
            raise

    def downgrade(self, revision: str) -> None:
        """Downgrade database to specified revision."""
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info("Database downgraded", revision=revision)
        except Exception as e:
            logger.error("Failed to downgrade database", error=str(e))
            raise

    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error("Failed to get current revision", error=str(e))
            return None

    def get_migration_history(self) -> list[dict[str, Any]]:
        """Get migration history."""
        try:
            script = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []

            for revision in script.walk_revisions():
                revisions.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'branch_labels': revision.branch_labels,
                    'depends_on': revision.depends_on,
                    'doc': revision.doc,
                    'module': revision.module
                })

            return revisions
        except Exception as e:
            logger.error("Failed to get migration history", error=str(e))
            return []

    def check_migration_status(self) -> dict[str, Any]:
        """Check migration status."""
        current_revision = self.get_current_revision()
        history = self.get_migration_history()

        return {
            'current_revision': current_revision,
            'total_migrations': len(history),
            'pending_migrations': [
                rev for rev in history
                if rev['revision'] != current_revision
            ][:5]  # Show first 5 pending
        }


class BackupManager:
    """Manages database and journal backups."""

    def __init__(self, database_url: str, journal_path: Path, backup_dir: Path):
        self.database_url = database_url
        self.journal_path = Path(journal_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a full backup of database and journal."""
        if backup_name is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"

        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        try:
            # Backup database
            self._backup_database(backup_path / "database.sql.gz")

            # Backup journal
            if self.journal_path.exists():
                self._backup_journal(backup_path / "journal.json.gz")

            # Create backup metadata
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.now(UTC).isoformat(),
                'database_url': self.database_url.split('@')[-1],  # Remove credentials
                'journal_path': str(self.journal_path),
                'backup_type': 'full'
            }

            with open(backup_path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info("Backup created successfully", backup_path=str(backup_path))
            return backup_path

        except Exception as e:
            logger.error("Failed to create backup", error=str(e))
            # Cleanup partial backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise

    def _backup_database(self, output_path: Path):
        """Backup database to compressed SQL file."""
        # Extract database connection details
        if self.database_url.startswith('postgresql://'):
            self._backup_postgresql(output_path)
        elif self.database_url.startswith('sqlite://'):
            self._backup_sqlite(output_path)
        else:
            raise ValueError(f"Unsupported database type: {self.database_url}")

    def _backup_postgresql(self, output_path: Path):
        """Backup PostgreSQL database."""
        try:
            # Use pg_dump to create backup
            cmd = [
                'pg_dump',
                self.database_url,
                '--no-password',
                '--verbose'
            ]

            with gzip.open(output_path, 'wt') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {result.stderr}")

        except FileNotFoundError:
            logger.warning("pg_dump not found, using SQLAlchemy backup")
            self._backup_with_sqlalchemy(output_path)

    def _backup_sqlite(self, output_path: Path):
        """Backup SQLite database."""
        db_path = self.database_url.replace('sqlite:///', '')
        if Path(db_path).exists():
            with open(db_path, 'rb') as src, gzip.open(output_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        else:
            logger.warning("SQLite database file not found", path=db_path)

    def _backup_with_sqlalchemy(self, output_path: Path):
        """Backup using SQLAlchemy (fallback method)."""
        engine = create_engine(self.database_url)

        with gzip.open(output_path, 'wt') as f:
            with engine.connect() as connection:
                # Get all table names
                result = connection.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))

                tables = [row[0] for row in result]

                for table in tables:
                    f.write(f"-- Table: {table}\n")
                    result = connection.execute(text(f"SELECT * FROM {table}"))

                    for row in result:
                        # Simple INSERT statement generation
                        columns = list(row.keys())
                        values = [repr(val) for val in row]
                        f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")

    def _backup_journal(self, output_path: Path):
        """Backup journal file."""
        with open(self.journal_path, 'rb') as src, gzip.open(output_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)

    def restore_backup(self, backup_path: Path) -> None:
        """Restore from backup."""
        backup_path = Path(backup_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Read metadata
        metadata_path = backup_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            logger.info("Restoring backup", metadata=metadata)

        try:
            # Restore database
            db_backup_path = backup_path / "database.sql.gz"
            if db_backup_path.exists():
                self._restore_database(db_backup_path)

            # Restore journal
            journal_backup_path = backup_path / "journal.json.gz"
            if journal_backup_path.exists():
                self._restore_journal(journal_backup_path)

            logger.info("Backup restored successfully")

        except Exception as e:
            logger.error("Failed to restore backup", error=str(e))
            raise

    def _restore_database(self, backup_path: Path):
        """Restore database from backup."""
        if self.database_url.startswith('postgresql://'):
            self._restore_postgresql(backup_path)
        elif self.database_url.startswith('sqlite://'):
            self._restore_sqlite(backup_path)
        else:
            raise ValueError(f"Unsupported database type: {self.database_url}")

    def _restore_postgresql(self, backup_path: Path):
        """Restore PostgreSQL database."""
        try:
            cmd = [
                'psql',
                self.database_url,
                '--no-password',
                '--quiet'
            ]

            with gzip.open(backup_path, 'rt') as f:
                result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"psql restore failed: {result.stderr}")

        except FileNotFoundError:
            logger.warning("psql not found, manual restore required")
            raise

    def _restore_sqlite(self, backup_path: Path):
        """Restore SQLite database."""
        db_path = self.database_url.replace('sqlite:///', '')

        # Backup existing database
        if Path(db_path).exists():
            backup_existing = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_existing)

        # Restore from backup
        with gzip.open(backup_path, 'rb') as src, open(db_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)

    def _restore_journal(self, backup_path: Path):
        """Restore journal from backup."""
        # Backup existing journal
        if self.journal_path.exists():
            backup_existing = f"{self.journal_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.journal_path, backup_existing)

        # Restore from backup
        with gzip.open(backup_path, 'rb') as src, open(self.journal_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)

    def list_backups(self) -> list[dict[str, Any]]:
        """List available backups."""
        backups = []

        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_path = backup_dir / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                        metadata['path'] = str(backup_dir)
                        backups.append(metadata)
                    except (OSError, json.JSONDecodeError):
                        logger.warning("Invalid backup metadata", path=str(backup_dir))

        return sorted(backups, key=lambda x: x.get('created_at', ''), reverse=True)

    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Remove old backups, keeping only the specified number."""
        backups = self.list_backups()

        if len(backups) <= keep_count:
            return

        backups_to_remove = backups[keep_count:]

        for backup in backups_to_remove:
            backup_path = Path(backup['path'])
            try:
                shutil.rmtree(backup_path)
                logger.info("Removed old backup", path=str(backup_path))
            except Exception as e:
                logger.error("Failed to remove backup", path=str(backup_path), error=str(e))


class DataReplaySystem:
    """System for replaying trading data for debugging and analysis."""

    def __init__(self, persistence_manager: PersistenceManager):
        self.persistence_manager = persistence_manager

    def replay_trading_session(self, session_id: str,
                             output_path: Optional[Path] = None) -> dict[str, Any]:
        """Replay a complete trading session."""
        # Get journal entries for the session
        journal_entries = self.persistence_manager.journal.read_entries()
        session_entries = [
            entry for entry in journal_entries
            if entry.session_id == session_id
        ]

        if not session_entries:
            raise ValueError(f"No entries found for session: {session_id}")

        # Sort by timestamp
        session_entries.sort(key=lambda x: x.timestamp)

        replay_data = {
            'session_id': session_id,
            'start_time': session_entries[0].timestamp.isoformat(),
            'end_time': session_entries[-1].timestamp.isoformat(),
            'total_events': len(session_entries),
            'events': []
        }

        for entry in session_entries:
            event_data = {
                'timestamp': entry.timestamp.isoformat(),
                'event_type': entry.event_type,
                'event_data': entry.event_data
            }
            replay_data['events'].append(event_data)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(replay_data, f, indent=2)

        return replay_data

    def analyze_decision_chain(self, decision_id: str) -> dict[str, Any]:
        """Analyze the complete decision chain for a specific trading decision."""
        journal_entries = self.persistence_manager.journal.read_entries()

        # Find the decision entry
        decision_entry = None
        for entry in journal_entries:
            if (entry.event_type == 'trading_decision' and
                entry.event_data.get('decision_id') == decision_id):
                decision_entry = entry
                break

        if not decision_entry:
            raise ValueError(f"Decision not found: {decision_id}")

        # Find related execution results
        execution_entries = [
            entry for entry in journal_entries
            if (entry.event_type == 'execution_result' and
                entry.timestamp >= decision_entry.timestamp and
                entry.timestamp <= decision_entry.timestamp.replace(hour=23, minute=59, second=59))
        ]

        analysis = {
            'decision_id': decision_id,
            'decision_timestamp': decision_entry.timestamp.isoformat(),
            'decision_context': decision_entry.event_data.get('decision_context', {}),
            'order_decision': decision_entry.event_data.get('order_decision', {}),
            'execution_results': [
                {
                    'timestamp': entry.timestamp.isoformat(),
                    'execution_result': entry.event_data.get('execution_result', {})
                }
                for entry in execution_entries
            ]
        }

        return analysis

    def generate_performance_report(self, start_time: datetime,
                                  end_time: datetime) -> dict[str, Any]:
        """Generate a comprehensive performance report for a time period."""
        # Get trades in the period
        trades = self.persistence_manager.get_trades(
            start_time=start_time,
            end_time=end_time
        )

        # Get journal entries
        journal_entries = self.persistence_manager.journal.read_entries(
            start_time=start_time,
            end_time=end_time
        )

        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])

        total_pnl = sum(t.pnl for t in trades if t.pnl)
        total_fees = sum(t.fees for t in trades)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # Event type distribution
        event_types = {}
        for entry in journal_entries:
            event_types[entry.event_type] = event_types.get(entry.event_type, 0) + 1

        report = {
            'period': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            },
            'trading_metrics': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'net_pnl': total_pnl - total_fees
            },
            'system_metrics': {
                'total_events': len(journal_entries),
                'event_type_distribution': event_types
            },
            'trades': [trade.model_dump() for trade in trades]
        }

        return report
