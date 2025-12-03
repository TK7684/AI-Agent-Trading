# Local Development Guide

This guide provides comprehensive instructions for setting up and running the AI Trading System locally for development and testing purposes.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **Git**: Latest version
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: At least 10GB free space

### Required Tools

1. **Python Package Manager**: Poetry (recommended) or pip
2. **Database**: PostgreSQL 13+ (or use Docker)
3. **Redis**: 6.0+ (for caching and session storage)
4. **Docker & Docker Compose**: Optional, for containerized dependencies

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-username/ai-trading-system.git
cd ai-trading-system
```

### 2. Set Up Python Environment

#### Using Poetry (Recommended)

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

#### Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Database

#### Option 1: Local PostgreSQL

```bash
# Create database user and database
sudo -u postgres createuser --interactive
sudo -u postgres createdb trading_db

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading_db TO your_user;"
```

#### Option 2: Docker PostgreSQL

```bash
# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
EOF

# Start services
docker-compose up -d
```

### 4. Set Up Node.js Environment

```bash
# Install Node.js dependencies
npm install

# Install Vercel CLI
npm i -g vercel
```

### 5. Configure Environment

```bash
# Create environment file
cp .env.development .env.local

# Edit with your configuration
# Windows
notepad .env.local
# macOS/Linux
nano .env.local
```

Sample `.env.local`:
```env
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_db
REDIS_URL=redis://localhost:6379/0

# LLM API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Exchange API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# Market Data API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
COINGECKO_API_KEY=your_coingecko_api_key
```

## Running the Application

### 1. Initialize Database

```bash
# Run database migrations
python -m alembic upgrade head

# Load initial data
python scripts/load_initial_data.py
```

### 2. Start Development Server

```bash
# Option 1: Using Vercel CLI
npm run dev

# Option 2: Using Python
python api/index.py

# Option 3: Using FastAPI directly
uvicorn apps.trading-api.main:app --reload --host 0.0.0.0 --port 3000
```

### 3. Access the Application

- **API**: http://localhost:3000
- **Health Check**: http://localhost:3000/api/health
- **Documentation**: http://localhost:3000/docs

## Development Workflow

### 1. Code Structure

```
ai-trading-system/
├── api/                    # Vercel serverless functions
│   ├── index.py            # Main request router
│   ├── functions/          # API endpoints
│   │   ├── trading.py      # Trading operations
│   │   ├── training.py     # Model training
│   │   ├── strategies.py   # Strategy management
│   │   ├── market.py      # Market data
│   │   └── health.py      # Health checks
│   └── requirements.txt    # Python dependencies
├── apps/                  # Application services
│   ├── trading-api/       # Main trading API
│   └── execution-gateway/ # Order execution (Rust)
├── libs/                  # Shared libraries
│   ├── trading_models/     # Core trading logic
│   └── rust-common/       # Shared Rust code
├── scripts/               # Utility scripts
└── tests/                 # Test files
```

### 2. Making Changes

1. **Code Changes**:
   - Modify the relevant files
   - Run tests: `pytest`
   - Check formatting: `ruff check .`
   - Fix any issues

2. **Database Changes**:
   - Create migration: `alembic revision --autogenerate -m "description"`
   - Apply migration: `alembic upgrade head`

3. **API Changes**:
   - Update API documentation
   - Test endpoints manually
   - Run integration tests

### 3. Testing

#### Unit Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_trading_models.py

# Run with coverage
pytest --cov=apps --cov=libs --cov-report=html
```

#### Integration Tests

```bash
# Run integration tests
pytest -m integration

# Run specific integration test
pytest tests/test_integration.py -k test_trading_workflow
```

#### Performance Tests

```bash
# Run performance benchmarks
pytest --benchmark-only

# Profile specific functions
pytest --profile
```

### 4. Debugging

#### Python Debugging

```bash
# Run with Python debugger
python -m pdb api/index.py

# Or use VS Code debugger with launch configuration
```

#### API Debugging

```bash
# Use curl to test endpoints
curl -X GET http://localhost:3000/api/health

# Use verbose mode for debugging
curl -v -X POST http://localhost:3000/api/trading/trades \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001}'
```

## Common Development Tasks

### 1. Adding New API Endpoint

1. Create function in `api/functions/`
2. Implement `handler(request_context)` function
3. Add route in `api/index.py`
4. Write tests in `tests/`
5. Update documentation

### 2. Adding New Trading Model

1. Create model class in `libs/trading_models/`
2. Implement required methods
3. Add to database models
4. Create migration
5. Write tests

### 3. Adding New Strategy

1. Create strategy class in `libs/trading_models/strategies/`
2. Implement required methods
3. Add to strategy registry
4. Write tests
5. Update documentation

## Troubleshooting

### Database Issues

#### Connection Problems

```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection string
psql $DATABASE_URL
```

#### Migration Issues

```bash
# Check migration status
alembic current

# Force migration to specific version
alembic upgrade <version_id>

# Reset database (DESTRUCTIVE)
alembic downgrade base
alembic upgrade head
```

### API Issues

#### Server Not Starting

```bash
# Check port usage
lsof -i :3000

# Kill process using port
kill -9 <PID>
```

#### Request Failures

```bash
# Check logs
tail -f logs/api.log

# Check environment variables
printenv | grep DATABASE_URL
```

### Performance Issues

#### Slow API Response

1. Check database queries
2. Add indexes to slow queries
3. Implement caching
4. Profile with Python profiler

#### Memory Usage

1. Monitor with `htop` or Task Manager
2. Check for memory leaks
3. Optimize data structures

## Advanced Configuration

### 1. Customizing LLM Models

Edit `.env.local`:
```env
# LLM Configuration
DEFAULT_LLM_MODEL=claude-3-sonnet
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30
```

### 2. Customizing Trading Parameters

Edit configuration file:
```toml
# config/trading.toml
[trading]
symbols = ["BTCUSDT", "ETHUSDT"]
timeframes = ["15m", "1h", "4h", "1d"]
max_concurrent_trades = 5
max_position_size = 0.1
default_stop_loss = 0.02
default_take_profit = 0.05
```

### 3. Customizing Risk Management

Edit configuration file:
```toml
# config/risk.toml
[risk_management]
max_daily_loss = 0.05
max_open_positions = 10
max_risk_per_trade = 0.02
required_win_rate = 0.6
```

## Deployment Preparation

### 1. Pre-deployment Checklist

- [ ] All tests passing
- [ ] Code formatted and linted
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Security checks passed
- [ ] Performance benchmarks acceptable

### 2. Local Testing

```bash
# Run full test suite
pytest

# Run integration tests
pytest -m integration

# Run performance tests
pytest --benchmark-only

# Run security tests
bandit -r libs/
```

### 3. Environment Validation

```bash
# Validate environment
python scripts/validate_environment.py

# Check API keys
python scripts/check_api_keys.py

# Verify database connection
python scripts/test_database.py
```

## Resources

### Documentation

- [API Documentation](http://localhost:3000/docs)
- [Model Documentation](./docs/models.md)
- [Strategy Guide](./docs/strategies.md)
- [LLM Integration](./docs/llm_integration.md)

### Tools

- [Poetry Documentation](https://python-poetry.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vercel CLI Documentation](https://vercel.com/docs/cli)
- [pytest Documentation](https://docs.pytest.org/)

### Community

- [GitHub Issues](https://github.com/your-username/ai-trading-system/issues)
- [Discord Community](https://discord.gg/your-invite)
- [Discussions](https://github.com/your-username/ai-trading-system/discussions)

## Conclusion

This local development guide provides everything you need to set up and work with the AI Trading System locally. By following these instructions, you can develop, test, and debug the system in a controlled environment before deploying to production.

For additional support or questions, refer to the project documentation or reach out to the development team through the provided channels.