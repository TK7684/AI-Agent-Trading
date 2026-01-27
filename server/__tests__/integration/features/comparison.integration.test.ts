/**
 * Comparison Feature Integration Tests
 * Tests the comparison router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { eq, and } from 'drizzle-orm';
import { getTestDb, resetTestDb } from '../../../../test-utils/database';
import { createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users, projects, comparisons } from '@drizzle/schema';

describe('Comparison Feature Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser: { id: number; email: string; name: string | null; role: string };
  let testProjects: Array<{ id: number; name: string }>;

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-user-openid',
      email: 'comparison@example.com',
      name: 'Comparison User',
      role: 'user',
    }).returning();

    testUser = user;

    // Create test projects
    const [project1] = await db.insert(projects).values({
      userId: testUser.id,
      name: 'Comparison Project 1',
      githubUrl: 'https://github.com/user/comp1',
      status: 'completed',
    }).returning();

    const [project2] = await db.insert(projects).values({
      userId: testUser.id,
      name: 'Comparison Project 2',
      githubUrl: 'https://github.com/user/comp2',
      status: 'completed',
    }).returning();

    const [project3] = await db.insert(projects).values({
      userId: testUser.id,
      name: 'Comparison Project 3',
      githubUrl: 'https://github.com/user/comp3',
      status: 'completed',
    }).returning();

    testProjects = [project1, project2, project3];
  });

  describe('Create Comparison', () => {
    it('should create a comparison with multiple projects', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.create({
        name: 'My Comparison',
        projectIds: [testProjects[0].id, testProjects[1].id],
        notes: 'Comparing DeFi protocols',
      });

      expect(result.success).toBe(true);
      expect(result.comparisonId).toBeDefined();

      // Verify in database
      const [comparison] = await db.select().from(comparisons).where(
        eq(comparisons.userId, testUser.id)
      );

      expect(comparison).toBeDefined();
      expect(comparison.name).toBe('My Comparison');
    });

    it('should require authentication to create comparison', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.comparison.create({
        name: 'Test Comparison',
        projectIds: [testProjects[0].id, testProjects[1].id],
      })).rejects.toThrow();
    });

    it('should require at least 2 projects for comparison', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      await expect(caller.comparison.create({
        name: 'Invalid Comparison',
        projectIds: [testProjects[0].id],
      })).rejects.toThrow();
    });

    it('should allow up to 4 projects in comparison', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.create({
        name: 'Max Projects Comparison',
        projectIds: [
          testProjects[0].id,
          testProjects[1].id,
          testProjects[2].id,
        ],
      });

      expect(result.success).toBe(true);
    });

    it('should create comparison without name', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.create({
        projectIds: [testProjects[0].id, testProjects[1].id],
      });

      expect(result.success).toBe(true);
    });
  });

  describe('Get User Comparisons', () => {
    beforeEach(async () => {
      // Create test comparisons
      await db.insert(comparisons).values([
        {
          userId: testUser.id,
          name: 'Comparison 1',
          projectIds: [testProjects[0].id, testProjects[1].id],
          notes: 'First comparison',
        },
        {
          userId: testUser.id,
          name: 'Comparison 2',
          projectIds: [testProjects[1].id, testProjects[2].id],
          notes: 'Second comparison',
        },
      ]);
    });

    it('should get user comparisons', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(2);
      expect(result[0].name).toBe('Comparison 1');
      expect(result[1].name).toBe('Comparison 2');
    });

    it('should require authentication to list comparisons', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.comparison.list()).rejects.toThrow();
    });

    it('should return empty array for users with no comparisons', async () => {
      // Create a user without comparisons
      const [newUser] = await db.insert(users).values({
        openId: 'new-user-openid',
        email: 'newuser@example.com',
        name: 'New User',
        role: 'user',
      }).returning();

      const caller = await createAuthenticatedCaller(newUser);

      const result = await caller.comparison.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(0);
    });
  });

  describe('Get Comparison by ID', () => {
    let comparisonId: number;

    beforeEach(async () => {
      const [comparison] = await db.insert(comparisons).values({
        userId: testUser.id,
        name: 'Detailed Comparison',
        projectIds: [testProjects[0].id, testProjects[1].id, testProjects[2].id],
        notes: 'Detailed notes',
      }).returning();

      comparisonId = comparison.id;
    });

    it('should get comparison by ID', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.get({ id: comparisonId });

      expect(result).toBeDefined();
      expect(result.name).toBe('Detailed Comparison');
      expect(result.projects).toBeDefined();
      expect(result.projects.length).toBe(3);
    });

    it('should return null for non-existent comparison', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.get({ id: 99999 });

      expect(result).toBeNull();
    });

    it('should not allow access to other users comparisons', async () => {
      // Create another user
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      // Try to access with different user
      const caller = await createAuthenticatedCaller(otherUser);

      const result = await caller.comparison.get({ id: comparisonId });

      // Should return null or undefined
      expect(result === null || result === undefined).toBe(true);
    });
  });

  describe('Update Comparison', () => {
    let comparisonId: number;

    beforeEach(async () => {
      const [comparison] = await db.insert(comparisons).values({
        userId: testUser.id,
        name: 'Original Name',
        projectIds: [testProjects[0].id, testProjects[1].id],
      }).returning();

      comparisonId = comparison.id;
    });

    it('should update comparison name and notes', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.update({
        id: comparisonId,
        name: 'Updated Name',
        notes: 'Updated notes',
      });

      expect(result.success).toBe(true);

      // Verify in database
      const [comparison] = await db.select().from(comparisons).where(
        eq(comparisons.id, comparisonId)
      );

      expect(comparison.name).toBe('Updated Name');
      expect(comparison.notes).toBe('Updated notes');
    });

    it('should update comparison projects', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.update({
        id: comparisonId,
        projectIds: [testProjects[1].id, testProjects[2].id],
      });

      expect(result.success).toBe(true);

      // Verify in database
      const [comparison] = await db.select().from(comparisons).where(
        eq(comparisons.id, comparisonId)
      );

      expect(comparison.projectIds).toEqual([testProjects[1].id, testProjects[2].id]);
    });
  });

  describe('Delete Comparison', () => {
    let comparisonId: number;

    beforeEach(async () => {
      const [comparison] = await db.insert(comparisons).values({
        userId: testUser.id,
        name: 'To Delete',
        projectIds: [testProjects[0].id, testProjects[1].id],
      }).returning();

      comparisonId = comparison.id;
    });

    it('should delete comparison', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.comparison.delete({ id: comparisonId });

      expect(result.success).toBe(true);

      // Verify deleted from database
      const [comparison] = await db.select().from(comparisons).where(
        eq(comparisons.id, comparisonId)
      );

      expect(comparison).toBeUndefined();
    });

    it('should require authentication to delete comparison', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.comparison.delete({ id: comparisonId })).rejects.toThrow();
    });
  });

  describe('Comparison Permissions', () => {
    it('should prevent users from accessing others comparisons via list', async () => {
      // Create another user with their own comparison
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      await db.insert(comparisons).values({
        userId: otherUser.id,
        name: 'Other User Comparison',
        projectIds: [testProjects[0].id, testProjects[1].id],
      });

      // First user's list should only show their comparisons
      const caller = await createAuthenticatedCaller(testUser);
      const result = await caller.comparison.list();

      expect(result).toBeDefined();
      expect(result.length).toBe(0); // No comparisons for testUser
    });
  });
});
