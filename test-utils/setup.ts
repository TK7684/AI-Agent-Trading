import { beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { getTestDb, resetTestDb } from './database';

// Global test setup
beforeAll(async () => {
  // Set test environment variables
  process.env.NODE_ENV = 'test';
  process.env.DATABASE_URL = process.env.TEST_DATABASE_URL || 
    'postgresql://test_user:test_password@localhost:5432/investment_auditor_test';
  
  // Initialize test database
  await getTestDb();
});

beforeEach(async () => {
  // Reset database before each test
  await resetTestDb();
});

afterAll(async () => {
  // Cleanup after all tests
  // Close database connections if needed
});

// Global test utilities
global.testUtils = {
  // Add any global test utilities here
};