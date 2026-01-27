/**
 * Authentication API Integration Tests
 * Tests the auth router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { eq } from 'drizzle-orm';
import { getTestDb, resetTestDb, seedTestDb } from '../../../../test-utils/database';
import { createTestCaller, createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users } from '@drizzle/schema';
import { registerUser, loginUser, createSessionToken } from '../../../_core/auth';

describe('Authentication API Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();
  });

  afterEach(async () => {
    // Cleanup is handled by resetTestDb in beforeEach
  });

  describe('User Registration', () => {
    it('should register a new user successfully', async () => {
      const caller = await createTestCaller();

      const result = await caller.auth.register({
        email: 'newuser@example.com',
        password: 'securepassword123',
        name: 'New User',
      });

      expect(result.success).toBe(true);
      expect(result.user).toBeDefined();
      expect(result.user.email).toBe('newuser@example.com');
      expect(result.user.name).toBe('New User');
      expect(result.user.role).toBe('user');

      // Verify user was created in database
      const [dbUser] = await db.select().from(users).where(eq(users.email, 'newuser@example.com'));
      expect(dbUser).toBeDefined();
      expect(dbUser.email).toBe('newuser@example.com');
    });

    it('should reject registration with invalid email', async () => {
      const caller = await createTestCaller();

      await expect(caller.auth.register({
        email: 'invalid-email',
        password: 'securepassword123',
        name: 'Test User',
      })).rejects.toThrow();
    });

    it('should reject registration with short password', async () => {
      const caller = await createTestCaller();

      await expect(caller.auth.register({
        email: 'test@example.com',
        password: 'short',
        name: 'Test User',
      })).rejects.toThrow();
    });

    it('should reject registration with duplicate email', async () => {
      const caller = await createTestCaller();

      // Register first user
      await caller.auth.register({
        email: 'duplicate@example.com',
        password: 'securepassword123',
        name: 'First User',
      });

      // Try to register with same email
      await expect(caller.auth.register({
        email: 'duplicate@example.com',
        password: 'anotherpassword123',
        name: 'Second User',
      })).rejects.toThrow();
    });

    it('should allow registration without name', async () => {
      const caller = await createTestCaller();

      const result = await caller.auth.register({
        email: 'noname@example.com',
        password: 'securepassword123',
      });

      expect(result.success).toBe(true);
      expect(result.user.name).toBeNull();
    });
  });

  describe('User Login', () => {
    beforeEach(async () => {
      // Create a test user for login tests
      const hashedPassword = await Bun.password.hash('password123', {
        algorithm: 'bcrypt',
        cost: 10,
      });

      await db.insert(users).values({
        openId: 'test-user-openid',
        email: 'login@example.com',
        passwordHash: hashedPassword,
        name: 'Login User',
        role: 'user',
      });
    });

    it('should login with valid credentials', async () => {
      const caller = await createTestCaller();

      const result = await caller.auth.login({
        email: 'login@example.com',
        password: 'password123',
      });

      expect(result.success).toBe(true);
      expect(result.user).toBeDefined();
      expect(result.user.email).toBe('login@example.com');
      expect(result.user.name).toBe('Login User');
    });

    it('should reject login with invalid email', async () => {
      const caller = await createTestCaller();

      await expect(caller.auth.login({
        email: 'nonexistent@example.com',
        password: 'password123',
      })).rejects.toThrow();
    });

    it('should reject login with invalid password', async () => {
      const caller = await createTestCaller();

      await expect(caller.auth.login({
        email: 'login@example.com',
        password: 'wrongpassword',
      })).rejects.toThrow();
    });
  });

  describe('User Session', () => {
    it('should return user info for authenticated session', async () => {
      const user = {
        id: 1,
        email: 'authenticated@example.com',
        name: 'Auth User',
        role: 'user',
      };

      const caller = await createAuthenticatedCaller(user);

      const result = await caller.auth.me();

      expect(result).toBeDefined();
      expect(result.email).toBe('authenticated@example.com');
      expect(result.name).toBe('Auth User');
      expect(result.role).toBe('user');
    });

    it('should return null for unauthenticated session', async () => {
      const caller = await createUnauthenticatedCaller();

      const result = await caller.auth.me();

      expect(result).toBeNull();
    });
  });

  describe('User Logout', () => {
    it('should logout successfully', async () => {
      const caller = await createTestCaller();

      const result = await caller.auth.logout();

      expect(result.success).toBe(true);
    });
  });

  describe('Session Token Creation', () => {
    it('should create valid session token for user', async () => {
      const [testUser] = await db.insert(users).values({
        openId: 'session-test-openid',
        email: 'session@example.com',
        name: 'Session User',
        role: 'user',
      }).returning();

      const sessionToken = await createSessionToken(testUser);

      expect(sessionToken).toBeDefined();
      expect(typeof sessionToken).toBe('string');
      expect(sessionToken.length).toBeGreaterThan(0);
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should complete full registration -> login -> access -> logout flow', async () => {
      const caller = await createTestCaller();

      // Step 1: Register
      const registerResult = await caller.auth.register({
        email: 'flowtest@example.com',
        password: 'flowpassword123',
        name: 'Flow Test User',
      });

      expect(registerResult.success).toBe(true);
      expect(registerResult.user.email).toBe('flowtest@example.com');

      // Step 2: Login (simulating new session)
      const loginResult = await caller.auth.login({
        email: 'flowtest@example.com',
        password: 'flowpassword123',
      });

      expect(loginResult.success).toBe(true);
      expect(loginResult.user.email).toBe('flowtest@example.com');

      // Step 3: Access protected resource with authenticated caller
      const authCaller = await createAuthenticatedCaller(loginResult.user);
      const meResult = await authCaller.auth.me();

      expect(meResult).toBeDefined();
      expect(meResult.email).toBe('flowtest@example.com');

      // Step 4: Logout
      const logoutResult = await caller.auth.logout();
      expect(logoutResult.success).toBe(true);
    });
  });
});
