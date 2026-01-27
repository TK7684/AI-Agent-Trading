# Testing Troubleshooting Guide

This guide helps resolve common issues when setting up and running tests for Investment Auditor.

## Dependency Resolution Issues

### Problem: ERESOLVE dependency conflicts

If you encounter errors like:
```
npm error ERESOLVE could not resolve
npm error While resolving: @builder.io/vite-plugin-jsx-loc@0.1.1
npm error Found: vite@7.3.1
npm error node_modules/vite
npm error   dev vite@"^7.1.7" from the root project
npm error   peer vite@"^4.0.0 || ^5" from @tailwindcss/vite@4.1.18
npm error   node_modules/@tailwindcss/vite
npm error     dev @tailwindcss/vite@"^4.1.3" from the root project
npm error   1 more (@vitejs/plugin-react)
npm error   node_modules/vite
npm error   peer vite@"^4.0.0 || ^5.0.0" from @builder.io/vite-plugin-jsx-loc@0.1.1
```

### Solution 1: Use Legacy Peer Dependencies

```bash
npm install --legacy-peer-deps
```

### Solution 2: Use Force Install

```bash
npm install --force
```

### Solution 3: Update Vite Version

Update Vite to a compatible version (7.2.0+):

```bash
npm install vite@latest
```

### Solution 4: Use PNPM (Recommended)

The project is configured to use PNPM which handles peer dependencies better:

```bash
# Install pnpm if not already installed
npm install -g pnpm

# Install dependencies with pnpm
pnpm install

# Run tests with pnpm
pnpm test
```

## Database Connection Issues

### Problem: Test database connection fails

If you see errors like:
```
Error: connect ECONNREFUSED 127.0.0.1:5432
```

### Solution 1: Start PostgreSQL Service

```bash
# On Windows with PostgreSQL installed
net start postgresql-x64-15

# On macOS with Homebrew
brew services start postgresql

# On Linux with systemd
sudo systemctl start postgresql
```

### Solution 2: Create Test Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create test database
CREATE DATABASE investment_auditor_test;

# Create test user
CREATE USER test_user WITH PASSWORD 'test_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE investment_auditor_test TO test_user;
```

### Solution 3: Check .env.test Configuration

Ensure your `.env.test` file has correct database settings:

```env
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/investment_auditor_test
```

## Test Timeout Issues

### Problem: Tests timeout during execution

If tests are failing with timeout errors:

### Solution 1: Increase Test Timeout

Update test configuration to increase timeout:

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    testTimeout: 30000, // 30 seconds
    hookTimeout: 10000, // 10 seconds
  },
});
```

### Solution 2: Mock Slow Operations

Mock slow external API calls:

```typescript
// In your test file
vi.mock('undici', () => ({
  fetch: vi.fn().mockImplementation(() => 
    new Promise(resolve => setTimeout(() => resolve(mockResponse), 100))
  ),
}));
```

## Playwright Issues

### Problem: Browser not found

If you see errors like:
```
Error: Executable doesn't exist: /path/to/project/node_modules/.bin/playwright
```

### Solution: Install Playwright Browsers

```bash
npx playwright install
```

### Solution: Use Playwright with Docker

```bash
# Run tests in Docker container
docker run --rm -i --ipc --host-gateway=1 -v $(pwd):/work/ -w /work/ -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright mcr.microsoft.com/playwright:v1.40.0 npx playwright test
```

## TypeScript Issues

### Problem: Type errors in test files

If you see TypeScript errors like:
```
Cannot find module '../../../test-utils/mocks' or its corresponding type declarations.
```

### Solution: Update Module Resolution

Ensure correct relative paths in test files:

```typescript
// For server tests
import { mockFetch } from '../../../../test-utils/mocks';

// For client tests
import { render } from '@testing-library/react';
```

### Solution: Update tsconfig.json

Add test directories to TypeScript configuration:

```json
{
  "compilerOptions": {
    "types": ["vitest/globals"],
    "moduleResolution": "node",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/test/*": ["./test-utils/*"]
    }
  }
}
```

## Coverage Issues

### Problem: Coverage report not generated

If coverage reports are missing or incomplete:

### Solution 1: Update Vitest Configuration

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'test/',
        '**/*.test.ts',
        '**/*.spec.ts'
      ]
    }
  },
});
```

### Solution 2: Install Coverage Dependencies

```bash
npm install --save-dev @vitest/coverage-v8
```

## Common Test Failures

### Problem: Tests fail with "not implemented" errors

### Solution: Check Mock Implementation

Ensure all mocked functions are properly implemented:

```typescript
// Instead of this
vi.fn();

// Use this
vi.fn().mockReturnValue(expectedValue);
```

### Problem: Tests pass in isolation but fail together

### Solution: Check Test Isolation

Ensure tests are properly isolated:

```typescript
beforeEach(() => {
  vi.clearAllMocks();
});
```

## Running Specific Tests

### Run Only Unit Tests
```bash
npm run test -- server/**/*.test.ts
```

### Run Only Integration Tests
```bash
npm run test:integration
```

### Run Only E2E Tests
```bash
npm run test:e2e
```

### Run Tests for Specific File
```bash
npx vitest run server/__tests__/unit/services/githubAnalyzer.test.ts
```

## Performance Testing

### Problem: Tests are slow to run

### Solution: Use Test Parallelization

```bash
# Run tests in parallel
npx vitest run --threads
```

### Solution: Optimize Database Operations

Use transactions and batch operations in test setup:

```typescript
beforeEach(async () => {
  const db = await getTestDb();
  await db.transaction(async (tx) => {
    // Batch operations
    await tx.delete(schema.projects);
    await tx.delete(schema.users);
  });
});
```

## Getting Help

If you're still stuck:

1. Check the [Testing Guide](./TESTING_GUIDE.md) for detailed instructions
2. Review existing test files for examples
3. Check the [Quick Testing Guide](./QUICK_TESTING_GUIDE.md) for common commands
4. Search for similar issues in the project's GitHub issues
5. Ask for help in the project discussions

## Environment-Specific Issues

### Windows

- Use `npm.cmd` instead of `npm` in some cases
- Check for long path issues
- Verify PowerShell execution policy

### macOS

- Check Xcode command line tools installation
- Verify Homebrew installation
- Check for file permission issues

### Linux

- Verify package manager installation
- Check for missing system dependencies
- Verify Docker installation if using containers