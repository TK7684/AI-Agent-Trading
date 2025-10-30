# Design Document

## Overview

This design document outlines the architecture for running the Autonomous Trading System without Docker containerization. The solution provides native Windows execution for all components while maintaining the same functionality, performance, and reliability as the Docker-based deployment. The design focuses on simplicity, developer experience, and production-ready native service management.

### Goals

- **Zero Docker Dependency**: Complete removal of Docker/Docker Compose requirements
- **Native Performance**: Leverage native Windows execution for optimal performance
- **Simple Installation**: One-command setup for all dependencies
- **Developer-Friendly**: Fast iteration with hot reload and native debugging
- **Production-Ready**: Robust process management and monitoring
- **Backward Compatible**: Maintain all existing features and APIs

### Non-Goals

- Cross-platform deployment (focus on Windows optimization)
- Kubernetes or container orchestration
- Distributed multi-node deployment
- Legacy Windows version support (Windows 10+ only)

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Native Windows Services                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │    Redis     │  │  Prometheus  │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  │ (Port 5432)  │  │ (Port 6379)  │  │ (Port 9090)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                   Application Layer                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Python Orchestrator (Poetry)                  │   │
│  │         - Trading logic & LLM integration            │   │
│  │         - Risk management & pattern recognition      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Trading API (FastAPI/Uvicorn)                │   │
│  │         - REST endpoints (Port 8000)                 │   │
│  │         - WebSocket support                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Execution Gateway (Rust Native)              │   │
│  │         - High-performance order execution           │   │
│  │         - WebSocket market data (Port 3000)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Trading Dashboard (Vite Dev Server)          │   │
│  │         - React UI with HMR (Port 5173)              │   │
│  │         - TradingView charts                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```


### Service Dependencies

```
PostgreSQL (Native Service)
    ↓
Redis (Native Service)
    ↓
Trading API (Python/Uvicorn) ← Orchestrator (Python)
    ↓
Execution Gateway (Rust)
    ↓
Trading Dashboard (Vite)
    ↓
Prometheus (Optional Monitoring)
```

### Process Management Strategy

The system uses a PowerShell-based process manager that:
- Starts services in dependency order
- Monitors process health with heartbeats
- Provides graceful shutdown
- Aggregates logs from all services
- Supports selective service restart

## Components and Interfaces

### 1. Native Service Installer

**Purpose**: Automated installation and configuration of PostgreSQL, Redis, and optional monitoring tools.

**Implementation**:
- PowerShell script: `scripts/install-native-services.ps1`
- Chocolatey package manager for Windows
- Automated service configuration
- Database initialization scripts

**Key Functions**:
```powershell
Install-PostgreSQL
    - Downloads PostgreSQL 15 via Chocolatey
    - Configures Windows Service
    - Creates trading database and user
    - Sets up connection pooling

Install-Redis
    - Downloads Redis via Chocolatey or MSI
    - Configures Windows Service
    - Sets memory limits and persistence
    - Enables AOF for durability

Install-Monitoring (Optional)
    - Installs Prometheus as Windows Service
    - Installs Grafana as Windows Service
    - Provisions dashboards and data sources
```

**Configuration Files**:
- `config/postgres-native.conf`: PostgreSQL tuning for trading workload
- `config/redis-native.conf`: Redis configuration with persistence
- `config/prometheus-native.yml`: Metrics scraping configuration

### 2. Process Manager

**Purpose**: Orchestrate startup, monitoring, and shutdown of all application services.

**Implementation**:
- PowerShell module: `scripts/ProcessManager.psm1`
- JSON configuration: `config/services.json`
- Log aggregation to `logs/` directory

**Service Configuration Schema**:
```json
{
  "services": [
    {
      "name": "trading-api",
      "command": "poetry run uvicorn apps.trading_api.main:app",
      "args": ["--host", "0.0.0.0", "--port", "8000", "--reload"],
      "workingDirectory": ".",
      "env": {
        "DATABASE_URL": "postgresql://trading:password@localhost:5432/trading",
        "REDIS_URL": "redis://localhost:6379/0"
      },
      "dependsOn": ["postgres", "redis"],
      "healthCheck": {
        "url": "http://localhost:8000/health",
        "interval": 10,
        "timeout": 5
      }
    }
  ]
}
```


**Process Manager API**:
```powershell
# Start all services
Start-TradingSystem [-Services <string[]>] [-SkipHealthCheck]

# Stop all services
Stop-TradingSystem [-Graceful] [-Timeout <int>]

# Restart specific service
Restart-TradingService -Name <string>

# Get service status
Get-TradingSystemStatus [-Detailed]

# View aggregated logs
Get-TradingSystemLogs [-Service <string>] [-Follow] [-Tail <int>]
```

### 3. Configuration Management

**Purpose**: Unified configuration system that works without Docker environment injection.

**Implementation**:
- Python: `python-dotenv` for .env file loading
- Node.js: `dotenv` package for frontend
- Rust: `dotenvy` crate for execution gateway
- Centralized: `config.toml` for shared settings

**Configuration Hierarchy**:
1. `config.toml` - Base configuration
2. `.env` - Environment-specific overrides
3. `.env.local` - Local developer overrides (gitignored)
4. Environment variables - Runtime overrides

**Example .env for Native Deployment**:
```bash
# Database (localhost instead of Docker service name)
DATABASE_URL=postgresql://trading:secure_password@localhost:5432/trading
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading
POSTGRES_USER=trading
POSTGRES_PASSWORD=secure_password

# Redis (localhost instead of Docker service name)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Frontend Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000

# Monitoring (optional)
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3001

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=./logs
```

### 4. Database Management

**Purpose**: Handle PostgreSQL schema initialization, migrations, and maintenance.

**Implementation**:
- Alembic for schema migrations
- PowerShell scripts for database operations
- Automated initialization on first run

**Database Scripts**:
```powershell
# Initialize database
Initialize-TradingDatabase
    - Creates database if not exists
    - Creates trading user with permissions
    - Runs initial schema migration
    - Seeds reference data

# Run migrations
Update-TradingDatabase [-Target <version>]
    - Checks current schema version
    - Applies pending migrations
    - Validates schema integrity

# Backup database
Backup-TradingDatabase [-OutputPath <path>]
    - Creates pg_dump backup
    - Compresses with gzip
    - Stores with timestamp

# Reset database (development only)
Reset-TradingDatabase [-Force]
    - Drops all tables
    - Reruns migrations
    - Reseeds data
```

**Migration Strategy**:
- Alembic migrations in `alembic/versions/`
- Automatic migration on service start
- Rollback support for failed migrations
- Schema validation before startup


### 5. Python Application Layer

**Purpose**: Run orchestrator and trading API as native Python processes with hot reload.

**Implementation**:
- Poetry for dependency management
- Uvicorn with --reload for development
- Watchdog for file monitoring
- Structured logging to files

**Service Definitions**:

**Trading API**:
```powershell
# Development mode
poetry run uvicorn apps.trading_api.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --reload `
    --reload-dir apps/trading_api `
    --reload-dir libs/trading_models `
    --log-config logging.yaml

# Production mode
poetry run uvicorn apps.trading_api.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --workers 4 `
    --log-config logging.yaml
```

**Orchestrator**:
```powershell
# Run as background process
poetry run python -m libs.trading_models.orchestrator `
    --config config.toml `
    --log-level INFO
```

**Hot Reload Configuration**:
- Watch directories: `apps/`, `libs/`
- Ignore patterns: `*.pyc`, `__pycache__`, `.pytest_cache`
- Reload delay: 1 second
- Graceful restart on file changes

### 6. Rust Execution Gateway

**Purpose**: High-performance native Windows executable for order execution.

**Implementation**:
- Cargo build system
- Native Windows executable
- Direct PostgreSQL connection via SQLx
- WebSocket server for market data

**Build Process**:
```powershell
# Development build
cargo build --package execution-gateway

# Production build (optimized)
cargo build --package execution-gateway --release

# Run executable
.\target\release\execution-gateway.exe `
    --config config.toml `
    --port 3000
```

**Configuration Loading**:
```rust
// Load from .env file
dotenvy::dotenv().ok();

// Load from config.toml
let config = Config::builder()
    .add_source(config::File::with_name("config"))
    .add_source(config::Environment::with_prefix("TRADING"))
    .build()?;

// Database connection
let database_url = env::var("DATABASE_URL")?;
let pool = PgPoolOptions::new()
    .max_connections(10)
    .connect(&database_url)
    .await?;
```

**Performance Optimizations**:
- Link-time optimization (LTO) enabled
- CPU-specific optimizations
- Static linking for portability
- Memory-mapped I/O for logs

### 7. React Dashboard

**Purpose**: Native Vite development server with instant HMR.

**Implementation**:
- Vite dev server on port 5173
- Proxy configuration for API calls
- Environment variable injection
- Production build to static files

**Development Server**:
```powershell
# Start dev server
cd apps/trading-dashboard-ui-clean
npm run dev

# Vite configuration (vite.config.ts)
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

**Production Build**:
```powershell
# Build static files
npm run build

# Output: dist/ directory with optimized assets
# Serve with any static file server
```

**Static File Serving Options**:
1. Python HTTP server: `python -m http.server 8080 -d dist`
2. Node.js serve: `npx serve dist -p 8080`
3. Nginx: Configure as static file server
4. FastAPI: Mount as static files in trading API


### 8. Monitoring Stack

**Purpose**: Optional native Prometheus and Grafana for system monitoring.

**Implementation**:
- Prometheus as Windows Service
- Grafana as Windows Service
- Automatic dashboard provisioning
- Metrics exporters in each service

**Prometheus Configuration**:
```yaml
# prometheus-native.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'execution-gateway'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']  # postgres_exporter

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']  # redis_exporter
```

**Grafana Provisioning**:
```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
```

## Data Models

### Service Configuration Model

```typescript
interface ServiceConfig {
  name: string;
  command: string;
  args: string[];
  workingDirectory: string;
  env: Record<string, string>;
  dependsOn: string[];
  healthCheck?: {
    url: string;
    interval: number;
    timeout: number;
    retries: number;
  };
  restart?: {
    enabled: boolean;
    maxRetries: number;
    backoffSeconds: number;
  };
}

interface SystemConfig {
  services: ServiceConfig[];
  logging: {
    directory: string;
    level: string;
    rotation: {
      maxSize: string;
      maxAge: number;
      maxBackups: number;
    };
  };
}
```

### Process State Model

```typescript
interface ProcessState {
  name: string;
  pid: number | null;
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'failed';
  startTime: Date | null;
  restartCount: number;
  lastError: string | null;
  healthStatus: 'healthy' | 'unhealthy' | 'unknown';
  lastHealthCheck: Date | null;
}
```

## Error Handling

### Service Startup Failures

**Scenario**: PostgreSQL fails to start

**Handling**:
1. Check if port 5432 is already in use
2. Verify PostgreSQL service is installed
3. Check Windows Event Log for service errors
4. Provide actionable error message with fix suggestions
5. Offer to retry with different port

**Example Error Message**:
```
❌ PostgreSQL failed to start
   Reason: Port 5432 is already in use
   
   Possible solutions:
   1. Stop existing PostgreSQL instance: net stop postgresql-x64-15
   2. Change port in .env: POSTGRES_PORT=5433
   3. Kill process using port: Get-Process -Id (Get-NetTCPConnection -LocalPort 5432).OwningProcess | Stop-Process
   
   Run: .\scripts\diagnose-postgres.ps1 for detailed analysis
```

### Dependency Resolution Failures

**Scenario**: Trading API starts before PostgreSQL is ready

**Handling**:
1. Implement exponential backoff retry logic
2. Maximum 30 second wait for dependencies
3. Health check polling every 2 seconds
4. Clear progress indication during wait
5. Fail fast with clear error if timeout exceeded

**Implementation**:
```powershell
function Wait-ForService {
    param(
        [string]$ServiceName,
        [string]$HealthCheckUrl,
        [int]$TimeoutSeconds = 30
    )
    
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $HealthCheckUrl -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Write-Host "." -NoNewline
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    
    throw "Service $ServiceName failed to become healthy within $TimeoutSeconds seconds"
}
```


### Configuration Errors

**Scenario**: Invalid DATABASE_URL in .env file

**Handling**:
1. Validate configuration on startup
2. Check connection before starting services
3. Provide specific error about what's wrong
4. Suggest correct format with example

**Validation Function**:
```python
def validate_database_url(url: str) -> tuple[bool, str]:
    """Validate PostgreSQL connection URL."""
    pattern = r'^postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)$'
    match = re.match(pattern, url)
    
    if not match:
        return False, (
            "Invalid DATABASE_URL format. "
            "Expected: postgresql://user:password@host:port/database\n"
            "Example: postgresql://trading:password@localhost:5432/trading"
        )
    
    user, password, host, port, database = match.groups()
    
    # Test connection
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        conn.close()
        return True, "Database connection successful"
    except psycopg2.OperationalError as e:
        return False, f"Cannot connect to database: {e}"
```

### Process Crash Recovery

**Scenario**: Trading API crashes during operation

**Handling**:
1. Detect process exit via monitoring
2. Log crash details and stack trace
3. Attempt automatic restart (max 3 times)
4. Exponential backoff between restarts
5. Alert user if restart limit exceeded

**Recovery Logic**:
```powershell
function Monitor-Process {
    param(
        [System.Diagnostics.Process]$Process,
        [ServiceConfig]$Config
    )
    
    $restartCount = 0
    $maxRestarts = 3
    
    while ($true) {
        $Process.WaitForExit()
        
        $exitCode = $Process.ExitCode
        Write-Log "Process $($Config.name) exited with code $exitCode"
        
        if ($restartCount -ge $maxRestarts) {
            Write-Error "Process $($Config.name) exceeded restart limit"
            Send-Alert -Service $Config.name -Message "Service failed after $maxRestarts restart attempts"
            break
        }
        
        $backoffSeconds = [Math]::Pow(2, $restartCount)
        Write-Log "Restarting $($Config.name) in $backoffSeconds seconds..."
        Start-Sleep -Seconds $backoffSeconds
        
        $Process = Start-ServiceProcess -Config $Config
        $restartCount++
    }
}
```

## Testing Strategy

### Unit Testing

**Scope**: Individual components and functions

**Tools**:
- Python: pytest with pytest-asyncio
- Rust: cargo test
- TypeScript: Vitest

**Key Test Areas**:
- Configuration loading and validation
- Process management functions
- Health check logic
- Error handling and recovery
- Database connection pooling

**Example Test**:
```python
@pytest.mark.asyncio
async def test_service_health_check():
    """Test health check endpoint responds correctly."""
    config = ServiceConfig(
        name="test-api",
        health_check=HealthCheck(
            url="http://localhost:8000/health",
            interval=10,
            timeout=5
        )
    )
    
    # Mock HTTP response
    with aioresponses() as m:
        m.get("http://localhost:8000/health", status=200)
        
        result = await check_service_health(config)
        assert result.is_healthy
        assert result.response_time < 1.0
```

### Integration Testing

**Scope**: Service interactions and data flow

**Test Scenarios**:
1. **Database Connection**: Verify all services can connect to PostgreSQL
2. **Redis Caching**: Test cache operations from Python and Rust
3. **API Communication**: Frontend → API → Database flow
4. **WebSocket Streaming**: Real-time data from execution gateway
5. **Configuration Loading**: All services read correct config

**Example Integration Test**:
```python
@pytest.mark.integration
async def test_end_to_end_trade_flow():
    """Test complete trade flow from API to database."""
    # Start services
    await start_test_services()
    
    try:
        # Submit trade via API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/trades",
                json={"symbol": "BTCUSDT", "quantity": 0.1}
            )
            assert response.status_code == 201
            trade_id = response.json()["id"]
        
        # Verify in database
        async with get_db_connection() as conn:
            trade = await conn.fetchrow(
                "SELECT * FROM trades WHERE id = $1", trade_id
            )
            assert trade is not None
            assert trade["symbol"] == "BTCUSDT"
        
        # Verify in Redis cache
        redis_client = await get_redis_client()
        cached_trade = await redis_client.get(f"trade:{trade_id}")
        assert cached_trade is not None
    
    finally:
        await stop_test_services()
```


### Performance Testing

**Scope**: Verify native deployment meets performance targets

**Benchmarks**:
- API response time: < 100ms (p95)
- Database query time: < 50ms (p95)
- WebSocket latency: < 10ms
- Memory usage: < 2GB per service
- CPU usage: < 50% under normal load

**Performance Test Suite**:
```python
@pytest.mark.performance
def test_api_response_time(benchmark):
    """Benchmark API endpoint response time."""
    def make_request():
        response = requests.get("http://localhost:8000/api/health")
        return response.json()
    
    result = benchmark(make_request)
    assert benchmark.stats.stats.mean < 0.1  # 100ms
```

**Load Testing**:
```powershell
# Use Apache Bench for load testing
ab -n 10000 -c 100 http://localhost:8000/api/health

# Expected results:
# - Requests per second: > 1000
# - Mean response time: < 100ms
# - Failed requests: 0
```

### System Testing

**Scope**: Complete system behavior and reliability

**Test Scenarios**:
1. **Cold Start**: System starts from completely stopped state
2. **Graceful Shutdown**: All services stop cleanly
3. **Service Recovery**: Services restart after crash
4. **Configuration Reload**: Changes applied without restart
5. **Database Migration**: Schema updates applied correctly
6. **Log Rotation**: Logs rotate without data loss

**Automated System Test**:
```powershell
# scripts/test-system.ps1
function Test-TradingSystem {
    Write-Host "🧪 Running system tests..."
    
    # Test 1: Cold start
    Write-Host "Test 1: Cold start"
    Stop-TradingSystem -Force
    $startResult = Start-TradingSystem -Timeout 60
    Assert-True $startResult.Success
    
    # Test 2: Health checks
    Write-Host "Test 2: Health checks"
    $health = Get-TradingSystemStatus -Detailed
    Assert-AllServicesHealthy $health
    
    # Test 3: API functionality
    Write-Host "Test 3: API functionality"
    $response = Invoke-RestMethod "http://localhost:8000/api/health"
    Assert-Equal $response.status "healthy"
    
    # Test 4: Database connectivity
    Write-Host "Test 4: Database connectivity"
    $dbTest = Test-DatabaseConnection
    Assert-True $dbTest.Connected
    
    # Test 5: Graceful shutdown
    Write-Host "Test 5: Graceful shutdown"
    $stopResult = Stop-TradingSystem -Graceful -Timeout 30
    Assert-True $stopResult.Success
    
    Write-Host "✅ All system tests passed"
}
```

## Deployment Strategy

### Development Environment Setup

**One-Command Installation**:
```powershell
# scripts/setup-native-dev.ps1
.\scripts\setup-native-dev.ps1

# This script will:
# 1. Check prerequisites (Python, Node.js, Rust, Chocolatey)
# 2. Install PostgreSQL and Redis
# 3. Install Poetry and npm dependencies
# 4. Build Rust components
# 5. Initialize database
# 6. Create .env.local from template
# 7. Run health checks
# 8. Start all services
```

**Manual Setup Steps** (if needed):
```powershell
# 1. Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Install services
choco install postgresql15 redis-64 -y

# 3. Install Python dependencies
poetry install

# 4. Install Node.js dependencies
cd apps/trading-dashboard-ui-clean
npm install
cd ../..

# 5. Build Rust components
cargo build --release

# 6. Initialize database
.\scripts\init-database.ps1

# 7. Start system
.\scripts\start-trading-system.ps1
```

### Production Deployment

**Production Setup**:
```powershell
# 1. Clone repository
git clone <repo-url>
cd autonomous-trading-system

# 2. Run production setup
.\scripts\setup-native-prod.ps1

# This script will:
# - Install services with production configuration
# - Set up Windows Services for auto-start
# - Configure firewall rules
# - Set up log rotation
# - Configure monitoring
# - Run security hardening
# - Create backup schedules
```

**Windows Service Registration**:
```powershell
# Register Trading API as Windows Service
New-Service -Name "TradingAPI" `
    -BinaryPathName "C:\Python311\python.exe -m uvicorn apps.trading_api.main:app --host 0.0.0.0 --port 8000" `
    -DisplayName "Trading API Service" `
    -Description "Autonomous Trading System API" `
    -StartupType Automatic `
    -Credential (Get-Credential)

# Register Execution Gateway as Windows Service
New-Service -Name "ExecutionGateway" `
    -BinaryPathName "C:\trading\target\release\execution-gateway.exe" `
    -DisplayName "Execution Gateway Service" `
    -Description "High-performance order execution gateway" `
    -StartupType Automatic
```


### Migration from Docker

**Migration Script**:
```powershell
# scripts/migrate-from-docker.ps1
function Migrate-FromDocker {
    Write-Host "🔄 Migrating from Docker to native deployment..."
    
    # 1. Export data from Docker containers
    Write-Host "Step 1: Exporting data from Docker..."
    docker-compose exec postgres pg_dump -U trading trading > backup.sql
    
    # 2. Stop Docker containers
    Write-Host "Step 2: Stopping Docker containers..."
    docker-compose down
    
    # 3. Install native services
    Write-Host "Step 3: Installing native services..."
    .\scripts\install-native-services.ps1
    
    # 4. Import data to native PostgreSQL
    Write-Host "Step 4: Importing data..."
    psql -U trading -d trading -f backup.sql
    
    # 5. Update configuration
    Write-Host "Step 5: Updating configuration..."
    Update-ConfigForNative
    
    # 6. Start native services
    Write-Host "Step 6: Starting native services..."
    Start-TradingSystem
    
    # 7. Verify migration
    Write-Host "Step 7: Verifying migration..."
    Test-MigrationSuccess
    
    Write-Host "✅ Migration complete!"
}
```

## Performance Optimizations

### Native Execution Benefits

**Expected Performance Improvements**:
- **Startup Time**: 60% faster (no container initialization)
- **Memory Usage**: 30% reduction (no container overhead)
- **I/O Performance**: 20% faster (direct filesystem access)
- **Network Latency**: 15% reduction (no Docker networking)
- **Build Time**: 50% faster (no image building)

### Windows-Specific Optimizations

**1. Process Priority**:
```powershell
# Set high priority for critical services
$process = Get-Process -Name "execution-gateway"
$process.PriorityClass = "High"
```

**2. CPU Affinity**:
```powershell
# Pin execution gateway to specific CPU cores
$process = Get-Process -Name "execution-gateway"
$process.ProcessorAffinity = 0x0F  # Cores 0-3
```

**3. Memory Management**:
```powershell
# Increase working set for database
$process = Get-Process -Name "postgres"
$process.MinWorkingSet = 512MB
$process.MaxWorkingSet = 2GB
```

**4. Disk I/O**:
```powershell
# Enable write caching for database drive
fsutil behavior set disablelastaccess 1
fsutil behavior set encryptpagingfile 0
```

### Database Tuning

**PostgreSQL Configuration** (`postgres-native.conf`):
```ini
# Memory settings
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
work_mem = 32MB

# Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# Query planner
random_page_cost = 1.1  # SSD optimization
effective_io_concurrency = 200

# Connections
max_connections = 100
```

**Redis Configuration** (`redis-native.conf`):
```ini
# Memory
maxmemory 1gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

## Security Considerations

### Service Isolation

**Windows User Accounts**:
```powershell
# Create dedicated service account
New-LocalUser -Name "TradingService" `
    -Description "Trading System Service Account" `
    -NoPassword

# Grant minimal permissions
$acl = Get-Acl "C:\trading"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "TradingService", "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl "C:\trading" $acl
```

### Network Security

**Firewall Rules**:
```powershell
# Allow only localhost connections to database
New-NetFirewallRule -DisplayName "PostgreSQL Local" `
    -Direction Inbound `
    -LocalPort 5432 `
    -Protocol TCP `
    -Action Allow `
    -RemoteAddress 127.0.0.1

# Allow API access from specific IPs
New-NetFirewallRule -DisplayName "Trading API" `
    -Direction Inbound `
    -LocalPort 8000 `
    -Protocol TCP `
    -Action Allow `
    -RemoteAddress @("192.168.1.0/24")
```

### Secrets Management

**Environment Variable Encryption**:
```powershell
# Encrypt sensitive environment variables
$securePassword = ConvertTo-SecureString "password" -AsPlainText -Force
$encryptedPassword = ConvertFrom-SecureString $securePassword
Set-Content ".env.encrypted" $encryptedPassword

# Decrypt at runtime
$encryptedPassword = Get-Content ".env.encrypted"
$securePassword = ConvertTo-SecureString $encryptedPassword
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
)
```

### Audit Logging

**Security Event Logging**:
```python
import logging
from datetime import datetime

security_logger = logging.getLogger("security")

def log_security_event(event_type: str, details: dict):
    """Log security-relevant events."""
    security_logger.info(
        "security_event",
        extra={
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
            "source_ip": request.client.host,
            "user_agent": request.headers.get("user-agent")
        }
    )
```

## Monitoring and Observability

### Health Checks

**Service Health Endpoints**:
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "execution_gateway": await check_gateway_health()
        },
        "metrics": {
            "uptime_seconds": get_uptime(),
            "memory_usage_mb": get_memory_usage(),
            "cpu_usage_percent": get_cpu_usage()
        }
    }
```

### Log Aggregation

**Centralized Logging**:
```powershell
# Aggregate logs from all services
function Get-AggregatedLogs {
    param(
        [int]$TailLines = 100,
        [string]$Level = "INFO"
    )
    
    $logFiles = @(
        "logs/trading-api.log",
        "logs/orchestrator.log",
        "logs/execution-gateway.log",
        "logs/dashboard.log"
    )
    
    $logs = @()
    foreach ($file in $logFiles) {
        if (Test-Path $file) {
            $content = Get-Content $file -Tail $TailLines
            $logs += $content | Where-Object { $_ -match $Level }
        }
    }
    
    $logs | Sort-Object | Select-Object -Last $TailLines
}
```

### Metrics Collection

**Prometheus Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    "trading_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "trading_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"]
)

# System metrics
active_connections = Gauge(
    "trading_api_active_connections",
    "Number of active connections"
)

memory_usage = Gauge(
    "trading_api_memory_usage_bytes",
    "Memory usage in bytes"
)
```

## Documentation

### User Documentation

**Quick Start Guide** (`docs/native-deployment-quickstart.md`):
- Prerequisites checklist
- One-command installation
- Verification steps
- Common issues and solutions

**Configuration Reference** (`docs/native-deployment-config.md`):
- All configuration options
- Environment variables
- Service-specific settings
- Performance tuning guide

**Troubleshooting Guide** (`docs/native-deployment-troubleshooting.md`):
- Common error messages
- Diagnostic commands
- Log analysis
- Recovery procedures

### Developer Documentation

**Architecture Overview** (`docs/native-deployment-architecture.md`):
- System components
- Data flow diagrams
- Service interactions
- Technology stack

**Development Workflow** (`docs/native-deployment-development.md`):
- Setting up dev environment
- Running tests
- Debugging techniques
- Hot reload configuration

**API Reference** (`docs/native-deployment-api.md`):
- Process manager API
- Configuration API
- Health check endpoints
- Metrics endpoints

## Migration Path

### Phase 1: Parallel Deployment (Week 1-2)

- Install native services alongside Docker
- Run both deployments simultaneously
- Compare performance and behavior
- Identify any discrepancies

### Phase 2: Testing and Validation (Week 3-4)

- Run full test suite on native deployment
- Performance benchmarking
- Load testing
- Security audit

### Phase 3: Documentation and Training (Week 5)

- Complete all documentation
- Create video tutorials
- Train team on native deployment
- Prepare rollback procedures

### Phase 4: Production Migration (Week 6)

- Schedule maintenance window
- Export data from Docker
- Deploy native services
- Import data and verify
- Monitor for 48 hours
- Decommission Docker deployment

## Success Criteria

- ✅ All services run natively without Docker
- ✅ Performance meets or exceeds Docker deployment
- ✅ One-command installation works reliably
- ✅ All tests pass (182/182)
- ✅ Documentation is complete and accurate
- ✅ Migration path is validated
- ✅ Developer experience is improved
- ✅ Production deployment is stable
