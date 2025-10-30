# Production deployment script for Trading Dashboard
param(
    [string]$Environment = "production",
    [switch]$Build = $false,
    [switch]$Monitoring = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host "Trading Dashboard Production Deployment Script"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Usage: .\deploy-production.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Environment    Environment to deploy (production, staging)"
    Write-Host "  -Build          Force rebuild of Docker images"
    Write-Host "  -Monitoring     Include monitoring stack (Prometheus, Grafana)"
    Write-Host "  -Help           Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy-production.ps1"
    Write-Host "  .\deploy-production.ps1 -Build -Monitoring"
    Write-Host "  .\deploy-production.ps1 -Environment staging"
    exit 0
}

# Colors for output
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = $Reset)
    Write-Host "$Color$Message$Reset"
}

function Check-Prerequisites {
    Write-ColorOutput "🔍 Checking prerequisites..." $Blue
    
    # Check Docker
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "❌ Docker is not installed or not in PATH" $Red
        exit 1
    }
    
    # Check Docker Compose
    if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "❌ Docker Compose is not installed or not in PATH" $Red
        exit 1
    }
    
    # Check if Docker is running
    try {
        docker info | Out-Null
        Write-ColorOutput "✅ Docker is running" $Green
    } catch {
        Write-ColorOutput "❌ Docker is not running. Please start Docker Desktop." $Red
        exit 1
    }
    
    # Check environment file
    $envFile = ".env.$Environment"
    if (!(Test-Path $envFile)) {
        Write-ColorOutput "❌ Environment file $envFile not found" $Red
        exit 1
    }
    
    Write-ColorOutput "✅ All prerequisites met" $Green
}

function Build-Images {
    if ($Build) {
        Write-ColorOutput "🔨 Building Docker images..." $Blue
        
        # Build frontend
        Write-ColorOutput "Building frontend image..." $Yellow
        docker build -t trading-dashboard-ui:latest ./apps/trading-dashboard-ui-clean/
        
        # Build backend
        Write-ColorOutput "Building backend image..." $Yellow
        docker build -t trading-api:latest ./apps/trading-api/
        
        Write-ColorOutput "✅ Images built successfully" $Green
    }
}

function Deploy-Services {
    Write-ColorOutput "🚀 Deploying services..." $Blue
    
    # Set environment
    $env:COMPOSE_FILE = "docker-compose.trading-dashboard.yml"
    $env:COMPOSE_PROJECT_NAME = "trading-dashboard"
    
    # Load environment variables
    Get-Content ".env.$Environment" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
    
    # Deploy core services
    $composeArgs = @("up", "-d")
    if ($Build) {
        $composeArgs += "--build"
    }
    
    Write-ColorOutput "Starting core services..." $Yellow
    docker-compose @composeArgs
    
    # Deploy monitoring if requested
    if ($Monitoring) {
        Write-ColorOutput "Starting monitoring services..." $Yellow
        docker-compose --profile monitoring up -d
    }
    
    Write-ColorOutput "✅ Services deployed successfully" $Green
}

function Wait-ForServices {
    Write-ColorOutput "⏳ Waiting for services to be ready..." $Blue
    
    $maxAttempts = 30
    $attempt = 0
    
    do {
        $attempt++
        Write-ColorOutput "Attempt $attempt/$maxAttempts..." $Yellow
        
        try {
            # Check frontend
            $frontendResponse = Invoke-WebRequest -Uri "http://localhost/health" -TimeoutSec 5 -UseBasicParsing
            
            # Check backend
            $backendResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
            
            if ($frontendResponse.StatusCode -eq 200 -and $backendResponse.StatusCode -eq 200) {
                Write-ColorOutput "✅ All services are ready!" $Green
                return
            }
        } catch {
            # Services not ready yet
        }
        
        Start-Sleep -Seconds 10
    } while ($attempt -lt $maxAttempts)
    
    Write-ColorOutput "⚠️ Services may not be fully ready. Check logs with: docker-compose logs" $Yellow
}

function Show-Status {
    Write-ColorOutput "📊 Deployment Status" $Blue
    Write-ColorOutput "===================" $Blue
    
    # Show running containers
    Write-ColorOutput "`nRunning containers:" $Yellow
    docker-compose ps
    
    # Show service URLs
    Write-ColorOutput "`nService URLs:" $Yellow
    Write-ColorOutput "Frontend: http://localhost" $Green
    Write-ColorOutput "API: http://localhost:8000" $Green
    Write-ColorOutput "API Docs: http://localhost:8000/docs" $Green
    
    if ($Monitoring) {
        Write-ColorOutput "Prometheus: http://localhost:9090" $Green
        Write-ColorOutput "Grafana: http://localhost:3001" $Green
    }
    
    Write-ColorOutput "`nTo view logs: docker-compose logs -f [service-name]" $Yellow
    Write-ColorOutput "To stop services: docker-compose down" $Yellow
}

# Main execution
try {
    Write-ColorOutput "🚀 Trading Dashboard Production Deployment" $Blue
    Write-ColorOutput "==========================================" $Blue
    
    Check-Prerequisites
    Build-Images
    Deploy-Services
    Wait-ForServices
    Show-Status
    
    Write-ColorOutput "`n✅ Deployment completed successfully!" $Green
    
} catch {
    Write-ColorOutput "`n❌ Deployment failed: $($_.Exception.Message)" $Red
    Write-ColorOutput "Check logs with: docker-compose logs" $Yellow
    exit 1
}