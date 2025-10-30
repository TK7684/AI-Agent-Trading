# Project Structure

## Top-Level Organization

```
autonomous-trading-system/
├── apps/              # Application services
├── libs/              # Shared libraries
├── infra/             # Infrastructure as code
├── ops/               # Operations and runbooks
├── tests/             # Test suites
├── scripts/           # Deployment and utility scripts
├── monitoring/        # Monitoring configuration
├── nginx/             # Nginx proxy configuration
└── demo_*.py          # Demonstration scripts
```

## Applications (`apps/`)

### `execution-gateway/` (Rust)
High-performance order execution service with WebSocket support for real-time market data.

### `trading_api/` (Python)
FastAPI-based REST API for trading operations, market data, and system management.

### `trading-dashboard-ui-clean/` (React/TypeScript)
Modern trading dashboard with real-time charts, position management, and system monitoring.

## Shared Libraries (`libs/`)

### `trading_models/` (Python)
Core trading logic and models:
- `base.py`: Base Pydantic models with optimized computed fields
- `orchestrator.py`: Main trading orchestration engine
- `llm_integration.py`: Multi-LLM routing and integration
- `risk_management.py`: Position sizing and risk controls
- `pattern_recognition.py`: Technical pattern detection
- `technical_indicators.py`: Technical analysis calculations
- `market_data.py`: Market data ingestion and processing
- `paper_trading.py`: Simulation mode implementation
- `config_manager.py`: Configuration management with hot reloading
- `performance_monitoring.py`: Real-time performance tracking
- `monitoring.py`: System health and metrics
- `security.py`: Authentication and authorization
- `persistence.py`: Database operations

### `rust-common/` (Rust)
Shared Rust types and utilities for cross-service communication.

## Infrastructure (`infra/`)

- `helm/`: Kubernetes Helm charts
- `terraform/`: Infrastructure as code
- `prometheus/`: Prometheus configuration
- `loki/`: Loki log aggregation config
- `promtail/`: Promtail log shipping config

## Operations (`ops/`)

- `runbooks/`: Operational procedures and troubleshooting guides

## Testing (`tests/`)

Comprehensive test suite organized by feature:
- `test_*.py`: Unit and integration tests
- `conftest.py`: Pytest fixtures and configuration
- Property-based testing with Hypothesis
- Chaos testing for resilience validation
- Performance benchmarking

## Scripts (`scripts/`)

### PowerShell Scripts (Windows)
- `deploy-development.ps1`: Development environment deployment
- `deploy-production.ps1`: Production deployment
- `install-deps.ps1`: Dependency installation
- `validate-setup.ps1`: Setup validation
- `verify-rust-models.ps1`: Rust model verification

### Shell Scripts (Linux/macOS)
- `health-check.sh`: System health validation
- `smoke-tests.sh`: Basic functionality tests
- `install-deps.sh`: Dependency installation

### Python Scripts
- `validate_comprehensive_testing.py`: Test validation
- `validate_performance_thresholds.py`: Performance validation

## Configuration Files

### Root Level
- `pyproject.toml`: Python project configuration and dependencies
- `Cargo.toml`: Rust workspace configuration
- `docker-compose.yml`: Core services
- `docker-compose.dev.yml`: Development environment
- `docker-compose.trading-dashboard.yml`: Production dashboard
- `config.toml`: Trading system configuration
- `security_config.toml`: Security settings
- `.env.development`: Development environment variables
- `.env.production`: Production environment variables

### Build & CI/CD
- `Dockerfile`: Base Python image
- `Dockerfile.orchestrator`: Orchestrator service
- `Dockerfile.execution-gateway`: Rust execution service
- `Dockerfile.monitoring`: Monitoring service
- `.github/workflows/`: CI/CD pipelines

## Naming Conventions

### Python
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

### Rust
- **Modules**: `snake_case`
- **Structs/Enums**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### TypeScript/React
- **Components**: `PascalCase.tsx`
- **Utilities**: `camelCase.ts`
- **Hooks**: `useCamelCase.ts`
- **Types**: `PascalCase` interfaces/types

## File Organization Patterns

### Python Modules
Each module in `libs/trading_models/` is self-contained with:
- Type definitions using Pydantic models
- Business logic as functions or classes
- Async/await for I/O operations
- Comprehensive docstrings

### Rust Crates
Workspace members follow standard Cargo structure:
- `src/lib.rs` or `src/main.rs`
- `src/models/`: Data structures
- `src/services/`: Business logic
- `tests/`: Integration tests

### React Components
- `src/components/`: Reusable UI components
- `src/pages/`: Page-level components
- `src/hooks/`: Custom React hooks
- `src/stores/`: Zustand state stores
- `src/utils/`: Utility functions
- `src/types/`: TypeScript type definitions

## Data Flow

1. **Market Data**: External APIs → `market_data.py` → Redis cache → Orchestrator
2. **Analysis**: Orchestrator → LLM Router → Multiple LLM providers → Signal generation
3. **Risk Check**: Signals → `risk_management.py` → Approved/Rejected
4. **Execution**: Approved signals → Rust execution gateway → Exchange
5. **Monitoring**: All components → Prometheus → Grafana dashboards
6. **UI Updates**: Backend → WebSocket → React dashboard

## Key Directories to Know

- **Demo scripts**: Root-level `demo_*.py` files demonstrate system features
- **Validation results**: `validation_results/` contains test outputs and reports
- **Logs**: `logs/` (created at runtime) for application logs
- **Coverage**: `htmlcov/` for test coverage reports
- **Monitoring config**: `monitoring_config/` for alerts and dashboards
