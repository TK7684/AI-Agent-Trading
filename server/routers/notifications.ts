/**
 * Notifications Router
 * Handles in-app notifications for users
 */

import { z } from 'zod';
import { eq, and } from 'drizzle-orm';
import { publicProcedure, protectedProcedure, router } from '../_core/trpc';
import { notifications } from '@drizzle/schema';

async function getDb() {
  const { getDb } = await import('../db');
  return getDb();
}

export const notificationsRouter = router({
  // Get user notifications
  list: protectedProcedure
    .input(z.object({
      unreadOnly: z.boolean().optional().default(false),
      limit: z.number().optional().default(50),
    }))
    .query(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      const query = db
        .select()
        .from(notifications)
        .where(eq(notifications.userId, ctx.user.id));

      if (input.unreadOnly) {
        query.where(and(
          eq(notifications.userId, ctx.user.id),
          eq(notifications.read, 0)
        ) as any);
      }

      return query.limit(input.limit).orderBy(notifications.createdAt);
    }),

  // Mark notification as read
  markRead: protectedProcedure
    .input(z.object({ notificationId: z.number() }))
    .mutation(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      await db
        .update(notifications)
        .set({ read: 1 })
        .where(and(
          eq(notifications.id, input.notificationId),
          eq(notifications.userId, ctx.user.id)
        ) as any);

      return { success: true };
    }),

  // Mark all notifications as read
  markAllRead: protectedProcedure
    .mutation(async ({ ctx }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      await db
        .update(notifications)
        .set({ read: 1 })
        .where(and(
          eq(notifications.userId, ctx.user.id),
          eq(notifications.read, 0)
        ) as any);

      return { success: true };
    }),

  // Delete notification
  delete: protectedProcedure
    .input(z.object({ notificationId: z.number() }))
    .mutation(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      await db
        .delete(notifications)
        .where(and(
          eq(notifications.id, input.notificationId),
          eq(notifications.userId, ctx.user.id)
        ) as any);

      return { success: true };
    }),

  // Get unread count
  unreadCount: protectedProcedure
    .query(async ({ ctx }) => {
      const db = await getDb();
      if (!db) return { count: 0 };

      const result = await db
        .select({ count: notifications.id })
        .from(notifications)
        .where(and(
          eq(notifications.userId, ctx.user.id),
          eq(notifications.read, 0)
        ) as any);

      return { count: result.length };
    }),
});
