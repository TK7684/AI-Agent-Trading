/**
 * tRPC Integration Test Helpers
 * Provides utilities for testing tRPC routers with proper context
 */

import type { TrpcContext } from '../server/_core/context';
import { appRouter } from '../server/routers';
import { createCallerFactory } from '@trpc/server';
import { getTestDb } from './database';
import type { User } from '@drizzle/schema';

// Store the test db module reference to inject into routers
let testDbInstance: Awaited<ReturnType<typeof getTestDb>> | null = null;

/**
 * Set the test database instance to be used by tests
 * This is used to inject the test database into the router context
 */
export async function setupTestDatabase() {
  testDbInstance = await getTestDb();

  // Set environment variable for getDb() function
  if (!process.env.DATABASE_URL) {
    process.env.DATABASE_URL = process.env.TEST_DATABASE_URL ||
      'postgresql://test_user:test_password@localhost:5432/investment_auditor_test';
  }

  return testDbInstance;
}

/**
 * Get the current test database instance
 */
export function getTestDbInstance() {
  return testDbInstance;
}

/**
 * Create a test tRPC caller with minimal context for testing
 */
export async function createTestCaller(overrides?: Partial<TrpcContext>) {
  await setupTestDatabase();

  const context: TrpcContext = {
    req: {
      header: () => '',
    } as any,
    res: {
      cookie: () => {},
      clearCookie: () => {},
    } as any,
    user: null,
    ...overrides,
  };

  const createCaller = createCallerFactory();
  return createCaller(appRouter)(context);
}

/**
 * Create an authenticated test caller with a mock user
 */
export async function createAuthenticatedCaller(user: User) {
  await setupTestDatabase();

  const context: TrpcContext = {
    req: {
      header: () => '',
    } as any,
    res: {
      cookie: () => {},
      clearCookie: () => {},
    } as any,
    user,
  };

  const createCaller = createCallerFactory();
  return createCaller(appRouter)(context);
}

/**
 * Create an unauthenticated test caller
 */
export async function createUnauthenticatedCaller() {
  await setupTestDatabase();

  const context: TrpcContext = {
    req: {
      header: () => '',
    } as any,
    res: {
      cookie: () => {},
      clearCookie: () => {},
    } as any,
    user: null,
  };

  const createCaller = createCallerFactory();
  return createCaller(appRouter)(context);
}

/**
 * Type for test caller - inferred from appRouter
 */
export type TestCaller = Awaited<ReturnType<typeof createTestCaller>>;

/**
 * Helper to create a mock user object
 */
export function createMockUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    openId: 'test-open-id',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    createdAt: new Date(),
    updatedAt: new Date(),
    ...overrides,
  };
}
