# Setting Up Testing Environment on Windows

This guide helps you set up the testing environment for Investment Auditor on Windows.

## Prerequisites

1. **Node.js**: Ensure Node.js 18+ is installed
   ```cmd
   node --version
   ```

2. **PostgreSQL**: Ensure PostgreSQL is installed and running
   ```cmd
   psql --version
   ```

3. **Git**: Ensure Git is installed
   ```cmd
   git --version
   ```

## Installation Steps

### Option 1: Using PNPM (Recommended)

1. Install PNPM globally:
   ```cmd
   npm install -g pnpm
   ```

2. Verify PNPM installation:
   ```cmd
   pnpm --version
   ```

3. Install project dependencies:
   ```cmd
   pnpm install
   ```

4. Install Vitest 1.0.0 for compatibility:
   ```cmd
   pnpm add -D vitest@1.0.0
   ```

5. Run tests:
   ```cmd
   pnpm test
   ```

### Option 2: Using NPM with Legacy Peer Dependencies

1. Clean existing node_modules:
   ```cmd
   rmdir /s /q node_modules
   ```

2. Install with legacy peer dependencies:
   ```cmd
   npm install --legacy-peer-deps
   ```

3. Run tests:
   ```cmd
   npm run test
   ```

### Option 3: Using NPM with Force Install

1. Clean existing node_modules:
   ```cmd
   rmdir /s /q node_modules
   ```

2. Install with force:
   ```cmd
   npm install --force
   ```

3. Run tests:
   ```cmd
   npm run test
   ```

## Database Setup

### 1. Create Test Database

1. Open PostgreSQL command line:
   ```cmd
   psql -U postgres
   ```

2. Create test database:
   ```sql
   CREATE DATABASE investment_auditor_test;
   ```

3. Create test user:
   ```sql
   CREATE USER test_user WITH PASSWORD 'test_password';
   ```

4. Grant privileges:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE investment_auditor_test TO test_user;
   ```

### 2. Configure Environment Variables

1. Copy environment file:
   ```cmd
   copy .env.example .env.test
   ```

2. Edit `.env.test` file with your database settings:
   ```env
   DATABASE_URL=postgresql://test_user:test_password@localhost:5432/investment_auditor_test
   NODE_ENV=test
   ```

## Running Tests

### Unit Tests
```cmd
pnpm test
```

### Integration Tests
```cmd
pnpm run test:integration
```

### E2E Tests

1. Install Playwright browsers:
   ```cmd
   pnpm exec playwright install
   ```

2. Run E2E tests:
   ```cmd
   pnpm run test:e2e
   ```

## Troubleshooting

### PNPM Not Found

If you get "pnpm is not recognized" error:

1. Check if PNPM is installed:
   ```cmd
   where pnpm
   ```

2. If not installed, install it:
   ```cmd
   npm install -g pnpm
   ```

3. Restart your terminal/command prompt

4. Verify installation:
   ```cmd
   pnpm --version
   ```

### Permission Issues

If you get permission errors:

1. Run as Administrator:
   - Right-click Command Prompt
   - Select "Run as administrator"

2. Or modify PowerShell execution policy:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Port Conflicts

If port 3000 is in use:

1. Find process using port:
   ```cmd
   netstat -ano | findstr :3000
   ```

2. Kill the process:
   ```cmd
   taskkill /PID <PID> /F
   ```

### PostgreSQL Connection Issues

1. Check if PostgreSQL is running:
   ```cmd
   netstat -ano | findstr :5432
   ```

2. Start PostgreSQL service:
   ```cmd
   net start postgresql-x64-15
   ```

## VS Code Integration

### Recommended Extensions

1. **Vitest**: For running and debugging tests
2. **Playwright Test Runner**: For E2E testing
3. **PostgreSQL**: For database management

### Test Runner Configuration

Add to `.vscode/settings.json`:
```json
{
  "vitest.enable": true,
  "vitest.commandLine": "pnpm test",
  "playwright.reuseBrowserServer": true
}
```

## Quick Start Script

Create a batch file `setup-testing.bat`:
```batch
@echo off
echo Setting up testing environment for Investment Auditor...

echo Installing PNPM globally...
npm install -g pnpm

echo Installing project dependencies...
pnpm install

echo Installing Vitest 1.0.0 for compatibility...
pnpm add -D vitest@1.0.0

echo Setting up test database...
psql -U postgres -c "CREATE DATABASE IF NOT EXISTS investment_auditor_test;"
psql -U postgres -c "CREATE USER IF NOT EXISTS test_user WITH PASSWORD 'test_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE investment_auditor_test TO test_user;"

echo Copying environment file...
copy .env.example .env.test

echo.
echo Testing environment is ready!
echo.
echo To run tests:
echo   pnpm test              - Run unit tests
echo   pnpm run test:integration - Run integration tests
echo   pnpm run test:e2e       - Run E2E tests
echo.
pause
```

Run this batch file to set up the entire testing environment.