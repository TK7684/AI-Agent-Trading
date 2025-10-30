# SQLAlchemy Persistence Layer

This document describes the SQLAlchemy-based data persistence layer implemented for the trading dashboard API.

## Overview

The persistence layer provides comprehensive data storage and retrieval capabilities for:
- Trading records (trades, positions, performance)
- System metrics and health monitoring
- Notifications and alerts
- Trading sessions and performance snapshots

## Architecture

### Database Models

#### TradeModel
Stores individual trading records with comprehensive metadata:
- Basic trade info (symbol, side, prices, quantity, P&L)
- Trading strategy information (pattern, confidence, strategy)
- Risk management (stop loss, take profit)
- Timing and duration tracking
- Entry/exit reasons

#### SystemMetricModel
Captures system performance and health metrics:
- System resources (CPU, memory, disk, network)
- Trading system metrics (active positions, daily P&L)
- Service health indicators
- Performance tracking

#### NotificationModel
Manages alerts and notifications:
- Categorized notifications (info, warning, error, success)
- Read/unread status tracking
- Persistent vs temporary notifications
- Rich metadata and context

#### TradingSessionModel
Tracks trading sessions and agent activity:
- Session configuration and parameters
- Performance statistics per session
- Agent version tracking

#### PerformanceSnapshotModel
Periodic performance snapshots for historical analysis:
- Portfolio metrics over time
- Risk metrics (drawdown, ratios)
- Trading statistics

### Data Access Layer

#### TradingDataAccess
- `create_trade()` - Create new trade records
- `update_trade()` - Update existing trades
- `get_trades()` - Query trades with filtering
- `get_trade_statistics()` - Aggregate trading statistics

#### SystemMetricsDataAccess
- `record_metrics()` - Store system metrics
- `get_recent_metrics()` - Retrieve recent metrics
- `get_metrics_summary()` - Aggregate metrics analysis

#### NotificationDataAccess
- `create_notification()` - Create new notifications
- `get_notifications()` - Query notifications with filtering
- `mark_as_read()` - Update notification status
- `get_unread_count()` - Count unread notifications

### Service Layer

#### PersistenceService
High-level service providing:
- Unified interface to all data operations
- Business logic for complex operations
- Data migration and cleanup utilities
- Performance optimization

## Database Configuration

### Supported Databases
- **PostgreSQL** (recommended for production)
- **SQLite** (development/testing)

### Environment Variables
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trading_db
# or for SQLite:
DATABASE_URL=sqlite+aiosqlite:///./trading.db
```

### Migration Management
Uses Alembic for database schema migrations:
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## API Integration

### Updated Endpoints

#### Trading Endpoints
- `GET /trading/performance` - Real-time performance from database
- `GET /trading/trades` - Paginated trades with advanced filtering
- `POST /trading/trades` - Create new trade records
- `POST /trading/trades/{id}/close` - Close existing trades

#### System Endpoints
- `GET /system/metrics` - Historical system metrics
- `GET /system/health` - Current system health from database
- `GET /system/notifications` - Paginated notifications

#### Admin Endpoints
- `POST /admin/database/migrate` - Migrate in-memory data
- `POST /admin/database/cleanup` - Clean old records
- `GET /admin/database/stats` - Database statistics

### Real-time Updates
WebSocket broadcasts are maintained for:
- Trade events (open/close)
- Performance updates
- System metrics
- Notifications

## Performance Features

### Indexing Strategy
- Optimized indexes for common queries
- Composite indexes for filtering operations
- Time-based indexes for historical data

### Query Optimization
- Efficient pagination with offset/limit
- Selective field loading
- Aggregate queries for statistics

### Data Lifecycle Management
- Automatic cleanup of old metrics
- Configurable data retention policies
- Background maintenance tasks

## Usage Examples

### Creating a Trade
```python
trade = await persistence_service.create_trade(
    symbol="BTCUSDT",
    side="LONG",
    entry_price=45000.0,
    quantity=0.1,
    confidence=0.85,
    pattern="breakout"
)
```

### Closing a Trade
```python
closed_trade = await persistence_service.close_trade(
    trade_id=trade.id,
    exit_price=45500.0,
    exit_reason="Take profit"
)
```

### Recording System Metrics
```python
metrics = await persistence_service.record_system_metrics(
    cpu_usage=25.5,
    memory_usage=60.2,
    disk_usage=45.0,
    network_latency=50.0
)
```

### Creating Notifications
```python
notification = await persistence_service.create_notification(
    notification_type="warning",
    title="High Drawdown Alert",
    message="Portfolio drawdown exceeded 10%",
    severity="high"
)
```

### Querying Data
```python
# Get recent trades with filtering
trades, total, has_next = await persistence_service.get_trades_paginated(
    page=1,
    page_size=20,
    symbol="BTCUSDT",
    status="CLOSED",
    profit_loss_filter="profit"
)

# Get performance metrics
performance = await persistence_service.get_trading_performance()

# Get system health
health = await persistence_service.get_system_health_summary()
```

## Testing

Run the test script to verify functionality:
```bash
cd apps/trading-api
python test_persistence.py
```

## Migration from In-Memory Storage

The persistence layer includes utilities to migrate existing in-memory data:

1. **Automatic Migration**: On startup, the system checks for existing database data
2. **Manual Migration**: Use the `/admin/database/migrate` endpoint
3. **Data Validation**: Ensures data integrity during migration

## Monitoring and Maintenance

### Health Checks
- Database connection monitoring
- Query performance tracking
- Error rate monitoring

### Maintenance Tasks
- Automatic old data cleanup
- Index optimization
- Performance monitoring

### Backup Recommendations
- Regular database backups
- Point-in-time recovery setup
- Disaster recovery procedures

## Security Considerations

### Data Protection
- Sensitive data handling
- SQL injection prevention
- Connection security

### Access Control
- Authentication required for all operations
- Admin-only endpoints for maintenance
- Rate limiting on all endpoints

## Future Enhancements

### Planned Features
- Advanced analytics queries
- Data export/import utilities
- Performance optimization tools
- Multi-tenant support

### Scalability Considerations
- Connection pooling optimization
- Read replica support
- Horizontal scaling strategies
- Caching layer integration

## Troubleshooting

### Common Issues
1. **Connection Errors**: Check DATABASE_URL configuration
2. **Migration Failures**: Verify database permissions
3. **Performance Issues**: Check index usage and query patterns
4. **Data Inconsistency**: Run data validation utilities

### Debug Mode
Enable SQL logging by setting `echo=True` in database engine configuration.

### Support
For issues or questions about the persistence layer, check:
1. Application logs for error details
2. Database logs for connection issues
3. Performance metrics for bottlenecks
4. Test script results for functionality verification