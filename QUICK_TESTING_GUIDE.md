# Quick Testing Guide for Investment Auditor

This guide provides quick instructions to get started with testing the Investment Auditor system.

## Prerequisites

1. Install dependencies:
```bash
npm install
```

2. Set up test environment variables:
```bash
cp .env.example .env.test
# Edit .env.test with your test database credentials
```

3. Start test database (if using local PostgreSQL):
```bash
# Create test database
createdb investment_auditor_test

# Run migrations
npm run db:push
```

## Running Tests

### Unit Tests
```bash
# Run all unit tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Integration Tests
```bash
# Run all integration tests
npm run test:integration
```

### Frontend Component Tests
```bash
# Run component tests (if separated)
npm run test:components
```

### End-to-End Tests
```bash
# Install Playwright browsers
npx playwright install

# Run E2E tests
npm run test:e2e

# Run E2E tests in headed mode
npm run test:e2e:headed

# Debug E2E tests
npm run test:e2e:debug
```

## Test Structure

```
├── server/
│   └── __tests__/
│       ├── unit/           # Unit tests for server functions
│       └── integration/    # Integration tests for API endpoints
├── client/
│   └── __tests__/         # Component tests for React components
├── e2e/
│   └── tests/             # End-to-end tests with Playwright
└── test-utils/              # Shared testing utilities
```

## Writing New Tests

### Unit Test Example
```typescript
import { describe, it, expect } from 'vitest';
import { functionToTest } from '../path/to/function';

describe('Function Name', () => {
  it('should do something', () => {
    const result = functionToTest(input);
    expect(result).toBe(expectedOutput);
  });
});
```

### Integration Test Example
```typescript
import { describe, it, expect } from 'vitest';
import { trpcMsw } from 'trpc-msw';

describe('API Endpoint', () => {
  it('should return expected response', async () => {
    const response = await trpcMsw.api.endpoint.query();
    expect(response).toEqual(expectedData);
  });
});
```

### Component Test Example
```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Component from '../Component';

describe('Component', () => {
  it('should render correctly', () => {
    render(<Component />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

### E2E Test Example
```typescript
import { test, expect } from '@playwright/test';

test('user workflow', async ({ page }) => {
  await page.goto('/');
  await page.click('[data-testid=some-button]');
  await expect(page.locator('[data-testid=result]')).toBeVisible();
});
```

## Best Practices

1. **Test Naming**: Use descriptive test names that explain what is being tested
2. **AAA Pattern**: Structure tests with Arrange, Act, Assert phases
3. **Test Isolation**: Each test should be independent and not rely on other tests
4. **Mock External Dependencies**: Mock APIs, databases, and external services
5. **Test Coverage**: Aim for at least 80% code coverage for critical paths
6. **Use Test IDs**: Add `data-testid` attributes for reliable element selection

## Debugging Tests

### Unit/Integration Tests
```bash
# Run with Node.js inspector
node --inspect-brk node_modules/.bin/vitest run

# Or use Vitest UI
npm run test:ui
```

### E2E Tests
```bash
# Run in headed mode to see browser
npm run test:e2e:headed

# Debug with Playwright Inspector
npm run test:e2e:debug
```

## CI/CD Integration

Tests will automatically run on:
- Push to `main` or `develop` branches
- Pull requests to `main` branch

View test results in the Actions tab of your GitHub repository.

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Check test database exists
psql -h localhost -p 5432 -U test_user -d investment_auditor_test -c "\l"
```

### Port Conflicts
```bash
# Check if port 3000 is in use
lsof -i :3000

# Kill process using port
kill -9 <PID>
```

### Test Timeouts
- Increase timeout values in test configurations
- Check for async operations not being properly awaited
- Verify mock responses are correctly configured

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Playwright Testing](https://playwright.dev/)
- [tRPC Testing](https://trpc.io/docs/quickstart/introduction)