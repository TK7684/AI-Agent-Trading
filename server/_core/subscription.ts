/**
 * Subscription Service
 * Manages premium tiers and feature access control
 */

export enum SubscriptionTier {
  FREE = 'free',
  PRO = 'pro',
  ENTERPRISE = 'enterprise',
}

export enum Feature {
  // Audit features
  UNLIMITED_AUDITS = 'unlimited_audits',
  ADVANCED_SECURITY_SCAN = 'advanced_security_scan',
  AI_ANALYSIS = 'ai_analysis',

  // Market data
  REAL_TIME_PRICE = 'real_time_price',
  ADVANCED_CHARTS = 'advanced_charts',
  MARKET_API_ACCESS = 'market_api_access',

  // Alerts & notifications
  UNLIMITED_ALERTS = 'unlimited_alerts',
  SMS_ALERTS = 'sms_alerts',
  EMAIL_ALERTS = 'email_alerts',

  // AI features
  AI_CHATBOT = 'ai_chatbot',
  AI_INSIGHTS = 'ai_insights',

  // Export & reports
  PDF_EXPORT = 'pdf_export',
  API_EXPORT = 'api_export',
  CUSTOM_REPORTS = 'custom_reports',

  // Watchlist & comparison
  UNLIMITED_WATCHLIST = 'unlimited_watchlist',
  ADVANCED_COMPARISON = 'advanced_comparison',

  // API access
  PUBLIC_API_ACCESS = 'public_api_access',
  API_RATE_LIMIT_BOOST = 'api_rate_limit_boost',
}

// Feature limits per tier
export const TIER_LIMITS: Record<SubscriptionTier, {
  auditsPerMonth: number;
  watchlistLimit: number;
  alertsLimit: number;
  apiRateLimit: number; // requests per minute
  features: Feature[];
}> = {
  [SubscriptionTier.FREE]: {
    auditsPerMonth: 10,
    watchlistLimit: 10,
    alertsLimit: 5,
    apiRateLimit: 30,
    features: [
      Feature.BASIC_AUDIT,
      Feature.MARKET_DATA_VIEW,
      Feature.WATCHLIST_LIMITED,
      Feature.ALERTS_LIMITED,
      Feature.PDF_EXPORT,
    ],
  },
  [SubscriptionTier.PRO]: {
    auditsPerMonth: 100,
    watchlistLimit: 100,
    alertsLimit: 50,
    apiRateLimit: 100,
    features: [
      Feature.UNLIMITED_AUDITS,
      Feature.ADVANCED_SECURITY_SCAN,
      Feature.AI_ANALYSIS,
      Feature.REAL_TIME_PRICE,
      Feature.ADVANCED_CHARTS,
      Feature.UNLIMITED_ALERTS,
      Feature.EMAIL_ALERTS,
      Feature.AI_CHATBOT,
      Feature.AI_INSIGHTS,
      Feature.PDF_EXPORT,
      Feature.API_EXPORT,
      Feature.UNLIMITED_WATCHLIST,
      Feature.ADVANCED_COMPARISON,
      Feature.PUBLIC_API_ACCESS,
    ],
  },
  [SubscriptionTier.ENTERPRISE]: {
    auditsPerMonth: -1, // unlimited
    watchlistLimit: -1,
    alertsLimit: -1,
    apiRateLimit: 1000,
    features: [
      Feature.UNLIMITED_AUDITS,
      Feature.ADVANCED_SECURITY_SCAN,
      Feature.AI_ANALYSIS,
      Feature.REAL_TIME_PRICE,
      Feature.ADVANCED_CHARTS,
      Feature.MARKET_API_ACCESS,
      Feature.UNLIMITED_ALERTS,
      Feature.SMS_ALERTS,
      Feature.EMAIL_ALERTS,
      Feature.AI_CHATBOT,
      Feature.AI_INSIGHTS,
      Feature.PDF_EXPORT,
      Feature.API_EXPORT,
      Feature.CUSTOM_REPORTS,
      Feature.UNLIMITED_WATCHLIST,
      Feature.ADVANCED_COMPARISON,
      Feature.PUBLIC_API_ACCESS,
      Feature.API_RATE_LIMIT_BOOST,
    ],
  },
};

// Pricing (in cents)
export const TIER_PRICING: Record<SubscriptionTier, {
  monthly: number;
  yearly: number;
}> = {
  [SubscriptionTier.FREE]: {
    monthly: 0,
    yearly: 0,
  },
  [SubscriptionTier.PRO]: {
    monthly: 2900, // $29/month
    yearly: 29000, // $290/year (~$24/month)
  },
  [SubscriptionTier.ENTERPRISE]: {
    monthly: 9900, // $99/month
    yearly: 99000, // $990/year (~$82/month)
  },
};

export interface UserSubscription {
  userId: number;
  tier: SubscriptionTier;
  startDate: Date;
  endDate?: Date;
  auditsThisMonth: number;
  monthStartDate: Date;
  isActive: boolean;
}

/**
 * Get user's subscription tier
 */
export function getUserTier(userRole?: string): SubscriptionTier {
  switch (userRole) {
    case 'enterprise':
    case 'admin':
      return SubscriptionTier.ENTERPRISE;
    case 'pro':
      return SubscriptionTier.PRO;
    default:
      return SubscriptionTier.FREE;
  }
}

/**
 * Check if user has access to a feature
 */
export function hasFeature(tier: SubscriptionTier, feature: Feature): boolean {
  return TIER_LIMITS[tier].features.includes(feature as any);
}

/**
 * Check if user can perform an action based on limits
 */
export function canPerformAction(
  subscription: UserSubscription,
  action: 'audit' | 'watchlist' | 'alert'
): boolean {
  const tier = getUserTier(subscription.tier as any);
  const limits = TIER_LIMITS[tier];

  switch (action) {
    case 'audit':
      return limits.auditsPerMonth === -1 || subscription.auditsThisMonth < limits.auditsPerMonth;
    case 'watchlist':
      return limits.watchlistLimit === -1;
    case 'alert':
      return limits.alertsLimit === -1;
    default:
      return false;
  }
}

/**
 * Get user's rate limit
 */
export function getRateLimit(tier: SubscriptionTier): number {
  return TIER_LIMITS[tier].apiRateLimit;
}

/**
 * Calculate prorated refund amount
 */
export function calculateProratedRefund(
  startDate: Date,
  endDate: Date,
  refundDate: Date,
  originalAmount: number
): number {
  const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  const remainingDays = Math.ceil((endDate.getTime() - refundDate.getTime()) / (1000 * 60 * 60 * 24));

  return Math.round((remainingDays / totalDays) * originalAmount);
}
