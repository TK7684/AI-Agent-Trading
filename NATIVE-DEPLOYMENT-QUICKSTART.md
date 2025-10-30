# Native Deployment Quick Start

Get the trading system running natively on Windows without Docker in under 10 minutes.

## Prerequisites

Before starting, ensure you have:

- ✅ **Windows 10/11** (64-bit)
- ✅ **Administrator access** (for installing services)
- ✅ **Internet connection** (for downloading dependencies)

## One-Command Installation

```powershell
# Clone the repository (if not already done)
git clone <repository-url>
cd autonomous-trading-system

# Run the automated setup
.\scripts\Setup-NativeDevelopment.ps1
```

That's it! The script will:
1. Check prerequisites (Python, Node.js, Rust, etc.)
2. Install PostgreSQL and Redis
3. Install all dependencies
4. Build the execution gateway
5. Initialize the database
6. Run health checks

## Manual Installation (If Needed)

If you prefer step-by-step installation or the automated script fails:

### Step 1: Install Prerequisites

```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python 3.11+
choco install python311 -y

# Install Node.js
choco install nodejs -y

# Install Rust
choco install rust -y

# Install Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Step 2: Install Native Services

```powershell
.\scripts\install-native-services.ps1
```

This installs:
- PostgreSQL 15
- Redis 7

### Step 3: Configure Environment

```powershell
# Create local environment file
copy .env.native.template .env.local

# Edit with your settings
notepad .env.local
```

Update these values:
- `POSTGRES_PASSWORD` - Your PostgreSQL password
- `SECRET_KEY` - Generate a secure random key
- API keys (OpenAI, Anthropic, etc.)

### Step 4: Install Dependencies

```powershell
# Python dependencies
poetry install

# Node.js dependencies
cd apps\trading-dashboard-ui-clean
npm install
cd ..\..

# Build Rust execution gateway
cargo build --package execution-gateway --release
```

### Step 5: Initialize Database

```powershell
.\scripts\init-database.ps1
```

### Step 6: Start the System

```powershell
.\scripts\start-trading-system.ps1
```

## Verification

Once started, verify the system is running:

```powershell
# Check service status
.\scripts\get-trading-status.ps1

# View logs
.\scripts\get-trading-logs.ps1

# Run health check
.\scripts\Test-TradingSystemHealth.ps1
```

## Access Points

After successful startup:

- **Trading Dashboard**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs
- **Trading API**: http://localhost:8000
- **Execution Gateway**: http://localhost:3000

## Common Commands

```powershell
# Start the system
.\scripts\start-trading-system.ps1

# Stop the system
.\scripts\stop-trading-system.ps1

# Check status
.\scripts\get-trading-status.ps1

# View logs
.\scripts\get-trading-logs.ps1 -Service trading-api

# Restart a service
.\scripts\Restart-TradingService.ps1 -ServiceName trading-api

# Run diagnostics
.\scripts\Test-TradingSystemHealth.ps1 -Detailed

# Backup database
.\scripts\Backup-TradingDatabase.ps1

# Reset database (development only)
.\scripts\Reset-TradingDatabase.ps1
```

## Troubleshooting

### Services Won't Start

```powershell
# Check prerequisites
.\scripts\Test-TradingSystemHealth.ps1

# Check PostgreSQL
Get-Service postgresql*

# Check Redis
Get-Service Redis

# View detailed logs
.\scripts\get-trading-logs.ps1 -Service <service-name> -Tail 100
```

### Database Connection Issues

```powershell
# Test PostgreSQL connection
psql -h localhost -U trading -d trading

# Check DATABASE_URL in .env.local
Get-Content .env.local | Select-String "DATABASE_URL"

# Reinitialize database
.\scripts\Reset-TradingDatabase.ps1
```

### Port Conflicts

If ports are already in use:

1. Edit `config/services.json`
2. Change port numbers for conflicting services
3. Update `.env.local` with new ports
4. Restart the system

### Build Failures

```powershell
# Clean and rebuild Rust
cargo clean
cargo build --package execution-gateway --release

# Reinstall Python dependencies
poetry install --no-cache

# Reinstall Node.js dependencies
cd apps\trading-dashboard-ui-clean
Remove-Item node_modules -Recurse -Force
npm install
```

## Performance Tips

1. **Disable Windows Defender** for project directory (improves build times)
2. **Use SSD** for database and logs
3. **Increase PostgreSQL** shared_buffers in postgresql.conf
4. **Configure Redis** maxmemory in redis.conf

## Next Steps

- Read [NATIVE-DEPLOYMENT.md](NATIVE-DEPLOYMENT.md) for detailed documentation
- Configure [config.toml](config.toml) for trading parameters
- Set up API keys in `.env.local`
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Getting Help

If you encounter issues:

1. Run diagnostics: `.\scripts\Test-TradingSystemHealth.ps1 -Detailed`
2. Check logs: `.\scripts\get-trading-logs.ps1`
3. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. Check GitHub issues

## Production Deployment

For production deployment, see:
- [Setup-NativeProduction.ps1](scripts/Setup-NativeProduction.ps1)
- Production deployment guide (coming soon)

---

**Ready to trade!** 🚀

The system is now running natively without Docker, providing better performance and easier debugging.
