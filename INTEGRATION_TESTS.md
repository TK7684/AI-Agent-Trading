# Integration Tests Guide

This document explains how to set up and run integration tests for the Investment Auditor project.

## Overview

Integration tests test the interaction between different components of the system, including:
- API endpoints (tRPC routers)
- Database operations
- Authentication and authorization
- Business logic workflows

Integration tests differ from unit tests in that they:
- Use a real test database (PostgreSQL)
- Test multiple components working together
- Make actual API calls through tRPC routers
- Verify data persistence and retrieval

## Prerequisites

### 1. PostgreSQL Database

Integration tests require a PostgreSQL test database. You can either:

#### Option A: Use Docker (Recommended)

```bash
docker run -d \
  --name investment-auditor-test-db \
  -e POSTGRES_USER=test_user \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=investment_auditor_test \
  -p 5433:5432 \
  postgres:16
```

Then set the environment variable:
```bash
export TEST_DATABASE_URL="postgresql://test_user:test_password@localhost:5433/investment_auditor_test"
```

#### Option B: Use Local PostgreSQL

Create a test database manually:
```bash
psql -U postgres
CREATE DATABASE investment_auditor_test;
CREATE USER test_user WITH PASSWORD 'test_password';
GRANT ALL PRIVILEGES ON DATABASE investment_auditor_test TO test_user;
```

Then set the environment variable:
```bash
export TEST_DATABASE_URL="postgresql://test_user:test_password@localhost:5432/investment_auditor_test"
```

### 2. Run Database Migrations

Before running tests for the first time, run the migrations on the test database:

```bash
DATABASE_URL="$TEST_DATABASE_URL" pnpm db:push
```

## Running Integration Tests

### Run All Integration Tests

```bash
pnpm test:integration
```

### Run Specific Integration Test Files

```bash
# Auth integration tests
pnpm test:integration auth.integration.test.ts

# Projects integration tests
pnpm test:integration projects.integration.test.ts

# Watchlist feature tests
pnpm test:integration watchlist.integration.test.ts
```

### Run Integration Tests in Watch Mode

```bash
vitest --config vitest.integration.config.ts
```

### Run Integration Tests with Coverage

```bash
vitest run --config vitest.integration.config.ts --coverage
```

## Test Structure

```
server/__tests__/
├── integration/
│   ├── api/
│   │   ├── auth.integration.test.ts       # Authentication API tests
│   │   └── projects.integration.test.ts   # Projects CRUD tests
│   ├── features/
│   │   ├── watchlist.integration.test.ts  # Watchlist feature tests
│   │   ├── comparison.integration.test.ts # Comparison feature tests
│   │   └── alerts.integration.test.ts     # Alerts feature tests
│   └── services/
│       └── discovery.integration.test.ts  # Discovery service tests
```

## Test Utilities

### Test Helpers

Located in `test-utils/`:

- `database.ts` - Test database setup, seeding, and utilities
- `trpc.ts` - tRPC caller creation for testing routers
- `mocks.ts` - Mock configurations

### Key Test Utilities

```typescript
import {
  getTestDb,
  resetTestDb,
  seedTestDb
} from '../../test-utils/database';

import {
  createTestCaller,
  createAuthenticatedCaller,
  createUnauthenticatedCaller
} from '../../test-utils/trpc';
```

## Writing Integration Tests

### Basic Template

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { getTestDb, resetTestDb } from '../../../../test-utils/database';
import { createAuthenticatedCaller } from '../../../../test-utils/trpc';
import { users } from '@drizzle/schema';

describe('My Feature Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser;

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create test user
    const [user] = await db.insert(users).values({
      openId: 'test-openid',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user',
    }).returning();

    testUser = user;
  });

  it('should test something', async () => {
    const caller = await createAuthenticatedCaller(testUser);

    // Call tRPC procedure
    const result = await caller.myFeature.myProcedure({
      // input
    });

    // Assert
    expect(result).toBeDefined();
  });
});
```

### Testing Authentication

```typescript
// Authenticated call
const authCaller = await createAuthenticatedCaller(testUser);
const result = await authCaller.project.create({ /* ... */ });

// Unauthenticated call (should fail)
const unauthCaller = await createUnauthenticatedCaller();
await expect(unauthCaller.project.create({ /* ... */ })).rejects.toThrow();
```

### Testing Database Operations

```typescript
// Create data
const [project] = await db.insert(projects).values({
  userId: testUser.id,
  name: 'Test Project',
  // ...
}).returning();

// Query data
const [retrieved] = await db.select()
  .from(projects)
  .where(eq(projects.id, project.id));

// Update data
await db.update(projects)
  .set({ name: 'Updated' })
  .where(eq(projects.id, project.id));

// Delete data
await db.delete(projects)
  .where(eq(projects.id, project.id));
```

### Mocking External Services

```typescript
import { vi } from 'vitest';

vi.mock('../../../services/githubAnalyzer', () => ({
  analyzeGitHub: vi.fn(() => Promise.resolve({
    score: 75,
    data: { /* ... */ },
    analysis: 'Mock analysis',
  })),
}));
```

## Current Test Coverage

### Authentication API (`auth.integration.test.ts`)
- ✅ User registration
- ✅ User login
- ✅ Session management
- ✅ Logout
- ✅ Token creation
- ✅ Full authentication flow

### Projects API (`projects.integration.test.ts`)
- ✅ Project creation
- ✅ Project retrieval (list and by ID)
- ✅ Project analysis
- ✅ Permission checks
- ✅ Error handling

### Watchlist Feature (`watchlist.integration.test.ts`)
- ✅ Add to watchlist
- ✅ Remove from watchlist
- ✅ List watchlist
- ✅ Check if in watchlist
- ✅ Permission checks

### Comparison Feature (`comparison.integration.test.ts`)
- ✅ Create comparison
- ✅ List comparisons
- ✅ Get comparison by ID
- ✅ Update comparison
- ✅ Delete comparison
- ✅ Permission checks

### Alerts Feature (`alerts.integration.test.ts`)
- ✅ Create price alerts
- ✅ Create score alerts
- ✅ List alerts
- ✅ Update alerts
- ✅ Disable alerts
- ✅ Permission checks
- ✅ Validation

### Discovery Service (`discovery.integration.test.ts`)
- ✅ Fetch trending projects
- ✅ Filter by category/status/score
- ✅ Get categories
- ✅ Get project details
- ✅ Caching behavior
- ✅ Error handling

## Troubleshooting

### Database Connection Issues

If you see "connection refused" errors:
1. Check PostgreSQL is running: `docker ps` or `psql -l`
2. Verify TEST_DATABASE_URL is set correctly
3. Ensure the test database exists

### Migration Errors

If tests fail due to missing tables:
```bash
DATABASE_URL="$TEST_DATABASE_URL" pnpm db:push
```

### Port Already in Use

If PostgreSQL port 5432 is already in use:
1. Use a different port in Docker: `-p 5433:5432`
2. Update TEST_DATABASE_URL to use port 5433

### Tests Timing Out

Increase timeout in `vitest.integration.config.ts`:
```typescript
testTimeout: 60000, // 60 seconds
```

## Continuous Integration

Integration tests can run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: investment_auditor_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: pnpm install

      - name: Setup database
        run: |
          pnpm db:push
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/investment_auditor_test

      - name: Run integration tests
        run: pnpm test:integration
        env:
          TEST_DATABASE_URL: postgresql://test_user:test_password@localhost:5432/investment_auditor_test
```

## Best Practices

1. **Isolation**: Each test should be independent. Use `beforeEach` to reset database state.
2. **Cleanup**: Always clean up created data in `afterEach` if needed.
3. **Mock External Services**: Use mocks for external APIs (GitHub, CoinGecko, etc.).
4. **Test Both Success and Failure**: Test both happy paths and error cases.
5. **Use Descriptive Names**: Make test names describe what they're testing.
6. **Assert Database State**: Verify data was actually persisted/modified.
7. **Test Permissions**: Ensure authorization checks work correctly.

## Contributing

When adding new features:
1. Add integration tests alongside the feature
2. Test all CRUD operations
3. Test permission checks
4. Test error cases
5. Update this README with new test files

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [tRPC Testing Guide](https://trpc.io/docs/server/testing)
- [Drizzle ORM Testing](https://orm.drizzle.team/docs/overview)
- [Testing Library](https://testing-library.com/)
