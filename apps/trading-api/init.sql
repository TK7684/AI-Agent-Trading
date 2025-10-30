-- Trading Dashboard Database Initialization Script
-- This script sets up the initial database structure for the trading dashboard

-- Create database if it doesn't exist (for development)
-- Note: This is handled by Docker environment variables in production

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default schema
SET search_path TO trading, public;

-- Create enum types
CREATE TYPE trade_status AS ENUM ('OPEN', 'CLOSED', 'CANCELLED');
CREATE TYPE trade_side AS ENUM ('LONG', 'SHORT');
CREATE TYPE notification_type AS ENUM ('info', 'warning', 'error', 'success');

-- Create tables
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side trade_side NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    quantity DECIMAL(20, 8) NOT NULL,
    pnl DECIMAL(20, 8),
    status trade_status NOT NULL DEFAULT 'OPEN',
    pattern VARCHAR(50),
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    fees DECIMAL(20, 8),
    duration INTEGER, -- in seconds
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cpu_usage DECIMAL(5, 2) NOT NULL,
    memory_usage DECIMAL(5, 2) NOT NULL,
    disk_usage DECIMAL(5, 2) NOT NULL,
    network_latency DECIMAL(10, 2) NOT NULL,
    error_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
    active_connections INTEGER NOT NULL DEFAULT 0,
    requests_per_minute INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type notification_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read BOOLEAN NOT NULL DEFAULT FALSE,
    persistent BOOLEAN NOT NULL DEFAULT FALSE,
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trading_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    total_trades INTEGER NOT NULL DEFAULT 0,
    total_pnl DECIMAL(20, 8) NOT NULL DEFAULT 0,
    win_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
    max_drawdown DECIMAL(20, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);
CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl);
CREATE INDEX IF NOT EXISTS idx_trades_confidence ON trades(confidence);

CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_sessions_updated_at BEFORE UPDATE ON trading_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW active_trades AS
SELECT * FROM trades WHERE status = 'OPEN';

CREATE OR REPLACE VIEW recent_trades AS
SELECT * FROM trades 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

CREATE OR REPLACE VIEW trading_performance AS
SELECT 
    COUNT(*) as total_trades,
    COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
    COUNT(*) FILTER (WHERE pnl < 0) as losing_trades,
    COALESCE(SUM(pnl), 0) as total_pnl,
    COALESCE(SUM(pnl) FILTER (WHERE timestamp >= CURRENT_DATE), 0) as daily_pnl,
    CASE 
        WHEN COUNT(*) > 0 THEN 
            ROUND((COUNT(*) FILTER (WHERE pnl > 0)::DECIMAL / COUNT(*)) * 100, 2)
        ELSE 0 
    END as win_rate,
    COALESCE(MAX(pnl), 0) as max_win,
    COALESCE(MIN(pnl), 0) as max_loss
FROM trades 
WHERE status = 'CLOSED';

-- Create function to calculate portfolio value (mock implementation)
CREATE OR REPLACE FUNCTION get_portfolio_value()
RETURNS DECIMAL(20, 8) AS $$
BEGIN
    -- This is a simplified calculation
    -- In a real system, this would calculate based on current positions and market prices
    RETURN (
        SELECT COALESCE(SUM(pnl), 0) + 100000 -- Starting with 100k base
        FROM trades 
        WHERE status = 'CLOSED'
    );
END;
$$ LANGUAGE plpgsql;

-- Insert initial data for development/testing
INSERT INTO trading_sessions (id, start_time, total_trades, total_pnl, win_rate)
VALUES (uuid_generate_v4(), NOW() - INTERVAL '1 day', 0, 0, 0)
ON CONFLICT DO NOTHING;

-- Create user for application (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trading_app') THEN
        CREATE ROLE trading_app WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA trading TO trading_app;
GRANT USAGE ON SCHEMA monitoring TO trading_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO trading_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA monitoring TO trading_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trading TO trading_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA monitoring TO trading_app;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA trading GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO trading_app;

-- Create monitoring views
CREATE OR REPLACE VIEW system_health_summary AS
SELECT 
    AVG(cpu_usage) as avg_cpu,
    AVG(memory_usage) as avg_memory,
    AVG(disk_usage) as avg_disk,
    AVG(network_latency) as avg_latency,
    AVG(error_rate) as avg_error_rate,
    MAX(timestamp) as last_update
FROM system_metrics 
WHERE timestamp >= NOW() - INTERVAL '1 hour';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Trading Dashboard database initialized successfully!';
    RAISE NOTICE 'Database: %', current_database();
    RAISE NOTICE 'Schema: %', current_schema();
    RAISE NOTICE 'Timestamp: %', NOW();
END
$$;