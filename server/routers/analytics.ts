/**
 * Analytics Router
 * Provides analytics and metrics for admin dashboard
 */

import { z } from 'zod';
import { protectedProcedure, router } from '../_core/trpc';
import { analyticsService } from '../_core/analytics';

export const analyticsRouter = router({
  // Get all analytics data (admin only)
  getAll: protectedProcedure
    .input(z.object({
      startDate: z.string().optional(),
      endDate: z.string().optional(),
    }).optional())
    .use(async ({ ctx, next }) => {
      // Check if user is admin
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async ({ input }) => {
      const dateRange = input?.startDate && input?.endDate
        ? { start: new Date(input.startDate), end: new Date(input.endDate) }
        : undefined;

      return analyticsService.getAnalytics(dateRange);
    }),

  // Get user metrics (admin only)
  getUserMetrics: protectedProcedure
    .use(async ({ ctx, next }) => {
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async () => {
      return analyticsService.getUserMetrics();
    }),

  // Get feature usage (admin only)
  getFeatureUsage: protectedProcedure
    .use(async ({ ctx, next }) => {
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async () => {
      return analyticsService.getFeatureUsage();
    }),

  // Get revenue metrics (admin only)
  getRevenueMetrics: protectedProcedure
    .use(async ({ ctx, next }) => {
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async () => {
      return analyticsService.getRevenueMetrics();
    }),

  // Get trend data (admin only)
  getTrends: protectedProcedure
    .input(z.object({
      startDate: z.string().optional(),
      endDate: z.string().optional(),
      days: z.number().optional().default(30),
    }))
    .use(async ({ ctx, next }) => {
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async ({ input }) => {
      const endDate = input.endDate ? new Date(input.endDate) : new Date();
      const startDate = input.startDate
        ? new Date(input.startDate)
        : new Date(Date.now() - input.days * 24 * 60 * 60 * 1000);

      return analyticsService.getTrends({ start: startDate, end: endDate });
    }),

  // Get top projects (admin only)
  getTopProjects: protectedProcedure
    .input(z.object({
      limit: z.number().optional().default(10),
    }))
    .use(async ({ ctx, next }) => {
      if (ctx.user?.role !== 'admin') {
        throw new Error('Unauthorized: Admin access required');
      }
      return next();
    })
    .query(async ({ input }) => {
      return analyticsService.getTopProjects(input.limit);
    }),

  // Track an event (internal use)
  trackEvent: protectedProcedure
    .input(z.object({
      type: z.enum(['page_view', 'audit_run', 'feature_used', 'conversion']),
      data: z.record(z.any()).optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      await analyticsService.trackEvent({
        ...input,
        userId: ctx.user?.id,
      });
      return { success: true };
    }),
});
