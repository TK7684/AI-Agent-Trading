# Development deployment script for Trading Dashboard
param(
    [switch]$Build = $false,
    [switch]$Clean = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host "Trading Dashboard Development Deployment Script"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Usage: .\deploy-development.ps1 [options]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Build    Force rebuild of Docker images"
    Write-Host "  -Clean    Clean up existing containers and volumes"
    Write-Host "  -Help     Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy-development.ps1"
    Write-Host "  .\deploy-development.ps1 -Build"
    Write-Host "  .\deploy-development.ps1 -Clean -Build"
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

function Clean-Environment {
    if ($Clean) {
        Write-ColorOutput "🧹 Cleaning development environment..." $Blue
        
        # Stop and remove containers
        docker-compose -f docker-compose.dev.yml down -v --remove-orphans
        
        # Remove development images if they exist
        $images = @("trading-dashboard-dev", "trading-api-dev")
        foreach ($image in $images) {
            if (docker images -q $image) {
                Write-ColorOutput "Removing image: $image" $Yellow
                docker rmi $image -f
            }
        }
        
        Write-ColorOutput "✅ Environment cleaned" $Green
    }
}

function Deploy-Development {
    Write-ColorOutput "🚀 Starting development environment..." $Blue
    
    # Set environment variables
    $env:COMPOSE_FILE = "docker-compose.dev.yml"
    $env:COMPOSE_PROJECT_NAME = "trading-dashboard-dev"
    
    # Load development environment
    if (Test-Path ".env.development") {
        Get-Content ".env.development" | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
            }
        }
    }
    
    # Start services
    $composeArgs = @("up", "-d")
    if ($Build) {
        $composeArgs += "--build"
    }
    
    docker-compose -f docker-compose.dev.yml @composeArgs
    
    Write-ColorOutput "✅ Development environment started" $Green
}

function Show-Development-Status {
    Write-ColorOutput "📊 Development Environment Status" $Blue
    Write-ColorOutput "=================================" $Blue
    
    # Show running containers
    Write-ColorOutput "`nRunning containers:" $Yellow
    docker-compose -f docker-compose.dev.yml ps
    
    # Show service URLs
    Write-ColorOutput "`nDevelopment URLs:" $Yellow
    Write-ColorOutput "Frontend (with hot reload): http://localhost:3000" $Green
    Write-ColorOutput "Backend API: http://localhost:8000" $Green
    Write-ColorOutput "API Documentation: http://localhost:8000/docs" $Green
    Write-ColorOutput "Database: localhost:5433 (user: trading, db: trading_dev)" $Green
    Write-ColorOutput "Redis: localhost:6380" $Green
    
    Write-ColorOutput "`nUseful commands:" $Yellow
    Write-Host "View logs: docker-compose -f docker-compose.dev.yml logs -f [service-name]"
    Write-Host "Stop services: docker-compose -f docker-compose.dev.yml down"
    Write-Host "Restart service: docker-compose -f docker-compose.dev.yml restart [service-name]"
    Write-Host "Shell into container: docker-compose -f docker-compose.dev.yml exec [service-name] sh"
}

# Main execution
try {
    Write-ColorOutput "🛠️ Trading Dashboard Development Setup" $Blue
    Write-ColorOutput "======================================" $Blue
    
    Clean-Environment
    Deploy-Development
    
    # Wait a moment for services to start
    Start-Sleep -Seconds 5
    
    Show-Development-Status
    
    Write-ColorOutput "`n✅ Development environment ready!" $Green
    Write-ColorOutput "Frontend will be available at http://localhost:3000 with hot reload" $Green
    Write-ColorOutput "Backend API will be available at http://localhost:8000" $Green
    
} catch {
    Write-ColorOutput "`n❌ Setup failed: $($_.Exception.Message)" $Red
    Write-ColorOutput "Check logs with: docker-compose -f docker-compose.dev.yml logs" $Yellow
    exit 1
}