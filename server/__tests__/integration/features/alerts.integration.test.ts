/**
 * Alerts Feature Integration Tests
 * Tests the alerts router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { eq, and } from 'drizzle-orm';
import { getTestDb, resetTestDb } from '../../../../test-utils/database';
import { createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users, projects, alertSettings } from '@drizzle/schema';

describe('Alerts Feature Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser: { id: number; email: string; name: string | null; role: string };
  let testProject: { id: number; name: string };

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-user-openid',
      email: 'alerts@example.com',
      name: 'Alerts User',
      role: 'user',
    }).returning();

    testUser = user;

    // Create a test project
    const [project] = await db.insert(projects).values({
      userId: testUser.id,
      name: 'Test Project for Alerts',
      githubUrl: 'https://github.com/user/alerts-test',
      status: 'completed',
    }).returning();

    testProject = project;
  });

  describe('Create Price Alert', () => {
    it('should create price above alert', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'above',
        targetPrice: 100,
      });

      expect(result.success).toBe(true);
      expect(result.alertId).toBeDefined();
    });

    it('should create price below alert', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'below',
        targetPrice: 50,
      });

      expect(result.success).toBe(true);
    });

    it('should require authentication to create price alert', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'above',
        targetPrice: 100,
      })).rejects.toThrow();
    });

    it('should validate target price is positive', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      await expect(caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'above',
        targetPrice: -10,
      })).rejects.toThrow();
    });
  });

  describe('Create Score Change Alert', () => {
    it('should create score increase alert', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.setScoreAlert({
        projectId: testProject.id,
        type: 'increase',
        threshold: 10,
      });

      expect(result.success).toBe(true);
      expect(result.alertId).toBeDefined();
    });

    it('should create score decrease alert', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.setScoreAlert({
        projectId: testProject.id,
        type: 'decrease',
        threshold: 15,
      });

      expect(result.success).toBe(true);
    });

    it('should require authentication to create score alert', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.alerts.setScoreAlert({
        projectId: testProject.id,
        type: 'increase',
        threshold: 10,
      })).rejects.toThrow();
    });

    it('should validate threshold is within valid range', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      await expect(caller.alerts.setScoreAlert({
        projectId: testProject.id,
        type: 'increase',
        threshold: 150, // Invalid: > 100
      })).rejects.toThrow();
    });
  });

  describe('Get User Alerts', () => {
    beforeEach(async () => {
      // Create test alerts
      await db.insert(alertSettings).values([
        {
          userId: testUser.id,
          projectId: testProject.id,
          alertType: 'price_above',
          targetPrice: 100,
          enabled: true,
        },
        {
          userId: testUser.id,
          projectId: testProject.id,
          alertType: 'score_increase',
          scoreThreshold: 10,
          enabled: true,
        },
      ]);
    });

    it('should get user alerts', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThanOrEqual(2);
    });

    it('should require authentication to list alerts', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.alerts.list()).rejects.toThrow();
    });

    it('should filter alerts by project', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.list({
        projectId: testProject.id,
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      // All alerts should be for the specified project
      result.forEach(alert => {
        expect(alert.projectId).toBe(testProject.id);
      });
    });

    it('should filter alerts by enabled status', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.list({
        enabled: true,
      });

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      result.forEach(alert => {
        expect(alert.enabled).toBe(true);
      });
    });
  });

  describe('Update Alert', () => {
    let alertId: number;

    beforeEach(async () => {
      const [alert] = await db.insert(alertSettings).values({
        userId: testUser.id,
        projectId: testProject.id,
        alertType: 'price_above',
        targetPrice: 100,
        enabled: true,
      }).returning();

      alertId = alert.id;
    });

    it('should update alert settings', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.update({
        alertId,
        targetPrice: 150,
        enabled: false,
      });

      expect(result.success).toBe(true);

      // Verify in database
      const [alert] = await db.select().from(alertSettings).where(
        eq(alertSettings.id, alertId)
      );

      expect(alert.targetPrice).toBe(150);
      expect(alert.enabled).toBe(false);
    });

    it('should require authentication to update alert', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.alerts.update({
        alertId,
        targetPrice: 200,
      })).rejects.toThrow();
    });

    it('should not allow updating other users alerts', async () => {
      // Create another user
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      // Try to update with different user
      const caller = await createAuthenticatedCaller(otherUser);

      await expect(caller.alerts.update({
        alertId,
        targetPrice: 200,
      })).rejects.toThrow();
    });
  });

  describe('Disable Alert', () => {
    let alertId: number;

    beforeEach(async () => {
      const [alert] = await db.insert(alertSettings).values({
        userId: testUser.id,
        projectId: testProject.id,
        alertType: 'price_below',
        targetPrice: 50,
        enabled: true,
      }).returning();

      alertId = alert.id;
    });

    it('should disable alert', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.alerts.disable({ alertId });

      expect(result.success).toBe(true);

      // Verify in database
      const [alert] = await db.select().from(alertSettings).where(
        eq(alertSettings.id, alertId)
      );

      expect(alert.enabled).toBe(false);
    });

    it('should require authentication to disable alert', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.alerts.disable({ alertId })).rejects.toThrow();
    });
  });

  describe('Alert Permissions', () => {
    it('should prevent users from accessing others alerts', async () => {
      // Create another user
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      // Create alert for first user
      await db.insert(alertSettings).values({
        userId: testUser.id,
        projectId: testProject.id,
        alertType: 'price_above',
        targetPrice: 100,
        enabled: true,
      });

      // Other user tries to access alerts
      const caller = await createAuthenticatedCaller(otherUser);

      const result = await caller.alerts.list();

      // Should not include first user's alerts
      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(0);
    });
  });

  describe('Alert Validation', () => {
    it('should reject invalid alert type', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      await expect(caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'invalid_type' as any,
        targetPrice: 100,
      })).rejects.toThrow();
    });

    it('should reject alerts for non-existent project', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      await expect(caller.alerts.setPriceAlert({
        projectId: 99999,
        type: 'above',
        targetPrice: 100,
      })).rejects.toThrow();
    });

    it('should reject duplicate alerts of same type', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      // Create first alert
      await caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'above',
        targetPrice: 100,
      });

      // Try to create duplicate
      await expect(caller.alerts.setPriceAlert({
        projectId: testProject.id,
        type: 'above',
        targetPrice: 100,
      })).rejects.toThrow();
    });
  });
});
