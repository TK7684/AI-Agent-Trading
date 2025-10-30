# Trading Dashboard Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Trading Dashboard deployment.

## Quick Diagnostic Commands

```powershell
# Check all services status
docker-compose ps

# View all logs
docker-compose logs --tail=50

# Check system resources
docker stats --no-stream

# Run health check
.\scripts\health-check-dashboard.ps1
```

## Common Issues and Solutions

### 1. Services Won't Start

#### Symptoms
- Containers exit immediately
- "Port already in use" errors
- Services stuck in "starting" state

#### Diagnosis
```powershell
# Check container status
docker-compose ps

# View startup logs
docker-compose logs [service-name]

# Check port conflicts
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5432"
```

#### Solutions

**Port Conflicts:**
```powershell
# Find and kill process using port
$processId = (netstat -ano | findstr ":8000" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
Stop-Process -Id $processId -Force

# Or change port in docker-compose.yml
```

**Permission Issues:**
```powershell
# Reset Docker Desktop
# Settings > Troubleshoot > Reset to factory defaults

# Or restart Docker service
Restart-Service docker
```

### 2. Database Connection Issues

#### Symptoms
- API returns 500 errors
- "Connection refused" in logs
- Database health check fails

#### Diagnosis
```powershell
# Check database container
docker-compose logs postgres

# Test database connection
docker-compose exec postgres pg_isready -U trading -d trading

# Check database processes
docker-compose exec postgres ps aux
```

#### Solutions

**Database Not Ready:**
```powershell
# Wait for database initialization
Start-Sleep -Seconds 30

# Check initialization logs
docker-compose logs postgres | Select-String "ready to accept connections"
```

**Connection String Issues:**
```powershell
# Verify environment variables
docker-compose exec trading-api env | Select-String "DATABASE"

# Test manual connection
docker-compose exec postgres psql -U trading -d trading -c "SELECT 1;"
```

**Database Corruption:**
```powershell
# Stop services
docker-compose down

# Remove database volume
docker volume rm trading-dashboard_postgres_data

# Restart (will recreate database)
docker-compose up -d
```

### 3. Frontend Loading Issues

#### Symptoms
- White screen or loading spinner
- 404 errors for static assets
- Console errors in browser

#### Diagnosis
```powershell
# Check frontend container
docker-compose logs trading-dashboard

# Check nginx configuration
docker-compose exec trading-dashboard nginx -t

# Test static file serving
curl -I http://localhost/
```

#### Solutions

**Build Issues:**
```powershell
# Rebuild frontend
docker-compose build --no-cache trading-dashboard

# Check build logs
docker-compose logs trading-dashboard
```

**Nginx Configuration:**
```powershell
# Reload nginx configuration
docker-compose exec trading-dashboard nginx -s reload

# Test configuration
docker-compose exec trading-dashboard nginx -t
```

**Environment Variables:**
```powershell
# Check frontend environment
docker-compose exec trading-dashboard env | Select-String "VITE"
```

### 4. API Connection Issues

#### Symptoms
- Frontend shows "Connection Error"
- API requests timeout
- WebSocket connections fail

#### Diagnosis
```powershell
# Test API directly
curl http://localhost:8000/health

# Check API logs
docker-compose logs trading-api

# Test WebSocket connection
# (requires websocat: winget install websocat)
echo "ping" | websocat ws://localhost:8000/ws/trading
```

#### Solutions

**API Server Issues:**
```powershell
# Restart API service
docker-compose restart trading-api

# Check API health endpoint
curl -v http://localhost:8000/health
```

**CORS Issues:**
```powershell
# Check CORS configuration
docker-compose exec trading-api env | Select-String "CORS"

# Test with curl
curl -H "Origin: http://localhost:3000" -v http://localhost:8000/api/health
```

**WebSocket Proxy Issues:**
```powershell
# Check nginx WebSocket configuration
docker-compose exec trading-dashboard cat /etc/nginx/conf.d/default.conf | Select-String -A 10 "location /ws"
```

### 5. Authentication Issues

#### Symptoms
- Login fails with valid credentials
- Token validation errors
- Unauthorized access errors

#### Diagnosis
```powershell
# Check authentication logs
docker-compose logs trading-api | Select-String "auth"

# Test login endpoint
curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}'
```

#### Solutions

**JWT Secret Issues:**
```powershell
# Check JWT secret configuration
docker-compose exec trading-api env | Select-String "SECRET"

# Ensure SECRET_KEY is set and consistent
```

**Token Expiration:**
```powershell
# Check token expiration settings in API code
# Default is 60 minutes - may need adjustment for development
```

### 6. Performance Issues

#### Symptoms
- Slow page loads
- High CPU/memory usage
- Timeouts

#### Diagnosis
```powershell
# Check resource usage
docker stats --no-stream

# Check system performance
Get-Counter "\Processor(_Total)\% Processor Time"
Get-Counter "\Memory\Available MBytes"
```

#### Solutions

**High Memory Usage:**
```powershell
# Restart memory-intensive services
docker-compose restart trading-api

# Increase Docker memory limit
# Docker Desktop > Settings > Resources > Memory
```

**Database Performance:**
```powershell
# Check database connections
docker-compose exec postgres psql -U trading -d trading -c "SELECT count(*) FROM pg_stat_activity;"

# Restart database if needed
docker-compose restart postgres
```

**Frontend Performance:**
```powershell
# Clear browser cache
# Check browser developer tools for performance issues
# Consider enabling gzip compression in nginx
```

### 7. WebSocket Issues

#### Symptoms
- Real-time updates not working
- Connection drops frequently
- WebSocket handshake failures

#### Diagnosis
```powershell
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/trading

# Check nginx WebSocket proxy
docker-compose logs trading-dashboard | Select-String "websocket"
```

#### Solutions

**Proxy Configuration:**
```powershell
# Verify nginx WebSocket proxy settings
docker-compose exec trading-dashboard cat /etc/nginx/conf.d/default.conf
```

**Connection Timeouts:**
```powershell
# Increase WebSocket timeout in nginx configuration
# proxy_read_timeout 86400;
# proxy_send_timeout 86400;
```

### 8. SSL/HTTPS Issues

#### Symptoms
- Certificate errors
- Mixed content warnings
- HTTPS redirects not working

#### Diagnosis
```powershell
# Check SSL certificate
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test HTTPS connection
curl -k https://localhost/health
```

#### Solutions

**Certificate Issues:**
```powershell
# Generate self-signed certificate for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem
```

**Mixed Content:**
```powershell
# Update frontend environment variables
# VITE_API_BASE_URL=https://localhost/api
# VITE_WS_BASE_URL=wss://localhost/ws
```

## Advanced Troubleshooting

### Container Debugging

#### Access Container Shell
```powershell
# Frontend container
docker-compose exec trading-dashboard sh

# Backend container
docker-compose exec trading-api bash

# Database container
docker-compose exec postgres bash
```

#### Inspect Container Configuration
```powershell
# View container details
docker inspect trading-dashboard_trading-api_1

# Check environment variables
docker-compose exec trading-api env

# Check mounted volumes
docker-compose exec trading-api df -h
```

### Network Debugging

#### Test Internal Network Connectivity
```powershell
# Test API from frontend container
docker-compose exec trading-dashboard curl http://trading-api:8000/health

# Test database from API container
docker-compose exec trading-api curl http://postgres:5432
```

#### Check Docker Networks
```powershell
# List networks
docker network ls

# Inspect trading network
docker network inspect trading-dashboard_trading-network
```

### Log Analysis

#### Structured Log Analysis
```powershell
# Filter API errors
docker-compose logs trading-api | Select-String "ERROR"

# Filter database connection issues
docker-compose logs trading-api | Select-String "database"

# Filter authentication issues
docker-compose logs trading-api | Select-String "auth"
```

#### Export Logs for Analysis
```powershell
# Export all logs
docker-compose logs > "logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# Export specific service logs
docker-compose logs trading-api > "api_logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
```

## Recovery Procedures

### Complete System Reset

```powershell
# Stop all services
docker-compose down

# Remove all containers and volumes
docker-compose down -v --remove-orphans

# Clean Docker system
docker system prune -a

# Remove project volumes
docker volume ls | Select-String "trading-dashboard" | ForEach-Object { docker volume rm $_.ToString().Split()[1] }

# Restart from scratch
.\scripts\deploy-production.ps1 -Build
```

### Database Recovery

#### Backup Current Database
```powershell
# Create backup before recovery
docker-compose exec postgres pg_dump -U trading trading > "backup_before_recovery_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
```

#### Reset Database
```powershell
# Stop services
docker-compose stop trading-api

# Reset database
docker-compose exec postgres psql -U trading -d trading -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restart API (will recreate tables)
docker-compose start trading-api
```

#### Restore from Backup
```powershell
# Restore from backup file
Get-Content backup.sql | docker-compose exec -T postgres psql -U trading trading
```

### Configuration Recovery

#### Reset to Default Configuration
```powershell
# Backup current configuration
$backupDir = "config_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir
Copy-Item .env.* $backupDir/
Copy-Item docker-compose.*.yml $backupDir/

# Reset to defaults
git checkout -- docker-compose.*.yml
cp .env.production.example .env.production
```

## Monitoring and Alerting

### Enable Detailed Logging

#### API Logging
```powershell
# Set debug logging
docker-compose exec trading-api env LOG_LEVEL=DEBUG

# Restart with debug logging
docker-compose restart trading-api
```

#### Database Logging
```powershell
# Enable query logging
docker-compose exec postgres psql -U trading -d trading -c "ALTER SYSTEM SET log_statement = 'all';"
docker-compose exec postgres psql -U trading -d trading -c "SELECT pg_reload_conf();"
```

### Performance Monitoring

#### Real-time Monitoring
```powershell
# Monitor container resources
docker stats

# Monitor system resources
Get-Counter "\Processor(_Total)\% Processor Time" -Continuous
```

#### Log Monitoring
```powershell
# Monitor API logs in real-time
docker-compose logs -f trading-api

# Monitor error logs
docker-compose logs -f | Select-String "ERROR"
```

## Prevention Strategies

### Regular Health Checks

#### Automated Monitoring
```powershell
# Schedule health checks (Windows Task Scheduler)
# Run: .\scripts\health-check-dashboard.ps1
# Frequency: Every 5 minutes
```

#### Proactive Monitoring
```powershell
# Monitor disk space
Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, @{Name="FreeSpace(GB)";Expression={[math]::Round($_.FreeSpace/1GB,2)}}

# Monitor Docker resources
docker system df
```

### Backup Strategies

#### Automated Backups
```powershell
# Database backup script (schedule with Task Scheduler)
$backupFile = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
docker-compose exec postgres pg_dump -U trading trading > $backupFile

# Compress and store
Compress-Archive -Path $backupFile -DestinationPath "$backupFile.zip"
Remove-Item $backupFile
```

### Update Procedures

#### Safe Update Process
```powershell
# 1. Backup current state
.\scripts\backup-system.ps1

# 2. Test in development
.\scripts\deploy-development.ps1 -Clean -Build

# 3. Deploy to production
.\scripts\deploy-production.ps1 -Build
```

## Database Setup Issues

### Common Database Problems

#### Database Connection Failed
**Symptoms:**
- "Authentication failed" errors
- "Connection refused" messages
- API shows database: false in health check

**Diagnosis:**
```powershell
# Run comprehensive database diagnostics
.\scripts\Test-DatabaseConnection.ps1 -Detailed

# Check PostgreSQL service
Get-Service postgresql*

# Test manual connection
psql -U postgres -c "SELECT version();"
```

**Solutions:**
```powershell
# Option 1: Run automated setup wizard
.\scripts\Setup-Database.ps1

# Option 2: Reset password
.\scripts\Reset-PostgreSQL-Password.ps1

# Option 3: Start PostgreSQL service
Start-Service postgresql-x64-17
```

#### Missing Database Tables
**Symptoms:**
- Schema validation warnings
- "Table does not exist" errors
- Empty database

**Solutions:**
```powershell
# Create all required tables
.\scripts\Create-DatabaseTables.ps1

# Validate existing schema
.\scripts\Create-DatabaseTables.ps1 -Validate

# Force recreation if needed
.\scripts\Create-DatabaseTables.ps1 -Force
```

#### Fallback Mode Active
**Symptoms:**
- "Running in Fallback Mode" warnings
- Mock data instead of real data
- Limited functionality warnings

**Solutions:**
```powershell
# Fix database connection first
.\scripts\Setup-Database.ps1

# Then attempt reconnection
curl -X POST http://localhost:8000/system/database/reconnect

# Or restart the API server
```

### Database Diagnostic Commands

```powershell
# Quick connection test
.\scripts\Test-DatabaseConnection.ps1 -QuickTest

# Full diagnostics with system info
.\scripts\Test-DatabaseConnection.ps1 -Detailed

# Schema validation only
.\scripts\Create-DatabaseTables.ps1 -Validate

# API database diagnostics
curl http://localhost:8000/system/database/diagnostics
```

---

## Getting Additional Help

### Information to Collect

When seeking help, collect this information:

```powershell
# System information
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory

# Database diagnostics
.\scripts\Test-DatabaseConnection.ps1 -Detailed > database_diagnostics.txt

# Docker information (if using Docker)
docker version
docker-compose version

# Service status
docker-compose ps

# Recent logs
docker-compose logs --tail=100 > troubleshooting_logs.txt

# Environment configuration (excluding sensitive data)
Get-Content .env.local | Where-Object { $_ -notmatch "PASSWORD|SECRET|KEY" }

# PostgreSQL service status
Get-Service postgresql* | Format-Table
```

### Database-Specific Information

```powershell
# PostgreSQL version and status
psql -U postgres -c "SELECT version();"

# Database and user information
psql -U postgres -c "\l"  # List databases
psql -U postgres -c "\du" # List users

# Table information
psql -U trading -d trading -c "\dt"  # List tables

# Connection diagnostics
.\scripts\Test-DatabaseConnection.ps1 -Detailed
```

### Support Channels

1. **Documentation**: 
   - [DATABASE-SETUP-GUIDE.md](DATABASE-SETUP-GUIDE.md) for comprehensive setup
   - [QUICK-FIX-DATABASE.md](QUICK-FIX-DATABASE.md) for quick solutions
2. **Logs**: Always include relevant log excerpts and diagnostic output
3. **Environment**: Specify development vs production
4. **Steps to Reproduce**: Provide clear reproduction steps
5. **Database State**: Include database diagnostics output

This troubleshooting guide covers the most common issues encountered with the Trading Dashboard deployment. Follow the diagnostic steps and solutions appropriate to your specific issue.