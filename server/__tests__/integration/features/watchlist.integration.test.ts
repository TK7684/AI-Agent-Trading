/**
 * Watchlist Feature Integration Tests
 * Tests the watchlist router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { eq, and } from 'drizzle-orm';
import { getTestDb, resetTestDb } from '../../../../test-utils/database';
import { createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users, projects, watchlist } from '@drizzle/schema';

describe('Watchlist Feature Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser: { id: number; email: string; name: string | null; role: string };
  let testProject: { id: number; name: string };

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-user-openid',
      email: 'watchlist@example.com',
      name: 'Watchlist User',
      role: 'user',
    }).returning();

    testUser = user;

    // Create a test project
    const [project] = await db.insert(projects).values({
      userId: testUser.id,
      name: 'Test Project for Watchlist',
      githubUrl: 'https://github.com/user/watchlist-test',
      status: 'completed',
    }).returning();

    testProject = project;
  });

  describe('Add to Watchlist', () => {
    it('should add project to watchlist', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.watchlist.add({
        projectId: testProject.id,
        notes: 'Interesting project to monitor',
      });

      expect(result.success).toBe(true);

      // Verify in database
      const [watchItem] = await db.select().from(watchlist).where(
        and(
          eq(watchlist.userId, testUser.id),
          eq(watchlist.projectId, testProject.id)
        )
      );

      expect(watchItem).toBeDefined();
      expect(watchItem.notes).toBe('Interesting project to monitor');
    });

    it('should require authentication to add to watchlist', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.watchlist.add({
        projectId: testProject.id,
      })).rejects.toThrow();
    });

    it('should not add duplicate entries to watchlist', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      // Add once
      await caller.watchlist.add({ projectId: testProject.id });

      // Try to add again - should handle gracefully
      const result = await caller.watchlist.add({ projectId: testProject.id });

      expect(result).toBeDefined();
    });
  });

  describe('Remove from Watchlist', () => {
    beforeEach(async () => {
      // Add project to watchlist
      await db.insert(watchlist).values({
        userId: testUser.id,
        projectId: testProject.id,
        notes: 'Test note',
      });
    });

    it('should remove project from watchlist', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.watchlist.remove({
        projectId: testProject.id,
      });

      expect(result.success).toBe(true);

      // Verify removed from database
      const [watchItem] = await db.select().from(watchlist).where(
        and(
          eq(watchlist.userId, testUser.id),
          eq(watchlist.projectId, testProject.id)
        )
      );

      expect(watchItem).toBeUndefined();
    });

    it('should require authentication to remove from watchlist', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.watchlist.remove({
        projectId: testProject.id,
      })).rejects.toThrow();
    });
  });

  describe('Get User Watchlist', () => {
    beforeEach(async () => {
      // Add multiple projects to watchlist
      const [project1] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'Watchlist Project 1',
        githubUrl: 'https://github.com/user/wl1',
        status: 'completed',
      }).returning();

      const [project2] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'Watchlist Project 2',
        githubUrl: 'https://github.com/user/wl2',
        status: 'completed',
      }).returning();

      await db.insert(watchlist).values([
        { userId: testUser.id, projectId: project1.id, notes: 'Note 1' },
        { userId: testUser.id, projectId: project2.id, notes: 'Note 2' },
      ]);
    });

    it('should get user watchlist', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.watchlist.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(2);
      expect(result[0]).toHaveProperty('project');
      expect(result[0]).toHaveProperty('notes');
    });

    it('should require authentication to get watchlist', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.watchlist.list()).rejects.toThrow();
    });

    it('should return empty array for users with no watchlist items', async () => {
      // Create a user without any watchlist items
      const [newUser] = await db.insert(users).values({
        openId: 'new-user-openid',
        email: 'newuser@example.com',
        name: 'New User',
        role: 'user',
      }).returning();

      const caller = await createAuthenticatedCaller(newUser);

      const result = await caller.watchlist.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(0);
    });
  });

  describe('Check if Project is in Watchlist', () => {
    it('should return true if project is in watchlist', async () => {
      // Add to watchlist
      await db.insert(watchlist).values({
        userId: testUser.id,
        projectId: testProject.id,
      });

      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.watchlist.check({
        projectId: testProject.id,
      });

      expect(result.isInWatchlist).toBe(true);
    });

    it('should return false if project is not in watchlist', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.watchlist.check({
        projectId: testProject.id,
      });

      expect(result.isInWatchlist).toBe(false);
    });

    it('should require authentication to check watchlist status', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.watchlist.check({
        projectId: testProject.id,
      })).rejects.toThrow();
    });
  });

  describe('Watchlist Permissions', () => {
    it('should prevent users from accessing others watchlists', async () => {
      // Create another user
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      // Add project to first user's watchlist
      await db.insert(watchlist).values({
        userId: testUser.id,
        projectId: testProject.id,
        notes: 'Private note',
      });

      // Other user tries to access
      const otherCaller = await createAuthenticatedCaller(otherUser);

      const result = await otherCaller.watchlist.check({
        projectId: testProject.id,
      });

      // Should not be in other user's watchlist
      expect(result.isInWatchlist).toBe(false);
    });
  });
});
