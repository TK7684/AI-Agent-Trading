# Trading Dashboard - Production Deployment

A comprehensive guide for deploying the Trading Dashboard application in production environments.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### 1-Minute Production Setup

```powershell
# Clone and navigate
git clone <repository-url>
cd trading-dashboard

# Configure environment
cp .env.production.example .env.production
# Edit .env.production with your settings

# Deploy
.\scripts\deploy-production.ps1 -Build

# Access
# Frontend: http://localhost
# API: http://localhost:8000
```

## 📋 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  React Frontend │────│   FastAPI       │
│   (Port 80/443) │    │   (Dashboard)   │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │              ┌─────────────────┐
         │                       │              │   PostgreSQL    │
         │                       │              │     Redis       │
         │                       │              └─────────────────┘
         │                       │
    ┌─────────────────┐    ┌─────────────────┐
    │   Prometheus    │    │    Grafana      │
    │  (Monitoring)   │    │  (Dashboards)   │
    └─────────────────┘    └─────────────────┘
```

## 🛠️ Deployment Options

### Option 1: Automated Scripts (Recommended)

#### Production Deployment
```powershell
# Full production deployment with monitoring
.\scripts\deploy-production.ps1 -Build -Monitoring

# Staging deployment
.\scripts\deploy-production.ps1 -Environment staging

# View deployment options
.\scripts\deploy-production.ps1 -Help
```

#### Development Deployment
```powershell
# Development with hot reload
.\scripts\deploy-development.ps1

# Clean rebuild
.\scripts\deploy-development.ps1 -Clean -Build
```

### Option 2: Manual Docker Compose

#### Production
```powershell
# Set environment
$env:COMPOSE_FILE = "docker-compose.trading-dashboard.yml"

# Load production environment
Get-Content .env.production | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

# Deploy core services
docker-compose up -d

# Add monitoring (optional)
docker-compose --profile monitoring up -d
```

#### Development
```powershell
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

## ⚙️ Configuration

### Environment Files

| File | Purpose | Usage |
|------|---------|-------|
| `.env.production` | Production settings | Required for production |
| `.env.development` | Development settings | Used by dev compose |
| `.env.staging` | Staging settings | Optional staging env |

### Key Configuration Variables

```bash
# Security (REQUIRED - Change these!)
POSTGRES_PASSWORD=your-secure-postgres-password
SECRET_KEY=your-very-secure-secret-key-change-this
GRAFANA_PASSWORD=your-secure-grafana-password

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com

# Database
POSTGRES_DB=trading
POSTGRES_USER=trading
DATABASE_URL=postgresql://trading:${POSTGRES_PASSWORD}@postgres:5432/trading

# Cache
REDIS_URL=redis://redis:6379/0
```

## 🔒 Security Configuration

### SSL/HTTPS Setup

1. **Obtain SSL certificates**:
   ```powershell
   # Using Let's Encrypt (example)
   certbot certonly --standalone -d yourdomain.com
   ```

2. **Place certificates**:
   ```
   nginx/ssl/cert.pem
   nginx/ssl/key.pem
   ```

3. **Enable HTTPS**:
   ```powershell
   # Uncomment SSL configuration in nginx/conf.d/trading-dashboard.conf
   # Deploy with production profile
   docker-compose --profile production up -d
   ```

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY (32+ characters)
- [ ] Configure CORS_ORIGINS for your domain
- [ ] Enable HTTPS with valid certificates
- [ ] Restrict database access to internal network
- [ ] Enable firewall rules
- [ ] Regular security updates

## 📊 Monitoring Setup

### Enable Monitoring Stack

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

### Available Dashboards

- **Trading Performance**: P&L, win rates, trade statistics
- **System Health**: CPU, memory, disk usage
- **API Performance**: Request metrics, response times
- **Database Metrics**: Connection pools, query performance

## 🏥 Health Monitoring

### Automated Health Checks

```powershell
# Run comprehensive health check
.\scripts\health-check-dashboard.ps1

# Schedule with Windows Task Scheduler
# Frequency: Every 5 minutes
# Action: PowerShell script execution
```

### Manual Health Checks

```powershell
# Check all services
docker-compose ps

# Test endpoints
curl http://localhost/health          # Frontend
curl http://localhost:8000/health     # Backend API
curl http://localhost:8000/api/health # API health

# Check logs
docker-compose logs --tail=50
```

### Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health` | Frontend health | HTTP 200 "healthy" |
| `/api/health` | Backend health | HTTP 200 JSON status |
| `/api/system/health` | System metrics | HTTP 200 system data |

## 🔧 Maintenance

### Regular Tasks

#### Daily
- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor resource usage

#### Weekly
- [ ] Backup database
- [ ] Update Docker images
- [ ] Review monitoring dashboards

#### Monthly
- [ ] Security updates
- [ ] Performance optimization
- [ ] Capacity planning

### Backup Procedures

#### Database Backup
```powershell
# Manual backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker-compose exec postgres pg_dump -U trading trading > "backup_$timestamp.sql"

# Automated backup (schedule with Task Scheduler)
.\scripts\backup-database.ps1
```

#### Configuration Backup
```powershell
# Backup configuration files
$backupDir = "config_backup_$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Path $backupDir
Copy-Item .env.* $backupDir/
Copy-Item docker-compose.*.yml $backupDir/
Copy-Item -Recurse nginx/ $backupDir/
```

### Update Procedures

#### Application Updates
```powershell
# Pull latest code
git pull origin main

# Backup current state
.\scripts\backup-system.ps1

# Deploy updates
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

## 🚨 Troubleshooting

### Common Issues

#### Services Won't Start
```powershell
# Check container status
docker-compose ps

# View startup logs
docker-compose logs [service-name]

# Check port conflicts
netstat -ano | findstr ":8000"
```

#### Database Connection Issues
```powershell
# Check database health
docker-compose exec postgres pg_isready -U trading

# Test connection
docker-compose exec postgres psql -U trading -d trading -c "SELECT 1;"

# Restart database
docker-compose restart postgres
```

#### Frontend Loading Issues
```powershell
# Check frontend logs
docker-compose logs trading-dashboard

# Test nginx configuration
docker-compose exec trading-dashboard nginx -t

# Reload nginx
docker-compose exec trading-dashboard nginx -s reload
```

### Recovery Procedures

#### Complete System Reset
```powershell
# Stop all services
docker-compose down

# Remove containers and volumes
docker-compose down -v --remove-orphans

# Clean Docker system
docker system prune -a

# Restart from scratch
.\scripts\deploy-production.ps1 -Build
```

#### Database Recovery
```powershell
# Restore from backup
Get-Content backup.sql | docker-compose exec -T postgres psql -U trading trading
```

### Getting Help

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

When reporting issues, include:
- Service status: `docker-compose ps`
- Recent logs: `docker-compose logs --tail=100`
- System info: `docker version && docker-compose version`
- Environment: Development/Production

## 📚 Additional Resources

### Documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive deployment guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed troubleshooting
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

### Useful Commands

```powershell
# Service Management
docker-compose ps                    # List services
docker-compose logs -f [service]     # View logs
docker-compose restart [service]     # Restart service
docker-compose exec [service] sh     # Shell into container

# System Information
docker stats --no-stream            # Resource usage
docker system df                     # Disk usage
docker system prune                  # Clean up

# Database Operations
docker-compose exec postgres psql -U trading trading  # Database shell
docker-compose exec redis redis-cli                   # Redis shell
```

### Performance Optimization

#### Production Tuning
- **Database**: Configure connection pooling, query optimization
- **Redis**: Set appropriate memory limits and eviction policies
- **Nginx**: Enable gzip compression, optimize worker processes
- **Application**: Use production builds, enable caching

#### Scaling Considerations
- **Horizontal Scaling**: Use load balancer with multiple API instances
- **Database Scaling**: Consider read replicas for high load
- **Caching**: Implement Redis clustering for high availability
- **Monitoring**: Set up alerting for resource thresholds

## 🎯 Production Checklist

Before going live:

### Security
- [ ] All default passwords changed
- [ ] SSL certificates configured
- [ ] Firewall rules in place
- [ ] CORS origins restricted
- [ ] Security headers enabled

### Performance
- [ ] Resource limits configured
- [ ] Database optimized
- [ ] Caching enabled
- [ ] Monitoring active

### Reliability
- [ ] Health checks configured
- [ ] Backup procedures tested
- [ ] Recovery procedures documented
- [ ] Monitoring alerts set up

### Compliance
- [ ] Logging configured
- [ ] Audit trails enabled
- [ ] Data retention policies
- [ ] Privacy controls

---

## 🆘 Emergency Contacts

For production issues:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Run health checks: `.\scripts\health-check-dashboard.ps1`
3. Check monitoring dashboards
4. Review recent logs
5. Contact system administrator

**Remember**: Always backup before making changes in production!