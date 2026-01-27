/**
 * Alert Monitor Service
 * Background job to monitor price/score changes and trigger alerts
 * Supports email and in-app notifications
 */

import { eq, and } from 'drizzle-orm';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { alertSettings, projects, auditReports, users, notifications } from '@drizzle/schema';
import { marketDataService } from './marketData';

// Types
interface AlertTrigger {
  alertId: number;
  userId: number;
  projectId: number;
  type: 'price' | 'score';
  message: string;
  data: any;
}

interface AlertCheck {
  alertId: number;
  userId: number;
  projectId: number;
  priceChangePercent?: number;
  scoreChangePoints?: number;
}

// State tracking
let lastCheckTime = Date.now();
const priceHistory = new Map<number, number>(); // projectId -> lastPrice
const scoreHistory = new Map<number, number>(); // projectId -> lastScore

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
      console.warn('[AlertMonitor] Failed to connect:', error);
      _db = null;
    }
  }
  return _db;
}

/**
 * Alert Monitor Service
 */
class AlertMonitorService {
  private isRunning = false;
  private checkInterval = 60000; // Check every 1 minute
  private intervalId: NodeJS.Timeout | null = null;

  /**
   * Start the alert monitor
   */
  start(): void {
    if (this.isRunning) {
      console.log('[AlertMonitor] Already running');
      return;
    }

    console.log('[AlertMonitor] Starting alert monitor...');
    this.isRunning = true;

    // Run immediately on start
    this.checkAlerts().catch(console.error);

    // Set up recurring checks
    this.intervalId = setInterval(() => {
      this.checkAlerts().catch(console.error);
    }, this.checkInterval);
  }

  /**
   * Stop the alert monitor
   */
  stop(): void {
    if (!this.isRunning) {
      return;
    }

    console.log('[AlertMonitor] Stopping alert monitor...');
    this.isRunning = false;

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * Check all enabled alerts and trigger if conditions are met
   */
  async checkAlerts(): Promise<void> {
    const db = await getDb();
    if (!db) {
      console.warn('[AlertMonitor] Database not available');
      return;
    }

    try {
      const startTime = Date.now();

      // Get all enabled alerts
      const alerts = await db
        .select()
        .from(alertSettings)
        .where(eq(alertSettings.enabled, 1));

      if (alerts.length === 0) {
        return;
      }

      console.log(`[AlertMonitor] Checking ${alerts.length} alerts...`);

      const triggers: AlertTrigger[] = [];

      // Check each alert
      for (const alert of alerts) {
        const trigger = await this.checkAlert(alert);
        if (trigger) {
          triggers.push(trigger);
        }
      }

      // Process triggers
      for (const trigger of triggers) {
        await this.processTrigger(trigger);
      }

      const elapsed = Date.now() - startTime;
      console.log(`[AlertMonitor] Check complete in ${elapsed}ms. Triggered ${triggers.length} alerts.`);

      lastCheckTime = Date.now();
    } catch (error) {
      console.error('[AlertMonitor] Error checking alerts:', error);
    }
  }

  /**
   * Check a single alert
   */
  private async checkAlert(alert: any): Promise<AlertTrigger | null> {
    const { id: alertId, userId, projectId, priceChangePercent, scoreChangePoints } = alert;

    // Get project and audit report
    const db = await getDb();
    if (!db) return null;

    const projectResult = await db
      .select()
      .from(projects)
      .where(eq(projects.id, projectId))
      .limit(1);

    if (projectResult.length === 0) return null;
    const project = projectResult[0];

    const reportResult = await db
      .select()
      .from(auditReports)
      .where(eq(auditReports.projectId, projectId))
      .limit(1);

    const report = reportResult[0];

    // Check price change alert
    if (priceChangePercent && project.contractAddress) {
      const priceTrigger = await this.checkPriceAlert(
        alertId,
        userId,
        projectId,
        project,
        priceChangePercent
      );
      if (priceTrigger) return priceTrigger;
    }

    // Check score change alert
    if (scoreChangePoints && report) {
      const scoreTrigger = await this.checkScoreAlert(
        alertId,
        userId,
        projectId,
        project,
        report,
        scoreChangePoints
      );
      if (scoreTrigger) return scoreTrigger;
    }

    return null;
  }

  /**
   * Check price change alert
   */
  private async checkPriceAlert(
    alertId: number,
    userId: number,
    projectId: number,
    project: any,
    threshold: number
  ): Promise<AlertTrigger | null> {
    try {
      // Get current price from market data
      const priceData = await marketDataService.getDetailedMarketData(
        project.description?.split(' ')[0] || 'BTC' // Use symbol from description
      );

      if (!priceData) return null;

      const currentPrice = priceData.price;
      const lastPrice = priceHistory.get(projectId);

      if (!lastPrice) {
        // First check, store price
        priceHistory.set(projectId, currentPrice);
        return null;
      }

      // Calculate price change percentage
      const priceChangePercent = ((currentPrice - lastPrice) / lastPrice) * 100;

      // Check if threshold is met
      if (Math.abs(priceChangePercent) >= threshold) {
        // Update price history
        priceHistory.set(projectId, currentPrice);

        const direction = priceChangePercent > 0 ? 'increased' : 'decreased';

        return {
          alertId,
          userId,
          projectId,
          type: 'price',
          message: `Price alert: ${project.name} ${direction} by ${Math.abs(priceChangePercent).toFixed(2)}%`,
          data: {
            projectName: project.name,
            oldPrice: lastPrice,
            newPrice: currentPrice,
            changePercent: priceChangePercent,
            threshold,
          },
        };
      }

      // Update price history periodically
      priceHistory.set(projectId, currentPrice);
    } catch (error) {
      console.error(`[AlertMonitor] Error checking price alert for project ${projectId}:`, error);
    }

    return null;
  }

  /**
   * Check score change alert
   */
  private async checkScoreAlert(
    alertId: number,
    userId: number,
    projectId: number,
    project: any,
    report: any,
    threshold: number
  ): Promise<AlertTrigger | null> {
    try {
      const currentScore = report.overallScore || 0;
      const lastScore = scoreHistory.get(projectId);

      if (!lastScore) {
        // First check, store score
        scoreHistory.set(projectId, currentScore);
        return null;
      }

      const scoreChange = currentScore - lastScore;

      // Check if threshold is met
      if (Math.abs(scoreChange) >= threshold) {
        // Update score history
        scoreHistory.set(projectId, currentScore);

        const direction = scoreChange > 0 ? 'improved' : 'declined';
        const newRiskLevel = this.getRiskLevel(currentScore);

        return {
          alertId,
          userId,
          projectId,
          type: 'score',
          message: `Score alert: ${project.name} audit score ${direction} by ${Math.abs(scoreChange)} points (now ${currentScore}/100)`,
          data: {
            projectName: project.name,
            oldScore: lastScore,
            newScore: currentScore,
            scoreChange,
            threshold,
            newRiskLevel,
          },
        };
      }

      // Update score history
      scoreHistory.set(projectId, currentScore);
    } catch (error) {
      console.error(`[AlertMonitor] Error checking score alert for project ${projectId}:`, error);
    }

    return null;
  }

  /**
   * Process an alert trigger
   */
  private async processTrigger(trigger: AlertTrigger): Promise<void> {
    const db = await getDb();
    if (!db) return;

    try {
      // Create in-app notification
      await db.insert(notifications).values({
        userId: trigger.userId,
        type: trigger.type === 'price' ? 'info' : 'warning',
        title: trigger.type === 'price' ? 'Price Alert' : 'Score Alert',
        message: trigger.message,
        data: JSON.stringify(trigger.data),
        read: 0,
      });

      console.log(`[AlertMonitor] Alert triggered for user ${trigger.userId}: ${trigger.message}`);

      // Here you could also send email notifications
      // For now, just in-app notifications
    } catch (error) {
      console.error('[AlertMonitor] Error processing trigger:', error);
    }
  }

  /**
   * Get risk level from score
   */
  private getRiskLevel(score: number): string {
    if (score >= 80) return 'low';
    if (score >= 60) return 'medium';
    if (score >= 40) return 'high';
    return 'critical';
  }

  /**
   * Get monitor status
   */
  getStatus(): {
    isRunning: boolean;
    lastCheckTime: number;
    trackedProjects: number;
  } {
    return {
      isRunning: this.isRunning,
      lastCheckTime,
      trackedProjects: new Set([...priceHistory.keys(), ...scoreHistory.keys()]).size,
    };
  }

  /**
   * Manually trigger a check for specific alerts
   */
  async manualCheck(alertIds: number[]): Promise<AlertTrigger[]> {
    const db = await getDb();
    if (!db) return [];

    const triggers: AlertTrigger[] = [];

    for (const alertId of alertIds) {
      const alerts = await db
        .select()
        .from(alertSettings)
        .where(eq(alertSettings.id, alertId))
        .limit(1);

      if (alerts.length > 0) {
        const trigger = await this.checkAlert(alerts[0]);
        if (trigger) {
          triggers.push(trigger);
          await this.processTrigger(trigger);
        }
      }
    }

    return triggers;
  }
}

// Export singleton instance
export const alertMonitorService = new AlertMonitorService();

// Auto-start in production
if (process.env.NODE_ENV === 'production') {
  alertMonitorService.start();
}

// Graceful shutdown
process.on('SIGINT', () => {
  alertMonitorService.stop();
});

process.on('SIGTERM', () => {
  alertMonitorService.stop();
});
