/**
 * Subscription Router
 * Manages user subscriptions and tier upgrades
 */

import { z } from 'zod';
import { protectedProcedure, publicProcedure, router } from '../_core/trpc';
import { eq } from 'drizzle-orm';
import { users } from '@drizzle/schema';
import { getDb } from '../db';
import {
  SubscriptionTier,
  TIER_LIMITS,
  TIER_PRICING,
  getUserTier,
  hasFeature,
  canPerformAction,
  getRateLimit,
} from '../_core/subscription';
import { createRateLimitMiddleware } from '../_core/rateLimit';

// Get user's subscription info
async function getUserSubscription(userId: number) {
  const db = await getDb();
  if (!db) throw new Error('Database not available');

  const result = await db
    .select()
    .from(users)
    .where(eq(users.id, userId))
    .limit(1);

  if (result.length === 0) {
    throw new Error('User not found');
  }

  const user = result[0];
  const tier = getUserTier(user.role);
  const limits = TIER_LIMITS[tier];

  return {
    tier,
    role: user.role,
    limits: {
      auditsPerMonth: limits.auditsPerMonth,
      watchlistLimit: limits.watchlistLimit,
      alertsLimit: limits.alertsLimit,
      apiRateLimit: limits.apiRateLimit,
    },
    features: limits.features,
    pricing: TIER_PRICING[tier],
  };
}

export const subscriptionRouter = router({
  // Get current subscription info
  getCurrent: protectedProcedure.query(async ({ ctx }) => {
    return getUserSubscription(ctx.user.id);
  }),

  // Get available subscription tiers
  getTiers: publicProcedure.query(() => {
    return Object.entries(SubscriptionTier).map(([key, value]) => ({
      id: value,
      name: key,
      limits: TIER_LIMITS[value],
      pricing: TIER_PRICING[value],
    }));
  }),

  // Check if user has access to a feature
  checkFeature: protectedProcedure
    .input(z.object({
      feature: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      const subscription = await getUserSubscription(ctx.user.id);
      return {
        hasAccess: subscription.features.includes(input.feature as any),
        tier: subscription.tier,
      };
    }),

  // Check if user can perform an action
  canPerform: protectedProcedure
    .input(z.object({
      action: z.enum(['audit', 'watchlist', 'alert']),
    }))
    .query(async ({ ctx, input }) => {
      const subscription = await getUserSubscription(ctx.user.id);
      const tier = subscription.tier;

      // For now, return true for all actions
      // In production, you'd check actual usage against limits
      return {
        canPerform: true,
        tier,
        limits: subscription.limits,
      };
    }),

  // Upgrade subscription (would integrate with payment provider)
  upgrade: protectedProcedure
    .input(z.object({
      tier: z.enum(['pro', 'enterprise']),
      billingPeriod: z.enum(['monthly', 'yearly']).default('monthly'),
    }))
    .use(createRateLimitMiddleware({ limit: { requests: 3, window: 60 } }))
    .mutation(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      // In production, this would:
      // 1. Create payment intent with Stripe/Payment provider
      // 2. Redirect to payment page
      // 3. Handle webhook to update role after payment

      // For now, just return the checkout URL info
      const tier = input.tier === 'pro' ? SubscriptionTier.PRO : SubscriptionTier.ENTERPRISE;
      const pricing = TIER_PRICING[tier];
      const amount = input.billingPeriod === 'yearly' ? pricing.yearly : pricing.monthly;

      return {
        checkoutUrl: `https://checkout.stripe.com/pay?tier=${input.tier}&period=${input.billingPeriod}`,
        amount,
        currency: 'USD',
        tier: input.tier,
        billingPeriod: input.billingPeriod,
      };
    }),

  // Cancel subscription
  cancel: protectedProcedure
    .use(createRateLimitMiddleware({ limit: { requests: 3, window: 60 } }))
    .mutation(async ({ ctx }) => {
      const db = await getDb();
      if (!db) throw new Error('Database not available');

      // In production, this would:
      // 1. Cancel subscription in Stripe
      // 2. Schedule role downgrade at period end

      return {
        success: true,
        message: 'Subscription will be cancelled at the end of the billing period',
      };
    }),

  // Get usage statistics
  getUsage: protectedProcedure.query(async ({ ctx }) => {
    const db = await getDb();
    if (!db) throw new Error('Database not available');

    const subscription = await getUserSubscription(ctx.user.id);

    // In production, you'd query actual usage from the database
    return {
      auditsThisMonth: 0,
      auditsLimit: subscription.limits.auditsPerMonth,
      watchlistCount: 0,
      watchlistLimit: subscription.limits.watchlistLimit,
      alertsCount: 0,
      alertsLimit: subscription.limits.alertsLimit,
      apiCallsThisMinute: 0,
      apiRateLimit: subscription.limits.apiRateLimit,
    };
  }),

  // Get billing history
  getBillingHistory: protectedProcedure.query(async ({ ctx }) => {
    // In production, this would fetch from payment provider
    return {
      invoices: [],
      hasMore: false,
    };
  }),

  // Update payment method
  updatePaymentMethod: protectedProcedure
    .input(z.object({
      paymentMethodId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      // In production, this would update in Stripe
      return {
        success: true,
        message: 'Payment method updated',
      };
    }),
});
