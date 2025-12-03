# Automated Trading System

A comprehensive, production-ready automated trading system with database integration, adaptive learning, and real-time monitoring capabilities. This system provides end-to-end automation for cryptocurrency trading with intelligent strategy optimization and risk management.

## 🚀 Key Features

### Core Trading Engine
- **Automated Trade Execution**: Real-time market analysis and order placement
- **Multi-Strategy Support**: Run multiple trading strategies simultaneously
- **Risk Management**: Comprehensive position sizing, stop-loss, and drawdown controls
- **Multi-Asset Trading**: Support for BTC, ETH, and additional cryptocurrencies

### Database Integration
- **Trade History**: Complete audit trail of all trades with detailed metadata
- **Performance Analytics**: Real-time calculation of win rates, profit factors, and Sharpe ratios
- **Learning Data Storage**: Storage of learning outcomes and strategy adaptations
- **System Metrics**: Comprehensive monitoring of system health and resource usage

### Adaptive Learning
- **Multi-Armed Bandit**: Automatic strategy selection and optimization
- **Pattern Recognition**: Machine learning-based pattern identification
- **Strategy Evolution**: Continuous improvement based on performance feedback
- **Parameter Tuning**: Automatic adjustment of strategy parameters

### Real-Time Monitoring
- **Performance Dashboard**: Live trading metrics and system health
- **Alert System**: Configurable alerts for critical events
- **Resource Monitoring**: CPU, memory, disk, and network tracking
- **Error Handling**: Comprehensive error detection and recovery

## 📁 Project Structure

```
auto_trading_system/
├── core/
│   └── live_trading_engine.py     # Main trading engine with automation
├── database/
│   ├── trade_repository.py         # Trade database operations
│   └── performance_repository.py   # Performance metrics storage
├── learning/
│   └── adaptive_strategy.py       # ML-based strategy optimization
├── monitoring/
│   └── performance_monitor.py     # Real-time monitoring and alerts
├── config/
│   └── automated_trading_config.py # Comprehensive configuration
├── start_automated_trading.py      # Main launcher
└── README.md                      # This documentation
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Redis (for caching)
- Sufficient system resources (min 8GB RAM, 4 CPU cores)

### Database Setup

1. **Install PostgreSQL**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   
   # Windows
   # Download from https://www.postgresql.org/download/windows/
   ```

2. **Create Database**
   ```sql
   CREATE DATABASE trading_db;
   CREATE USER trading_user WITH PASSWORD 'trading_pass';
   GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
   ```

3. **Install Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   
   # Windows
   # Download from https://redis.io/download
   ```

### Python Dependencies

```bash
cd "AI Agent Trading"
pip install -e .
```

### Configuration

1. **Copy and edit configuration**
   ```bash
   cp auto_trading_system/config/automated_trading_config.py my_config.py
   # Edit my_config.py with your settings
   ```

2. **Set environment variables**
   ```bash
   export DATABASE_URL="postgresql+asyncpg://trading_user:trading_pass@localhost:5432/trading_db"
   export REDIS_URL="redis://localhost:6379/0"
   export OPENAI_API_KEY="your-openai-key"
   export ANTHROPIC_API_KEY="your-anthropic-key"
   ```

## 🚀 Quick Start

### 1. Start the Automated Trading System

```bash
# Live trading (real money)
python auto_trading_system/start_automated_trading.py

# Simulation mode (no real trades)
python auto_trading_system/start_automated_trading.py --demo

# Dry run mode (simulate but don't execute)
python auto_trading_system/start_automated_trading.py --dry-run
```

### 2. Monitor the System

The system provides real-time monitoring through:
- Console output with performance metrics
- Database logs accessible via SQL
- Performance reports generated every hour
- Alert notifications for critical events

### 3. View Results

Access trading results through:
- PostgreSQL database queries
- Performance reports in logs
- Dashboard (if enabled in config)

## 📊 System Components

### Live Trading Engine (`core/live_trading_engine.py`)

The heart of the system that:
- Fetches real-time market data
- Generates trading signals using AI
- Applies adaptive learning adjustments
- Executes trades with risk management
- Monitors and manages positions

**Key Classes:**
- `LiveTradingEngine`: Main orchestrator
- `TradeSignal`: Trading signal data structure
- `Position`: Active position management

### Database Integration (`database/`)

**Trade Repository (`trade_repository.py`)**
- Stores all trade records with full metadata
- Provides performance analytics
- Supports complex queries for strategy analysis

**Performance Repository (`performance_repository.py`)**
- Stores system performance metrics
- Manages learning results
- Tracks system health over time

### Adaptive Learning (`learning/adaptive_strategy.py`)

Machine learning system that:
- Registers and manages multiple strategies
- Performs real-time strategy optimization
- Adapts to changing market conditions
- Provides intelligent position management

**Key Features:**
- Multi-armed bandit algorithms (UCB1, epsilon-greedy)
- Random forest-based optimization
- Market condition assessment
- Adaptive parameter tuning

### Performance Monitoring (`monitoring/performance_monitor.py`)

Comprehensive monitoring system with:
- Real-time metrics collection
- Configurable alert thresholds
- Performance reporting
- System health tracking

**Metrics Tracked:**
- System: CPU, memory, disk, network
- Trading: Win rate, P&L, drawdown, positions
- Learning: Accuracy, convergence, adaptations

## ⚙️ Configuration

### Trading Configuration

```python
# Key settings to configure
trading:
  symbols: ["BTCUSDT", "ETHUSDT"]           # Trading pairs
  account_balance: 10000.0                  # Starting capital
  max_risk_per_trade: 0.02                 # 2% risk per trade
  max_drawdown_pct: 10.0                   # Max 10% drawdown
  min_confidence: 0.6                      # Min confidence for trades
  max_concurrent_positions: 10             # Max open positions
```

### Database Configuration

```python
database:
  host: "localhost"
  port: 5432
  database: "trading_db"
  username: "trading_user"
  password: "trading_pass"
  max_connections: 20
  backup_enabled: True
  data_retention_days: 90
```

### Learning Configuration

```python
learning:
  cycle_interval_trades: 50                # Learn every 50 trades
  adaptation_threshold: 0.05               # Adapt on 5% performance drop
  optimization_enabled: True                # Enable auto-optimization
  bandit_algorithm: "ucb1"                 # Strategy selection algorithm
```

### Monitoring Configuration

```python
monitoring:
  collection_interval_seconds: 30           # Collect metrics every 30s
  cpu_threshold: 80.0                      # Alert at 80% CPU
  drawdown_alert_threshold: 8.0             # Alert at 8% drawdown
  alert_enabled: True                      # Enable alerts
  daily_report_enabled: True               # Generate daily reports
```

## 📈 Performance Optimization

### System Tuning

1. **Database Optimization**
   ```sql
   -- Indexes for performance
   CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp);
   CREATE INDEX idx_trades_status ON trades(status);
   CREATE INDEX idx_performance_timestamp ON performance_metrics(timestamp);
   ```

2. **Connection Pooling**
   ```python
   # Optimize database connections
   max_connections = max_concurrent_positions + 10
   connection_timeout = 30
   ```

3. **Memory Management**
   ```python
   # Limit history size
   max_history_size = 1000
   cleanup_old_data_enabled = True
   ```

### Trading Optimization

1. **Strategy Selection**
   - Use UCB1 for balanced exploration/exploitation
   - Start with multiple strategies
   - Let the system learn which perform best

2. **Risk Management**
   - Never risk more than 2% per trade
   - Use position sizing based on volatility
   - Implement correlation limits

3. **Performance Targets**
   - Aim for 65%+ win rate
   - Target 1.5+ profit factor
   - Keep drawdown under 10%

## 🔍 Monitoring & Debugging

### Performance Reports

The system generates comprehensive reports:

```
📊 24-Hour Performance Report:
==================================================
System:
   Avg CPU: 45.2%
   Avg Memory: 62.1%
   Uptime: 24.0h

Trading:
   Total Trades: 156
   Win Rate: 68.5%
   Daily P&L: $1,234.56
   Max Drawdown: 3.2%

Learning:
   Learning Cycles: 12
   Accuracy Improvement: 0.045
   Profit Improvement: 0.067
==================================================
```

### Debugging Tools

1. **Enable Debug Mode**
   ```python
   # In configuration
   debug_mode: True
   log_level: "DEBUG"
   ```

2. **Check Database**
   ```sql
   -- Recent trades
   SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;
   
   -- Performance metrics
   SELECT * FROM performance_metrics ORDER BY timestamp DESC LIMIT 10;
   ```

3. **Monitor Logs**
   ```bash
   tail -f automated_trading.log
   ```

### Common Issues

**High CPU Usage**
- Check if too many strategies are running
- Verify database indexes are created
- Reduce monitoring collection frequency

**Low Win Rate**
- Verify minimum confidence threshold
- Check if market conditions changed
- Consider strategy re-optimization

**Database Connection Issues**
- Verify PostgreSQL is running
- Check connection parameters
- Ensure sufficient max_connections

## 🛡️ Security & Safety

### Trading Safety Features

1. **Risk Controls**
   - Maximum position size limits
   - Daily loss limits
   - Correlation exposure limits
   - Emergency stop functionality

2. **Position Management**
   - Automatic stop-loss placement
   - Take-profit targets
   - Position timeout limits
   - Profit protection mechanisms

3. **System Safeguards**
   - Resource usage monitoring
   - Error detection and recovery
   - Graceful shutdown procedures
   - Data backup and recovery

### Security Best Practices

1. **API Key Management**
   - Use encrypted key storage
   - Rotate keys regularly
   - Implement rate limiting
   - Monitor for unauthorized access

2. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Implement user access controls
   - Regular security updates

3. **Network Security**
   - Use secure connections
   - Implement IP whitelisting
   - Monitor for suspicious activity
   - Regular security audits

## 📝 Advanced Usage

### Custom Strategy Development

1. **Create Strategy Class**
   ```python
   class MyCustomStrategy:
       def __init__(self, config):
           self.config = config
       
       def generate_signal(self, market_data):
           # Your custom logic
           return signal
   ```

2. **Register Strategy**
   ```python
   await adaptive_manager.register_strategy(
       "MyStrategy",
       parameters,
       initial_performance
   )
   ```

### Database Analysis

1. **Performance Analytics**
   ```sql
   -- Strategy performance
   SELECT strategy, 
          COUNT(*) as trades,
          AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_rate,
          SUM(pnl) as total_pnl
   FROM trades 
   GROUP BY strategy;
   
   -- Pattern analysis
   SELECT pattern,
          COUNT(*) as occurrences,
          AVG(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as success_rate
   FROM trades
   WHERE pattern IS NOT NULL
   GROUP BY pattern
   ORDER BY success_rate DESC;
   ```

2. **Learning Optimization**
   ```sql
   -- Learning effectiveness
   SELECT DATE_TRUNC('day', timestamp) as day,
          COUNT(*) as learning_cycles,
          AVG(accuracy_improvement) as avg_accuracy_imp
   FROM learning_results
   GROUP BY day
   ORDER BY day DESC;
   ```

### API Integration

1. **External APIs**
   - Integrate with exchange APIs for live trading
   - Use market data providers for real-time feeds
   - Implement webhook notifications for alerts

2. **Custom Indicators**
   - Add technical analysis libraries
   - Implement custom signal processing
   - Integrate with external analytics

## 🚀 Production Deployment

### System Requirements

**Minimum:**
- 8GB RAM
- 4 CPU cores
- 100GB storage
- Stable internet connection

**Recommended:**
- 16GB RAM
- 8 CPU cores
- 500GB SSD storage
- Redundant internet connections

### Deployment Steps

1. **Server Setup**
   ```bash
   # Ubuntu server setup
   sudo apt-get update
   sudo apt-get install postgresql redis-server python3.11
   ```

2. **Application Deployment**
   ```bash
   # Clone and setup
   git clone <repository>
   cd "AI Agent Trading"
   pip install -e .
   
   # Setup systemd service
   sudo cp scripts/automated-trading.service /etc/systemd/system/
   sudo systemctl enable automated-trading
   sudo systemctl start automated-trading
   ```

3. **Monitoring Setup**
   ```bash
   # Setup log rotation
   sudo cp scripts/logrotate.conf /etc/logrotate.d/automated-trading
   
   # Setup monitoring
   # Configure monitoring tools (Prometheus, Grafana, etc.)
   ```

### Maintenance

1. **Regular Tasks**
   - Database backups
   - Log file management
   - Performance reviews
   - Strategy optimization

2. **Monitoring**
   - System health checks
   - Performance metrics
   - Error tracking
   - Security audits

## 📚 Reference Documentation

### Database Schema

**Trades Table**
```sql
CREATE TABLE trades (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE,
    symbol VARCHAR(20),
    side VARCHAR(10),
    entry_price FLOAT,
    exit_price FLOAT,
    quantity FLOAT,
    pnl FLOAT,
    status VARCHAR(20),
    pattern VARCHAR(50),
    confidence FLOAT,
    strategy VARCHAR(50),
    timeframe VARCHAR(10),
    risk_reward_ratio FLOAT
);
```

**Performance Metrics Table**
```sql
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE,
    daily_pnl FLOAT,
    total_trades INTEGER,
    winning_trades INTEGER,
    win_rate FLOAT,
    max_drawdown FLOAT,
    sharpe_ratio FLOAT,
    cpu_usage FLOAT,
    memory_usage FLOAT
);
```

### Configuration Reference

Full configuration options are available in `automated_trading_config.py`. Key sections include:
- `TradingConfig`: Trading parameters and risk limits
- `DatabaseConfig`: Database connection and performance settings
- `LearningConfig`: Machine learning and adaptation settings
- `MonitoringConfig`: Alerting and monitoring configuration
- `SecurityConfig`: Security and safety settings

### API Reference

The system exposes several interfaces:
- **Trading API**: Order placement and position management
- **Database API**: Trade history and analytics
- **Learning API**: Strategy management and optimization
- **Monitoring API**: Real-time metrics and health checks

## 🤝 Contributing

We welcome contributions! Key areas for improvement:
1. **Additional Exchanges**: Support for more trading platforms
2. **Advanced Strategies**: New trading algorithms and indicators
3. **Enhanced Analytics**: More sophisticated performance metrics
4. **UI Development**: Web dashboard and visualization tools
5. **Documentation**: Improve documentation and examples

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check this documentation thoroughly
2. Review the debug logs for specific error messages
3. Examine the database for performance insights
4. Test with demo mode before live trading
5. Monitor system resources during operation

## ⚠️ Disclaimer

**IMPORTANT WARNING**: This is an automated trading system that involves real financial risk. Before using with real money:

1. **Thoroughly test** in simulation mode
2. **Start with small amounts** you can afford to lose
3. **Monitor closely** during initial deployment
4. **Understand the risks** of automated trading
5. **Ensure adequate safeguards** are in place
6. **Review all configurations** before going live
7. **Have emergency stop procedures** ready

The authors are not responsible for any financial losses incurred while using this system. Use at your own risk and ensure you understand all implications before deploying with real capital.