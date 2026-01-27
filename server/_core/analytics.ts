/**
 * Analytics Service
 * Tracks user behavior, feature usage, and business metrics
 */

import { eq, and, gte, lte, sql, desc } from 'drizzle-orm';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { users, projects, auditReports, watchlist, comparisons, alertSettings, notifications } from '@drizzle/schema';

let _db: ReturnType<typeof drizzle> | null = null;
let _client: postgres.Sql | null = null;

async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _client = postgres(process.env.DATABASE_URL, {
        onnotice: () => {},
      });
      _db = drizzle(_client);
    } catch (error) {
      console.warn('[Analytics] Failed to connect:', error);
      _db = null;
    }
  }
  return _db;
}

// Types
export interface UserMetrics {
  totalUsers: number;
  activeUsers: number; // Last 30 days
  newUsers: number; // Last 30 days
  paidUsers: number;
  churnRate: number; // Last 30 days
}

export interface FeatureUsage {
  totalProjects: number;
  totalAudits: number;
  totalWatchlist: number;
  totalComparisons: number;
  totalAlerts: number;
}

export interface PerformanceMetrics {
  avgResponseTime: number;
  errorRate: number;
  uptime: number;
  slowQueries: number;
}

export interface RevenueMetrics {
  mrr: number; // Monthly Recurring Revenue
  arr: number; // Annual Recurring Revenue
  arpu: number; // Average Revenue Per User
  ltv: number; // Lifetime Value
  trialConversions: number;
}

export interface AnalyticsData {
  users: UserMetrics;
  features: FeatureUsage;
  performance: PerformanceMetrics;
  revenue: RevenueMetrics;
  trends: {
    dailyUsers: Array<{ date: string; count: number }>;
    dailyAudits: Array<{ date: string; count: number }>;
    dailyRevenue: Array<{ date: string; amount: number }>;
  };
}

/**
 * Analytics Service
 */
class AnalyticsService {
  /**
   * Get all analytics data
   */
  async getAnalytics(dateRange?: { start: Date; end: Date }): Promise<AnalyticsData> {
    const [users, features, revenue] = await Promise.all([
      this.getUserMetrics(),
      this.getFeatureUsage(),
      this.getRevenueMetrics(),
    ]);

    const trends = await this.getTrends(dateRange);

    return {
      users,
      features,
      performance: {
        avgResponseTime: 150, // Placeholder
        errorRate: 0.02, // 2%
        uptime: 99.9,
        slowQueries: 12,
      },
      revenue,
      trends,
    };
  }

  /**
   * Get user metrics
   */
  async getUserMetrics(): Promise<UserMetrics> {
    const db = await getDb();
    if (!db) {
      return { totalUsers: 0, activeUsers: 0, newUsers: 0, paidUsers: 0, churnRate: 0 };
    }

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    try {
      const [totalResult, activeResult, newResult, paidResult] = await Promise.all([
        db.select({ count: sql<number>`count(*)::int` }).from(users),
        db
          .select({ count: sql<number>`count(*)::int` })
          .from(users)
          .where(gte(users.lastSignedIn, thirtyDaysAgo)),
        db
          .select({ count: sql<number>`count(*)::int` })
          .from(users)
          .where(gte(users.createdAt, thirtyDaysAgo)),
        db
          .select({ count: sql<number>`count(*)::int` })
          .from(users)
          .where(sql`${users.role} IN ('pro', 'enterprise')`),
      ]);

      return {
        totalUsers: totalResult[0]?.count || 0,
        activeUsers: activeResult[0]?.count || 0,
        newUsers: newResult[0]?.count || 0,
        paidUsers: paidResult[0]?.count || 0,
        churnRate: 2.5, // Placeholder - would need historical data
      };
    } catch (error) {
      console.error('[Analytics] Error fetching user metrics:', error);
      return { totalUsers: 0, activeUsers: 0, newUsers: 0, paidUsers: 0, churnRate: 0 };
    }
  }

  /**
   * Get feature usage metrics
   */
  async getFeatureUsage(): Promise<FeatureUsage> {
    const db = await getDb();
    if (!db) {
      return { totalProjects: 0, totalAudits: 0, totalWatchlist: 0, totalComparisons: 0, totalAlerts: 0 };
    }

    try {
      const [projectsResult, watchlistResult, comparisonsResult, alertsResult] = await Promise.all([
        db.select({ count: sql<number>`count(*)::int` }).from(projects),
        db.select({ count: sql<number>`count(*)::int` }).from(watchlist),
        db.select({ count: sql<number>`count(*)::int` }).from(comparisons),
        db.select({ count: sql<number>`count(*)::int` }).from(alertSettings),
      ]);

      // Count completed audits
      const auditsResult = await db
        .select({ count: sql<number>`count(*)::int` })
        .from(auditReports)
        .where(sql`${auditReports.overallScore} IS NOT NULL`);

      return {
        totalProjects: projectsResult[0]?.count || 0,
        totalAudits: auditsResult[0]?.count || 0,
        totalWatchlist: watchlistResult[0]?.count || 0,
        totalComparisons: comparisonsResult[0]?.count || 0,
        totalAlerts: alertsResult[0]?.count || 0,
      };
    } catch (error) {
      console.error('[Analytics] Error fetching feature metrics:', error);
      return { totalProjects: 0, totalAudits: 0, totalWatchlist: 0, totalComparisons: 0, totalAlerts: 0 };
    }
  }

  /**
   * Get revenue metrics
   */
  async getRevenueMetrics(): Promise<RevenueMetrics> {
    // In production, this would fetch from Stripe/payment provider
    // For now, return placeholder data
    const userMetrics = await this.getUserMetrics();

    return {
      mrr: userMetrics.paidUsers * 29 * 0.5, // Assume $29/mo avg, 50% pay annually
      arr: userMetrics.paidUsers * 290 * 0.5,
      arpu: 15, // $15 per user average
      ltv: 180, // $180 lifetime value (12 months * $15)
      trialConversions: Math.floor(userMetrics.newUsers * 0.05), // 5% conversion
    };
  }

  /**
   * Get trend data
   */
  async getTrends(dateRange?: { start: Date; end: Date }): Promise<{
    dailyUsers: Array<{ date: string; count: number }>;
    dailyAudits: Array<{ date: string; count: number }>;
    dailyRevenue: Array<{ date: string; amount: number }>;
  }> {
    const db = await getDb();
    if (!db) {
      return { dailyUsers: [], dailyAudits: [], dailyRevenue: [] };
    }

    const start = dateRange?.start || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    const end = dateRange?.end || new Date();

    try {
      // Get daily active users
      const dailyUsers = await db
        .select({
          date: sql<string>`date(${users.lastSignedIn})`,
          count: sql<number>`count(*)::int`,
        })
        .from(users)
        .where(
          and(
            gte(users.lastSignedIn, start),
            lte(users.lastSignedIn, end)
          )
        )
        .groupBy(sql`date(${users.lastSignedIn})`)
        .orderBy(sql`date(${users.lastSignedIn})`);

      // Get daily audits
      const dailyAudits = await db
        .select({
          date: sql<string>`date(${auditReports.createdAt})`,
          count: sql<number>`count(*)::int`,
        })
        .from(auditReports)
        .where(
          and(
            gte(auditReports.createdAt, start),
            lte(auditReports.createdAt, end)
          )
        )
        .groupBy(sql`date(${auditReports.createdAt})`)
        .orderBy(sql`date(${auditReports.createdAt})`);

      // Placeholder for daily revenue (would come from payment provider)
      const dailyRevenue = dailyAudits.map(a => ({
        date: a.date,
        amount: Math.floor(Math.random() * 500) + 100, // Placeholder
      }));

      return {
        dailyUsers,
        dailyAudits,
        dailyRevenue,
      };
    } catch (error) {
      console.error('[Analytics] Error fetching trends:', error);
      return { dailyUsers: [], dailyAudits: [], dailyRevenue: [] };
    }
  }

  /**
   * Track an event
   */
  async trackEvent(event: {
    type: 'page_view' | 'audit_run' | 'feature_used' | 'conversion';
    userId?: number;
    data?: Record<string, any>;
  }): Promise<void> {
    const db = await getDb();
    if (!db) return;

    // In production, this would store events in a separate events table
    console.log('[Analytics] Event:', event);
  }

  /**
   * Get top projects by audit count
   */
  async getTopProjects(limit = 10): Promise<Array<{
    id: number;
    name: string;
    auditCount: number;
  }>> {
    const db = await getDb();
    if (!db) return [];

    try {
      const result = await db
        .select({
          id: projects.id,
          name: projects.name,
          auditCount: sql<number>`count(${auditReports.id})::int`,
        })
        .from(projects)
        .innerJoin(auditReports, eq(projects.id, auditReports.projectId))
        .groupBy(projects.id, projects.name)
        .orderBy(desc(sql`count(${auditReports.id})`))
        .limit(limit);

      return result;
    } catch (error) {
      console.error('[Analytics] Error fetching top projects:', error);
      return [];
    }
  }
}

// Export singleton instance
export const analyticsService = new AnalyticsService();
