"""Initial database schema for trading system

Revision ID: 001
Revises:
Create Date: 2025-09-08 13:56:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trades table
    op.create_table('trades',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('pattern', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('fees', sa.Float(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('timeframe', sa.String(length=10), nullable=True),
        sa.Column('entry_reason', sa.Text(), nullable=True),
        sa.Column('exit_reason', sa.Text(), nullable=True),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trades_pnl', 'trades', ['pnl'], unique=False)
    op.create_index('idx_trades_status_timestamp', 'trades', ['status', 'timestamp'], unique=False)
    op.create_index('idx_trades_symbol_timestamp', 'trades', ['symbol', 'timestamp'], unique=False)
    op.create_index(op.f('ix_trades_status'), 'trades', ['status'], unique=False)
    op.create_index(op.f('ix_trades_symbol'), 'trades', ['symbol'], unique=False)

    # Create system_metrics table
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cpu_usage', sa.Float(), nullable=False),
        sa.Column('memory_usage', sa.Float(), nullable=False),
        sa.Column('disk_usage', sa.Float(), nullable=False),
        sa.Column('network_latency', sa.Float(), nullable=False),
        sa.Column('error_rate', sa.Float(), nullable=False),
        sa.Column('active_connections', sa.Integer(), nullable=False),
        sa.Column('requests_per_minute', sa.Integer(), nullable=False),
        sa.Column('active_positions', sa.Integer(), nullable=False),
        sa.Column('daily_trades', sa.Integer(), nullable=False),
        sa.Column('daily_pnl', sa.Float(), nullable=False),
        sa.Column('portfolio_value', sa.Float(), nullable=False),
        sa.Column('database_healthy', sa.Boolean(), nullable=False),
        sa.Column('broker_healthy', sa.Boolean(), nullable=False),
        sa.Column('llm_healthy', sa.Boolean(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_system_metrics_timestamp', 'system_metrics', ['timestamp'], unique=False)
    op.create_index(op.f('ix_system_metrics_timestamp'), 'system_metrics', ['timestamp'], unique=False)

    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=False),
        sa.Column('persistent', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_read_timestamp', 'notifications', ['read', 'timestamp'], unique=False)
    op.create_index('idx_notifications_type_timestamp', 'notifications', ['type', 'timestamp'], unique=False)
    op.create_index(op.f('ix_notifications_read'), 'notifications', ['read'], unique=False)
    op.create_index(op.f('ix_notifications_timestamp'), 'notifications', ['timestamp'], unique=False)
    op.create_index(op.f('ix_notifications_type'), 'notifications', ['type'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # Create trading_sessions table
    op.create_table('trading_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('symbols', sa.JSON(), nullable=True),
        sa.Column('timeframes', sa.JSON(), nullable=True),
        sa.Column('strategy_config', sa.JSON(), nullable=True),
        sa.Column('risk_config', sa.JSON(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('total_pnl', sa.Float(), nullable=False),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('agent_version', sa.String(length=20), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trading_sessions_start_time', 'trading_sessions', ['start_time'], unique=False)
    op.create_index('idx_trading_sessions_status', 'trading_sessions', ['status'], unique=False)

    # Create performance_snapshots table
    op.create_table('performance_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_pnl', sa.Float(), nullable=False),
        sa.Column('daily_pnl', sa.Float(), nullable=False),
        sa.Column('portfolio_value', sa.Float(), nullable=False),
        sa.Column('daily_change_percent', sa.Float(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('current_drawdown', sa.Float(), nullable=False),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('active_positions', sa.Integer(), nullable=False),
        sa.Column('total_exposure', sa.Float(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['trading_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_performance_snapshots_timestamp', 'performance_snapshots', ['timestamp'], unique=False)
    op.create_index(op.f('ix_performance_snapshots_timestamp'), 'performance_snapshots', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_performance_snapshots_timestamp'), table_name='performance_snapshots')
    op.drop_index('idx_performance_snapshots_timestamp', table_name='performance_snapshots')
    op.drop_table('performance_snapshots')
    op.drop_index('idx_trading_sessions_status', table_name='trading_sessions')
    op.drop_index('idx_trading_sessions_start_time', table_name='trading_sessions')
    op.drop_table('trading_sessions')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_type'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_timestamp'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_read'), table_name='notifications')
    op.drop_index('idx_notifications_type_timestamp', table_name='notifications')
    op.drop_index('idx_notifications_read_timestamp', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_system_metrics_timestamp'), table_name='system_metrics')
    op.drop_index('idx_system_metrics_timestamp', table_name='system_metrics')
    op.drop_table('system_metrics')
    op.drop_index(op.f('ix_trades_symbol'), table_name='trades')
    op.drop_index(op.f('ix_trades_status'), table_name='trades')
    op.drop_index('idx_trades_symbol_timestamp', table_name='trades')
    op.drop_index('idx_trades_status_timestamp', table_name='trades')
    op.drop_index('idx_trades_pnl', table_name='trades')
    op.drop_table('trades')
