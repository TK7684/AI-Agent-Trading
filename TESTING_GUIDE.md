# Testing Guide for Investment Auditor

This guide provides comprehensive instructions on how to test the Investment Auditor system, including unit tests, integration tests, and end-to-end testing.

## Table of Contents

1. [Testing Setup](#testing-setup)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Unit Testing](#unit-testing)
5. [Integration Testing](#integration-testing)
6. [Frontend Testing](#frontend-testing)
7. [End-to-End Testing](#end-to-end-testing)
8. [Database Testing](#database-testing)
9. [CI/CD Integration](#cicd-integration)
10. [Best Practices](#best-practices)

## Testing Setup

### Prerequisites

- Node.js (v18 or higher)
- PostgreSQL (for integration tests)
- Docker (for containerized testing environment)

### Test Dependencies

The project already includes Vitest as the testing framework. Additional testing dependencies include:

```bash
# Install additional testing dependencies if needed
npm install --save-dev @testing-library/react @testing-library/jest-dom jsdom
```

### Environment Configuration

Create a test environment file:

```bash
# .env.test
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/investment_auditor_test
NODE_ENV=test
```

## Running Tests

### Basic Commands

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm run test server/services/githubAnalyzer.test.ts
```

### Test Scripts

Add these scripts to your `package.json`:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui",
    "test:integration": "vitest run --config vitest.integration.config.ts",
    "test:e2e": "playwright test"
  }
}
```

## Test Structure

```
├── server/
│   ├── __tests__/
│   │   ├── unit/
│   │   │   ├── services/
│   │   │   ├── db/
│   │   │   └── utils/
│   │   └── integration/
│   │       ├── api/
│   │       └── workflows/
├── client/
│   ├── __tests__/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
├── e2e/
│   ├── fixtures/
│   ├── page-objects/
│   └── tests/
└── test-utils/
    ├── database.ts
    ├── mocks.ts
    └── helpers.ts
```

## Unit Testing

### Server-Side Unit Tests

Example for testing the GitHub analyzer service:

```typescript
// server/__tests__/unit/services/githubAnalyzer.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { analyzeGitHub } from '../../../services/githubAnalyzer';
import { fetch } from 'undici';

// Mock the fetch function
vi.mock('undici');

describe('GitHub Analyzer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should analyze a valid GitHub repository', async () => {
    const mockRepoData = {
      name: 'test-repo',
      stargazers_count: 100,
      forks_count: 50,
      open_issues_count: 10,
      language: 'TypeScript',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-12-01T00:00:00Z',
    };

    const mockCommits = [
      { sha: 'abc123', commit: { author: { date: '2023-12-01T00:00:00Z' } } },
      { sha: 'def456', commit: { author: { date: '2023-11-01T00:00:00Z' } } },
    ];

    // Mock API responses
    (fetch as any).mockResolvedValueOnce({
      json: async () => mockRepoData,
    }).mockResolvedValueOnce({
      json: async () => mockCommits,
    });

    const result = await analyzeGitHub('https://github.com/user/test-repo');

    expect(result).toBeDefined();
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(100);
    expect(result.data.repository).toEqual(mockRepoData);
  });

  it('should handle invalid GitHub URLs', async () => {
    await expect(analyzeGitHub('invalid-url')).rejects.toThrow();
  });
});
```

### Database Unit Tests

Example for testing database functions:

```typescript
// server/__tests__/unit/db/projects.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getDb } from '../../../db';
import { createProject, getProjectById, getProjectsByUserId } from '../../../db';
import { projects } from '../../../drizzle/schema';
import { eq } from 'drizzle-orm';

describe('Project Database Operations', () => {
  let db: any;
  let testUserId: number;

  beforeEach(async () => {
    db = await getDb();
    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-open-id',
      email: 'test@example.com',
    }).returning();
    testUserId = user.id;
  });

  afterEach(async () => {
    // Clean up test data
    await db.delete(projects).where(eq(projects.userId, testUserId));
    await db.delete(users).where(eq(users.id, testUserId));
  });

  it('should create a new project', async () => {
    const projectData = {
      userId: testUserId,
      name: 'Test Project',
      description: 'A test project',
      githubUrl: 'https://github.com/user/test-repo',
    };

    const projectId = await createProject(projectData);
    expect(projectId).toBeDefined();
    expect(typeof projectId).toBe('number');

    const project = await getProjectById(projectId);
    expect(project).toMatchObject(projectData);
  });

  it('should retrieve projects by user ID', async () => {
    // Create multiple projects
    await createProject({ userId: testUserId, name: 'Project 1' });
    await createProject({ userId: testUserId, name: 'Project 2' });

    const userProjects = await getProjectsByUserId(testUserId);
    expect(userProjects).toHaveLength(2);
    expect(userProjects[0].userId).toBe(testUserId);
  });
});
```

## Integration Testing

### API Endpoint Tests

Example for testing tRPC endpoints:

```typescript
// server/__tests__/integration/api/auth.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createTRPCMsw } from 'trpc-msw';
import { setupServer } from 'msw/node';
import { appRouter } from '../../../routers';
import { db } from '../../test-utils/database';

const trpcMsw = createTRPCMsw<typeof appRouter>();
const server = setupServer(...trpcMsw.handlers);

describe('Authentication API', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('should register a new user', async () => {
    const userData = {
      email: 'test@example.com',
      password: 'password123',
      name: 'Test User',
    };

    const response = await trpcMsw.auth.register.mutate(userData);

    expect(response.success).toBe(true);
    expect(response.user.email).toBe(userData.email);
    expect(response.user.name).toBe(userData.name);
  });

  it('should login with valid credentials', async () => {
    // First register a user
    const userData = {
      email: 'test@example.com',
      password: 'password123',
      name: 'Test User',
    };
    await trpcMsw.auth.register.mutate(userData);

    // Then login
    const loginData = {
      email: userData.email,
      password: userData.password,
    };

    const response = await trpcMsw.auth.login.mutate(loginData);

    expect(response.success).toBe(true);
    expect(response.user.email).toBe(userData.email);
  });
});
```

## Frontend Testing

### React Component Tests

Example for testing a React component:

```typescript
// client/__tests__/components/Auth/LoginPage.test.tsx
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from '../../../pages/Auth/LoginPage';

// Mock the trpc client
vi.mock('../../../lib/trpc', () => ({
  trpc: {
    auth: {
      login: {
        useMutation: () => ({
          mutateAsync: vi.fn().mockResolvedValue({
            success: true,
            user: { id: 1, email: 'test@example.com', name: 'Test User' },
          }),
          isLoading: false,
        }),
      },
    },
  },
}));

describe('LoginPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderLoginPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    );
  };

  it('should render login form', () => {
    renderLoginPage();

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('should show validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const loginButton = screen.getByRole('button', { name: /login/i });
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('should submit form with valid data', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(loginButton);

    // Verify the mutation was called (mocked above)
    await waitFor(() => {
      expect(screen.getByText(/login successful/i)).toBeInTheDocument();
    });
  });
});
```

## End-to-End Testing

### Playwright E2E Tests

Example for testing the complete user workflow:

```typescript
// e2e/tests/project-audit.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Project Audit Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid=email-input]', 'test@example.com');
    await page.fill('[data-testid=password-input]', 'password123');
    await page.click('[data-testid=login-button]');
    await expect(page.locator('[data-testid=dashboard]')).toBeVisible();
  });

  test('should complete full project audit workflow', async ({ page }) => {
    // Navigate to new project page
    await page.click('[data-testid=new-project-button]');
    await expect(page.locator('[data-testid=new-project-form]')).toBeVisible();

    // Fill project details
    await page.fill('[data-testid=project-name]', 'Test Project');
    await page.fill('[data-testid=project-description]', 'A test project for audit');
    await page.fill('[data-testid=github-url]', 'https://github.com/user/test-repo');
    await page.fill('[data-testid=contract-address]', '0x1234567890123456789012345678901234567890');
    await page.selectOption('[data-testid=chain-select]', 'ethereum');

    // Submit project
    await page.click('[data-testid=create-project-button]');
    await expect(page.locator('[data-testid=project-created-message]')).toBeVisible();

    // Start analysis
    await page.click('[data-testid=analyze-button]');
    await expect(page.locator('[data-testid=analysis-progress]')).toBeVisible();

    // Wait for analysis to complete
    await expect(page.locator('[data-testid=analysis-results]')).toBeVisible({ timeout: 30000 });

    // Verify results
    await expect(page.locator('[data-testid=overall-score]')).toBeVisible();
    await expect(page.locator('[data-testid=risk-level]')).toBeVisible();
    await expect(page.locator('[data-testid=github-score]')).toBeVisible();
    await expect(page.locator('[data-testid=tokenomics-score]')).toBeVisible();
  });

  test('should handle project comparison', async ({ page }) => {
    // Create first project
    await createProject(page, 'Project 1', 'https://github.com/user/repo1');
    
    // Create second project
    await createProject(page, 'Project 2', 'https://github.com/user/repo2');

    // Navigate to comparison page
    await page.click('[data-testid=comparison-tab]');
    await page.click('[data-testid=new-comparison-button]');

    // Select projects to compare
    await page.check('[data-testid=project-1-checkbox]');
    await page.check('[data-testid=project-2-checkbox]');
    await page.fill('[data-testid=comparison-name]', 'Test Comparison');
    await page.click('[data-testid=create-comparison-button]');

    // Verify comparison results
    await expect(page.locator('[data-testid=comparison-table]')).toBeVisible();
    await expect(page.locator('[data-testid=comparison-chart]')).toBeVisible();
  });
});

async function createProject(page: any, name: string, githubUrl: string) {
  await page.click('[data-testid=new-project-button]');
  await page.fill('[data-testid=project-name]', name);
  await page.fill('[data-testid=github-url]', githubUrl);
  await page.click('[data-testid=create-project-button]');
  await expect(page.locator('[data-testid=project-created-message]')).toBeVisible();
}
```

## Database Testing

### Test Database Setup

Create test utilities for database operations:

```typescript
// test-utils/database.ts
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import * as schema from '../../drizzle/schema';

let testDb: ReturnType<typeof drizzle> | null = null;

export async function getTestDb() {
  if (!testDb) {
    const connectionString = process.env.TEST_DATABASE_URL || 
      'postgresql://test_user:test_password@localhost:5432/investment_auditor_test';
    
    const client = postgres(connectionString);
    testDb = drizzle(client, { schema });
    
    // Run migrations
    await migrate(testDb, { migrationsFolder: './drizzle' });
  }
  
  return testDb;
}

export async function resetTestDb() {
  const db = await getTestDb();
  
  // Delete all data in correct order (respect foreign keys)
  await db.delete(schema.auditReports);
  await db.delete(schema.projects);
  await db.delete(schema.users);
}

export async function seedTestDb() {
  const db = await getTestDb();
  
  // Create test users
  const [testUser] = await db.insert(schema.users).values({
    openId: 'test-open-id',
    email: 'test@example.com',
    name: 'Test User',
  }).returning();
  
  // Create test projects
  const [testProject] = await db.insert(schema.projects).values({
    userId: testUser.id,
    name: 'Test Project',
    description: 'A test project',
    githubUrl: 'https://github.com/user/test-repo',
  }).returning();
  
  return { testUser, testProject };
}
```

## CI/CD Integration

### GitHub Actions Workflow

Create a CI pipeline for automated testing:

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_USER: test_user
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
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Setup test database
      run: |
        npm run db:migrate:test
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/investment_auditor_test
    
    - name: Run unit tests
      run: npm run test:unit
    
    - name: Run integration tests
      run: npm run test:integration
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/investment_auditor_test
    
    - name: Run E2E tests
      run: npm run test:e2e
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/investment_auditor_test
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage/lcov.info
```

## Best Practices

### General Testing Guidelines

1. **Test Pyramid**: Focus on unit tests (70%), integration tests (20%), and E2E tests (10%)
2. **Test Naming**: Use descriptive test names that explain what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
4. **Test Isolation**: Each test should be independent and not rely on other tests
5. **Mock External Dependencies**: Mock APIs, databases, and other external services

### Code Coverage

- Aim for at least 80% code coverage for critical paths
- Focus on testing business logic and error handling
- Use coverage reports to identify untested code

### Performance Testing

- Include performance tests for critical API endpoints
- Test database query performance with realistic data volumes
- Monitor memory usage and response times

### Security Testing

- Test authentication and authorization mechanisms
- Validate input sanitization and SQL injection prevention
- Test rate limiting and DDoS protection

## Troubleshooting

### Common Issues

1. **Database Connection Errors**: Ensure test database is running and accessible
2. **Timeout Issues**: Increase timeout values for integration and E2E tests
3. **Mock Failures**: Verify mocks are properly configured and reset between tests
4. **Environment Variables**: Check that test environment variables are correctly set

### Debugging Tests

- Use `console.log` or Vitest's built-in debugging features
- Run tests with `--inspect` flag for Node.js debugging
- Use browser dev tools for E2E test debugging

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Playwright Testing](https://playwright.dev/)
- [Drizzle ORM Testing](https://orm.drizzle.team/docs/goodies/testing)