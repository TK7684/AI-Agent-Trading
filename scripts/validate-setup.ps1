Write-Host "Validating Autonomous Trading System setup..." -ForegroundColor Green

$errors = 0

Write-Host "Checking project structure..." -ForegroundColor Yellow
$requiredDirs = @("apps", "libs", "infra", "ops", ".github", "tests", "scripts")
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "✓ Directory $dir exists" -ForegroundColor Green
    } else {
        Write-Host "✗ Directory $dir missing" -ForegroundColor Red
        $errors++
    }
}

Write-Host "Checking required files..." -ForegroundColor Yellow
$requiredFiles = @("pyproject.toml", "Cargo.toml", "Dockerfile", ".gitignore", ".pre-commit-config.yaml", "README.md", "Makefile", "config.toml")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✓ File $file exists" -ForegroundColor Green
    } else {
        Write-Host "✗ File $file missing" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "Validation Summary:" -ForegroundColor Cyan
if ($errors -eq 0) {
    Write-Host "✓ All checks passed! Project setup is complete." -ForegroundColor Green
} else {
    Write-Host "✗ $errors errors found." -ForegroundColor Red
}

Write-Host "Project foundation setup is complete!" -ForegroundColor Green