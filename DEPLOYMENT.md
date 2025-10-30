# Trading Dashboard Deployment Guide

This guide covers the deployment of the Trading Dashboard application in both development and production environments using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

### Required Software

- **Docker Desktop** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **PowerShell** (for Windows deployment scripts)
- **Git** (for cloning the repository)

### System Requirements

- **Minimum**: 4GB RAM, 2 CPU cores, 10GB disk space
- **Recommended**: 8GB RAM, 4 CPU cores, 20GB disk space

### Network Requirements

- Port 80 (HTTP frontend)
- Port 443 (HTTPS frontend, production only)
- Port 8000 (API backend)
- Port 5432 (PostgreSQL)
- Port 6379 (Redis)
- Port 3000 (Development frontend)
- Port 9090 (Prometheus, monitoring)
- Port 3001 (Grafana, monitoring)

## Quick Start

### Development Environment

```powershell
# Clone the repository
git clone <repository-url>
cd trading-dashboard

# Start development environment
.\scripts\deploy-development.ps1

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Production Environment

```powershell
# Configure environment
cp .env.production.example .env.production
# Edit .env.production with your settings

# Deploy production
.\scripts\deploy-production.ps1 -Build

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
```

## Development Deployment

### Using PowerShell Scripts

The easiest way to start the development environment:

```powershell
# Basic development setup
.\scripts\deploy-development.ps1

# Clean rebuild
.\scripts\deploy-development.ps1 -Clean -Build

# View help
.\scripts\deploy-development.ps1 -Help
```

### Manual Docker Compose

```powershell
# Start development services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### Development Features

- **Hot Reload**: Frontend automatically reloads on code changes
- **Debug Mode**: Backend runs with debug logging and auto-reload
- **Separate Database**: Uses `trading_dev` database on port 5433
- **Volume Mounts**: Source code is mounted for live editing

### Development URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React development server |
| Backend API | http://localhost:8000 | FastAPI with auto-reload |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Database | localhost:5433 | PostgreSQL (user: trading, db: trading_dev) |
| Redis | localhost:6380 | Redis cache |

## Production Deployment

### Environment Configuration

1. **Copy environment template**:
   ```powershell
   cp .env.production.example .env.production
   ```

2. **Edit configuration**:
   ```bash
   # Required: Change these values
   POSTGRES_PASSWORD=your-secure-postgres-password
   SECRET_KEY=your-very-secure-secret-key-change-this
   GRAFANA_PASSWORD=your-secure-grafana-password
   
   # Optional: Configure for your domain
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   ```

### Deployment Options

#### Option 1: Using PowerShell Scripts (Recommended)

```powershell
# Basic production deployment
.\scripts\deploy-production.ps1

# Full deployment with monitoring
.\scripts\deploy-production.ps1 -Build -Monitoring

# Staging deployment
.\scripts\deploy-production.ps1 -Environment staging
```

#### Option 2: Manual Docker Compose

```powershell
# Set environment
$env:COMPOSE_FILE = "docker-compose.trading-dashboard.yml"
$env:COMPOSE_PROJECT_NAME = "trading-dashboard"

# Load environment variables
Get-Content .env.production | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

# Deploy core services
docker-compose up -d

# Deploy with monitoring
docker-compose --profile monitoring up -d
```

### Production Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │  Trading UI     │
│   (Port 80/443) │────│  (React/Nginx)  │
└─────────────────┘    └─────────────────┘
         │                       │
         │              ┌─────────────────┐
         └──────────────│  Trading API    │
                        │  (FastAPI)      │
                        └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │     Redis       │
                    └─────────────────┘
```

### Production URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost | Production React app |
| Backend API | http://localhost:8000 | Production FastAPI |
| API Docs | http://localhost:8000/docs | API documentation |
| Prometheus | http://localhost:9090 | Metrics (monitoring profile) |
| Grafana | http://localhost:3001 | Dashboards (monitoring profile) |

## Configuration

### Environment Variables

#### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `production` | Yes |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `SECRET_KEY` | JWT secret key | - | Yes |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |

#### Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_DB` | Database name | `trading` | Yes |
| `POSTGRES_USER` | Database user | `trading` | Yes |
| `POSTGRES_PASSWORD` | Database password | - | Yes |
| `DATABASE_URL` | Full database URL | Auto-generated | No |

#### Redis Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` | No |

### SSL/HTTPS Configuration

For production HTTPS deployment:

1. **Obtain SSL certificates** (Let's Encrypt, commercial CA, etc.)

2. **Place certificates**:
   ```
   nginx/ssl/cert.pem
   nginx/ssl/key.pem
   ```

3. **Update nginx configuration**:
   ```bash
   # Uncomment SSL lines in nginx/conf.d/trading-dashboard.conf
   ssl_certificate /etc/nginx/ssl/cert.pem;
   ssl_certificate_key /etc/nginx/ssl/key.pem;
   ```

4. **Deploy with SSL profile**:
   ```powershell
   docker-compose --profile production up -d
   ```

## Monitoring

### Enabling Monitoring Stack

```powershell
# Deploy with monitoring
.\scripts\deploy-production.ps1 -Monitoring

# Or manually
docker-compose --profile monitoring up -d
```

### Monitoring Services

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| Prometheus | http://localhost:9090 | None | Metrics collection |
| Grafana | http://localhost:3001 | admin/[GRAFANA_PASSWORD] | Dashboards |

### Available Metrics

- **Application Metrics**: API response times, error rates, request counts
- **System Metrics**: CPU, memory, disk usage
- **Database Metrics**: Connection counts, query performance
- **Trading Metrics**: Trade counts, P&L, system health

### Custom Dashboards

Pre-configured Grafana dashboards are available in `monitoring/grafana/dashboards/`:

- **Trading Performance Dashboard**: P&L, win rates, trade statistics
- **System Health Dashboard**: Infrastructure metrics
- **API Performance Dashboard**: Request metrics, error rates

## Troubleshooting

### Common Issues

#### 1. Port Conflicts

**Problem**: Port already in use
```
Error: bind: address already in use
```

**Solution**:
```powershell
# Check what's using the port
netstat -ano | findstr :8000

# Kill the process or change port in docker-compose
```

#### 2. Database Connection Issues

**Problem**: Cannot connect to database
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions**:
```powershell
# Check database container
docker-compose logs postgres

# Restart database
docker-compose restart postgres

# Check database health
docker-compose exec postgres pg_isready -U trading
```

#### 3. Frontend Build Issues

**Problem**: Frontend fails to build
```
npm ERR! code ELIFECYCLE
```

**Solutions**:
```powershell
# Clear npm cache
docker-compose exec trading-dashboard-dev npm cache clean --force

# Rebuild with clean slate
.\scripts\deploy-development.ps1 -Clean -Build
```

#### 4. WebSocket Connection Issues

**Problem**: Real-time updates not working

**Solutions**:
```powershell
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/trading

# Check nginx WebSocket proxy configuration
docker-compose logs nginx-proxy
```

### Health Checks

#### Automated Health Check

```powershell
# Run comprehensive health check
.\scripts\health-check-dashboard.ps1
```

#### Manual Health Checks

```powershell
# Check frontend
curl http://localhost/health

# Check backend
curl http://localhost:8000/health

# Check API endpoints
curl http://localhost:8000/api/health

# Check database via API
curl http://localhost:8000/api/system/health
```

### Log Analysis

#### View Service Logs

```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-api

# Last 100 lines
docker-compose logs --tail=100 trading-dashboard
```

#### Log Locations

- **Application Logs**: `./logs/api/`
- **Nginx Logs**: `./logs/nginx/`
- **Database Logs**: Container logs only
- **System Logs**: Container logs only

### Performance Issues

#### High Memory Usage

```powershell
# Check container resource usage
docker stats

# Restart memory-intensive services
docker-compose restart trading-api
```

#### Slow API Responses

```powershell
# Check database performance
docker-compose exec postgres psql -U trading -c "SELECT * FROM pg_stat_activity;"

# Check Redis performance
docker-compose exec redis redis-cli info stats
```

### Recovery Procedures

#### Complete System Recovery

```powershell
# Stop all services
docker-compose down

# Clean up containers and volumes
docker-compose down -v --remove-orphans

# Rebuild and restart
.\scripts\deploy-production.ps1 -Build
```

#### Database Recovery

```powershell
# Backup database
docker-compose exec postgres pg_dump -U trading trading > backup.sql

# Restore database
docker-compose exec -T postgres psql -U trading trading < backup.sql
```

## Security Considerations

### Production Security Checklist

- [ ] **Change default passwords** in `.env.production`
- [ ] **Use strong SECRET_KEY** (32+ random characters)
- [ ] **Configure CORS_ORIGINS** for your domain only
- [ ] **Enable HTTPS** with valid SSL certificates
- [ ] **Update Docker images** regularly
- [ ] **Monitor security logs** for suspicious activity
- [ ] **Backup database** regularly
- [ ] **Restrict network access** to necessary ports only

### Network Security

```bash
# Production firewall rules (example)
# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Restrict database access (internal only)
ufw deny 5432/tcp

# Restrict Redis access (internal only)
ufw deny 6379/tcp
```

### Container Security

- **Non-root users**: All containers run as non-root users
- **Read-only filesystems**: Where possible
- **Security scanning**: Regularly scan images for vulnerabilities
- **Minimal base images**: Using Alpine Linux for smaller attack surface

### Data Protection

- **Encryption at rest**: Configure database encryption
- **Encryption in transit**: Use HTTPS/WSS for all communications
- **Backup encryption**: Encrypt database backups
- **Access logging**: Monitor all API access

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- [ ] Check service health and logs
- [ ] Review monitoring dashboards
- [ ] Update Docker images if needed

#### Monthly
- [ ] Backup database
- [ ] Review security logs
- [ ] Update dependencies
- [ ] Performance optimization review

#### Quarterly
- [ ] Security audit
- [ ] Disaster recovery testing
- [ ] Capacity planning review

### Update Procedures

#### Application Updates

```powershell
# Pull latest code
git pull origin main

# Rebuild and deploy
.\scripts\deploy-production.ps1 -Build
```

#### Docker Image Updates

```powershell
# Pull latest base images
docker-compose pull

# Rebuild with latest images
docker-compose build --no-cache

# Deploy updated images
docker-compose up -d
```

### Backup Procedures

#### Database Backup

```powershell
# Create backup
docker-compose exec postgres pg_dump -U trading trading > "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

# Automated backup script
# Add to Windows Task Scheduler for regular backups
```

#### Configuration Backup

```powershell
# Backup configuration files
$backupDir = "backup_$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Path $backupDir
Copy-Item .env.production $backupDir/
Copy-Item docker-compose.*.yml $backupDir/
Copy-Item -Recurse nginx/ $backupDir/
```

## Support

### Getting Help

1. **Check this documentation** for common issues
2. **Review application logs** for error details
3. **Check Docker container status** and logs
4. **Run health checks** to identify failing components
5. **Consult monitoring dashboards** for system metrics

### Useful Commands Reference

```powershell
# Service management
docker-compose ps                          # List running services
docker-compose logs -f [service]          # View logs
docker-compose restart [service]          # Restart service
docker-compose exec [service] sh          # Shell into container

# System information
docker system df                           # Docker disk usage
docker system prune                        # Clean up unused resources
docker stats                               # Container resource usage

# Database operations
docker-compose exec postgres psql -U trading trading  # Database shell
docker-compose exec redis redis-cli                   # Redis shell
```

This deployment guide provides comprehensive instructions for deploying the Trading Dashboard in both development and production environments. Follow the appropriate sections based on your deployment needs and environment.