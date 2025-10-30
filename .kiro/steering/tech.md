# Technology Stack

## Languages & Runtimes

- **Python 3.11+**: Core trading logic, orchestration, and LLM integration
- **Rust 1.78+**: High-performance execution gateway and shared libraries
- **TypeScript/React**: Trading dashboard UI
- **Node.js**: Frontend build tooling

## Build Systems & Package Managers

- **Poetry**: Python dependency management and packaging
- **Cargo**: Rust build system and package manager
- **npm/Vite**: Frontend build and development server

## Core Frameworks & Libraries

### Python Stack
- **FastAPI**: REST API framework with async support
- **Pydantic v2**: Data validation and settings management
- **SQLAlchemy 2.0**: Database ORM with async support
- **Pandas/NumPy**: Data analysis and numerical computing
- **HTTPX**: Async HTTP client
- **WebSockets**: Real-time communication

### Rust Stack
- **Tokio**: Async runtime
- **Serde**: Serialization/deserialization
- **SQLx**: Async database driver
- **Reqwest**: HTTP client with rustls-tls

### Frontend Stack
- **React 18**: UI framework
- **Zustand**: State management
- **React Router**: Client-side routing
- **Lightweight Charts**: TradingView-style charting
- **Vite**: Build tool and dev server
- **Vitest**: Testing framework

## Infrastructure

- **PostgreSQL 15**: Primary database
- **Redis 7**: Caching and real-time data
- **Docker/Docker Compose**: Containerization
- **Nginx**: Reverse proxy and static file serving
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **Loki/Promtail**: Log aggregation

## Development Tools

### Code Quality
- **Ruff**: Python linting and formatting (replaces Black, isort, flake8)
- **MyPy**: Python static type checking
- **Rustfmt**: Rust code formatting
- **Clippy**: Rust linting
- **ESLint**: TypeScript/React linting
- **Prettier**: Frontend code formatting

### Testing
- **pytest**: Python testing with async support
- **pytest-cov**: Code coverage reporting
- **Hypothesis**: Property-based testing
- **Vitest**: Frontend unit and integration testing
- **Testing Library**: React component testing

### Security
- **Bandit**: Python security linting
- **Safety**: Python dependency vulnerability scanning
- **Cargo Audit**: Rust dependency security auditing
- **Pre-commit**: Git hooks for automated checks
- **detect-secrets**: Secret scanning

## Common Commands

### Python Development
```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest
poetry run pytest --cov  # with coverage

# Linting and formatting
poetry run ruff check .
poetry run ruff format .
poetry run mypy .

# Security checks
poetry run bandit -r apps libs
poetry run safety check
```

### Rust Development
```bash
# Build
cargo build
cargo build --release

# Test
cargo test --workspace

# Linting and formatting
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings

# Security audit
cargo audit
```

### Frontend Development
```bash
# Development server (in apps/trading-dashboard-ui-clean)
npm run dev

# Build
npm run build

# Test
npm run test
npm run test:coverage

# Linting and formatting
npm run lint
npm run format
```

### Docker Operations
```bash
# Development environment
docker-compose -f docker-compose.dev.yml up -d

# Production environment
docker-compose -f docker-compose.trading-dashboard.yml up -d

# View logs
docker-compose logs -f [service]

# Rebuild
docker-compose build --no-cache
```

### Makefile Targets
```bash
make install      # Install all dependencies
make test         # Run all tests
make lint         # Run all linters
make format       # Format all code
make security     # Run security scans
make build        # Build all components
make clean        # Clean build artifacts
make dev-setup    # Complete development setup
```

## Configuration

- **Python**: `pyproject.toml` for dependencies and tool configuration
- **Rust**: `Cargo.toml` workspace configuration
- **Frontend**: `package.json` and `vite.config.ts`
- **Docker**: Multiple compose files for different environments
- **Environment**: `.env.development` and `.env.production` files
- **Trading Config**: `config.toml` for system configuration

## Performance Optimizations

- Async/await throughout Python codebase
- Connection pooling for database and HTTP
- Multi-level caching with TTL and LRU eviction
- Data compression for network and storage
- Memory leak detection and monitoring
- Function-level performance profiling
