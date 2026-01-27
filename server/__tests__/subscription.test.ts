/**
 * Unit Tests for Subscription Service
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SubscriptionTier,
  TIER_LIMITS,
  TIER_PRICING,
  getUserTier,
  hasFeature,
  canPerformAction,
  getRateLimit,
  calculateProratedRefund,
  Feature,
} from '../../server/_core/subscription';

describe('Subscription Service', () => {
  describe('getUserTier', () => {
    it('should return FREE tier for undefined role', () => {
      expect(getUserTier(undefined)).toBe(SubscriptionTier.FREE);
    });

    it('should return FREE tier for user role', () => {
      expect(getUserTier('user')).toBe(SubscriptionTier.FREE);
    });

    it('should return PRO tier for pro role', () => {
      expect(getUserTier('pro')).toBe(SubscriptionTier.PRO);
    });

    it('should return ENTERPRISE tier for admin/enterprise role', () => {
      expect(getUserTier('admin')).toBe(SubscriptionTier.ENTERPRISE);
      expect(getUserTier('enterprise')).toBe(SubscriptionTier.ENTERPRISE);
    });
  });

  describe('TIER_LIMITS', () => {
    it('should have FREE tier with lowest limits', () => {
      const free = TIER_LIMITS[SubscriptionTier.FREE];
      expect(free.auditsPerMonth).toBe(10);
      expect(free.watchlistLimit).toBe(10);
      expect(free.alertsLimit).toBe(5);
      expect(free.apiRateLimit).toBe(30);
    });

    it('should have PRO tier with medium limits', () => {
      const pro = TIER_LIMITS[SubscriptionTier.PRO];
      expect(pro.auditsPerMonth).toBe(100);
      expect(pro.watchlistLimit).toBe(100);
      expect(pro.alertsLimit).toBe(50);
      expect(pro.apiRateLimit).toBe(100);
    });

    it('should have ENTERPRISE tier with unlimited limits', () => {
      const enterprise = TIER_LIMITS[SubscriptionTier.ENTERPRISE];
      expect(enterprise.auditsPerMonth).toBe(-1); // -1 means unlimited
      expect(enterprise.watchlistLimit).toBe(-1);
      expect(enterprise.alertsLimit).toBe(-1);
      expect(enterprise.apiRateLimit).toBe(1000);
    });
  });

  describe('TIER_PRICING', () => {
    it('should have FREE tier with zero cost', () => {
      const free = TIER_PRICING[SubscriptionTier.FREE];
      expect(free.monthly).toBe(0);
      expect(free.yearly).toBe(0);
    });

    it('should have PRO tier with pricing', () => {
      const pro = TIER_PRICING[SubscriptionTier.PRO];
      expect(pro.monthly).toBe(2900); // $29
      expect(pro.yearly).toBe(29000); // $290
    });

    it('should have ENTERPRISE tier with higher pricing', () => {
      const enterprise = TIER_PRICING[SubscriptionTier.ENTERPRISE];
      expect(enterprise.monthly).toBe(9900); // $99
      expect(enterprise.yearly).toBe(99000); // $990
    });

    it('should offer yearly discount for PRO', () => {
      const pro = TIER_PRICING[SubscriptionTier.PRO];
      const yearlyMonthly = pro.yearly / 12;
      const monthlySavings = pro.monthly * 12 - pro.yearly;
      expect(yearlyMonthly).toBeLessThan(pro.monthly);
      expect(monthlySavings).toBe(5800); // Save $58/year
    });
  });

  describe('hasFeature', () => {
    it('should check feature access correctly for FREE tier', () => {
      expect(hasFeature(SubscriptionTier.FREE, 'pdf_export' as any)).toBe(true);
      expect(hasFeature(SubscriptionTier.FREE, 'ai_chatbot' as any)).toBe(false);
    });

    it('should check feature access correctly for PRO tier', () => {
      expect(hasFeature(SubscriptionTier.PRO, 'ai_chatbot' as any)).toBe(true);
      expect(hasFeature(SubscriptionTier.PRO, 'public_api_access' as any)).toBe(true);
      expect(hasFeature(SubscriptionTier.PRO, 'custom_reports' as any)).toBe(false);
    });

    it('should check feature access correctly for ENTERPRISE tier', () => {
      expect(hasFeature(SubscriptionTier.ENTERPRISE, 'custom_reports' as any)).toBe(true);
      expect(hasFeature(SubscriptionTier.ENTERPRISE, 'sms_alerts' as any)).toBe(true);
    });
  });

  describe('getRateLimit', () => {
    it('should return correct rate limits per tier', () => {
      expect(getRateLimit(SubscriptionTier.FREE)).toBe(30);
      expect(getRateLimit(SubscriptionTier.PRO)).toBe(100);
      expect(getRateLimit(SubscriptionTier.ENTERPRISE)).toBe(1000);
    });
  });

  describe('calculateProratedRefund', () => {
    it('should calculate full refund if cancelled immediately', () => {
      const start = new Date('2024-01-01');
      const end = new Date('2024-02-01');
      const refundDate = new Date('2024-01-01');
      const amount = 10000; // $100

      const refund = calculateProratedRefund(start, end, refundDate, amount);
      expect(refund).toBe(amount);
    });

    it('should calculate no refund if cancelled at period end', () => {
      const start = new Date('2024-01-01');
      const end = new Date('2024-02-01');
      const refundDate = new Date('2024-02-01');
      const amount = 10000;

      const refund = calculateProratedRefund(start, end, refundDate, amount);
      expect(refund).toBe(0);
    });

    it('should calculate half refund for mid-period cancellation', () => {
      const start = new Date('2024-01-01');
      const end = new Date('2024-02-01');
      const refundDate = new Date('2024-01-16');
      const amount = 10000;

      const refund = calculateProratedRefund(start, end, refundDate, amount);
      expect(refund).toBeGreaterThan(4000);
      expect(refund).toBeLessThan(6000);
    });
  });
});
