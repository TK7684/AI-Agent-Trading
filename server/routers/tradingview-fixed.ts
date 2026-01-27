/**
 * TradingView Integration Router
 * Webhook receiver for TradingView alerts + signal generation
 */

import { z } from "zod";
import { publicProcedure, protectedProcedure, router } from "../_core/trpc";
import { eq, and, desc } from "drizzle-orm";
import { getDb } from "../db";
import { tradingViewAlerts, tradingSignals, notifications, projects, auditReports } from "../../drizzle/schema";
import crypto from "crypto";

// Validation schema for TradingView webhook alerts
const TradingViewAlertSchema = z.object({
  symbol: z.string(),
  exchange: z.string().default("BINANCE"),
  price: z.number(),
  action: z.enum(["BUY", "SELL", "HOLD"]),
  indicators: z.object({
    rsi: z.number().optional(),
    macd: z.number().optional(),
    ema: z.number().optional(),
    bb: z.boolean().optional(),
    volume: z.number().optional(),
  }).optional(),
  message: z.string().optional(),
  timestamp: z.number().optional(),
  signature: z.string().optional(), // TradingView webhook signature
});

// Verify TradingView webhook signature
function verifyWebhookSignature(payload: any, signature: string | undefined): boolean {
  if (!signature || !process.env.TRADINGVIEW_WEBHOOK_SECRET) {
    console.warn("[TradingView] Webhook signature verification skipped - no secret configured");
    return true; // Allow if not configured
  }

  const payloadString = JSON.stringify(payload);
  const expectedSignature = crypto
    .createHmac('sha256', process.env.TRADINGVIEW_WEBHOOK_SECRET)
    .update(payloadString)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature, 'hex'),
    Buffer.from(expectedSignature, 'hex')
  );
}

// Combined signal calculation
function calculateCombinedSignal(params: {
  tradingViewAction: string;
  auditScore?: number | null;
  riskLevel?: string | null;
}): {
  action: "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
  confidence: number;
  reasoning: string;
} {
  const { tradingViewAction, auditScore, riskLevel } = params;
  const tvScore = tradingViewAction === "BUY" ? 80 : tradingViewAction === "SELL" ? 20 : 50;
  const auditWeight = auditScore || 50;

  // Calculate weighted average
  let combinedScore = (tvScore * 0.4) + (auditWeight * 0.6);

  // Adjust based on risk level
  if (riskLevel === "critical") combinedScore -= 30;
  if (riskLevel === "high") combinedScore -= 15;
  if (riskLevel === "low") combinedScore += 10;

  // Determine action and confidence
  let action: "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
  let confidence = combinedScore;
  let reasoning = "";

  if (combinedScore >= 80) {
    action = "STRONG_BUY";
    reasoning = `Strong buy signal: TradingView ${tradingViewAction} + high audit score (${auditScore || 'N/A'})`;
  } else if (combinedScore >= 60) {
    action = "BUY";
    reasoning = `Buy signal: TradingView ${tradingViewAction} + good audit score (${auditScore || 'N/A'})`;
  } else if (combinedScore >= 40) {
    action = "HOLD";
    reasoning = `Hold signal: Mixed signals from TradingView (${tradingViewAction}) and audit (${auditScore || 'N/A'})`;
  } else if (combinedScore >= 20) {
    action = "SELL";
    reasoning = `Sell signal: TradingView ${tradingViewAction} + lower audit score (${auditScore || 'N/A'})`;
  } else {
    action = "STRONG_SELL";
    reasoning = `Strong sell signal: TradingView ${tradingViewAction} + low audit score (${auditScore || 'N/A'})`;
  }

  return { action, confidence, reasoning };
}

export const tradingViewRouter = router({
  /**
   * Webhook endpoint for TradingView alerts
   * This is a public endpoint that TradingView can send alerts to
   */
  receiveAlert: publicProcedure
    .input(TradingViewAlertSchema)
    .mutation(async ({ input, ctx }) => {
      const { symbol, exchange, action, price, indicators, message, timestamp, signature } = input;

      // Verify webhook signature
      if (!verifyWebhookSignature(input, signature)) {
        console.error("[TradingView] Invalid webhook signature for alert:", input);
        throw new Error("Invalid webhook signature");
      }

      const db = await getDb();
      if (!db) {
        throw new Error("Database not available");
      }

      // Store alert
      const alertResult = await db.insert(tradingViewAlerts).values({
        userId: ctx.user?.id || 1, // Default to admin user if no auth
        symbol,
        exchange,
        action,
        price: price.toString(),
        indicators: JSON.stringify(indicators || {}),
        message: message || `${action} signal for ${symbol}`,
        timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
        processed: 0,
      }).returning();

      const alertId = alertResult[0].id;

      // Try to find associated audit project
      // Note: projects table doesn't have a symbol column, so we skip this lookup
      // In production, you'd need to add a symbol column to projects or use a different lookup method
      let auditScore: number | null = null;
      let riskLevel: string | null = null;
      let projectId: number | null = null;

      // Generate combined signal
      if (action !== "HOLD") {
        const signal = calculateCombinedSignal({
          tradingViewAction: action,
          auditScore,
          riskLevel,
        });

        // Calculate trading recommendations
        const currentPrice = price;
        let stopLoss: string, takeProfit: string;

        if (action === "BUY") {
          stopLoss = (currentPrice * 0.95).toFixed(2); // 5% below
          takeProfit = (currentPrice * 1.15).toFixed(2); // 15% above
        } else {
          stopLoss = (currentPrice * 1.05).toFixed(2); // 5% above
          takeProfit = (currentPrice * 0.85).toFixed(2); // 15% below
        }

        // Create trading signal
        await db.insert(tradingSignals).values({
          userId: ctx.user?.id || 1,
          projectId,
          symbol,
          signalType: signal.action,
          tradingViewSignal: 1,
          auditSignal: projectId ? 1 : 0,
          geminiSignal: 0, // Will be updated when Gemini is integrated
          confidence: signal.confidence,
          auditScore: auditScore || 0,
          technicalScore: indicators?.rsi || 50,
          entryPrice: currentPrice.toString(),
          stopLoss,
          takeProfit,
          positionSize: "5", // Default 5% of portfolio
          reasoning: signal.reasoning,
          riskLevel: riskLevel || "medium",
          status: "active",
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // Expires in24h
        });

        // Create notification
        if (ctx.user?.id) {
          await db.insert(notifications).values({
            userId: ctx.user.id,
            type: action === "BUY" ? "info" : "warning",
            title: `TradingView Alert: ${symbol}`,
            message: `${action} signal at $${currentPrice}. ${signal.reasoning}`,
            data: JSON.stringify({
              alertId,
              signal: signal.action,
              confidence: signal.confidence,
              price: currentPrice,
              stopLoss,
              takeProfit,
            }),
            read: 0,
          });
        }

        // Mark alert as processed
        await db.update(tradingViewAlerts)
          .set({ processed: 1 })
          .where(eq(tradingViewAlerts.id, alertId));

        return {
          success: true,
          signal: {
            action: signal.action,
            confidence: signal.confidence,
            reasoning: signal.reasoning,
            stopLoss,
            takeProfit,
            auditScore,
            riskLevel,
          },
        };
      }

      return {
        success: true,
        message: "Alert stored (HOLD action - no signal generated)",
      };
    }),

  /**
   * Get recent TradingView alerts for a user
   */
  getAlerts: protectedProcedure
    .input(z.object({
      limit: z.number().min(1).max(100).optional().default(50),
      symbol: z.string().optional(),
    }))
    .query(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) return [];

      const conditions = input.symbol
        ? and(eq(tradingViewAlerts.userId, ctx.user.id), eq(tradingViewAlerts.symbol, input.symbol))
        : eq(tradingViewAlerts.userId, ctx.user.id);

      return await db.select().from(tradingViewAlerts)
        .where(conditions)
        .orderBy(desc(tradingViewAlerts.timestamp))
        .limit(input.limit);
    }),

  /**
   * Get trading signals for a user
   */
  getSignals: protectedProcedure
    .input(z.object({
      status: z.enum(["active", "executed", "expired"]).optional(),
      limit: z.number().min(1).max(100).optional().default(50),
    }))
    .query(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) return [];

      const conditions = input.status
        ? and(eq(tradingSignals.userId, ctx.user.id), eq(tradingSignals.status, input.status))
        : eq(tradingSignals.userId, ctx.user.id);

      return await db.select().from(tradingSignals)
        .where(conditions)
        .orderBy(desc(tradingSignals.createdAt))
        .limit(input.limit);
    }),

  /**
   * Get a specific signal with details
   */
  getSignalById: protectedProcedure
    .input(z.object({ id: z.number() }))
    .query(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) return null;

      const result = await db.select().from(tradingSignals)
        .where(and(
          eq(tradingSignals.id, input.id),
          eq(tradingSignals.userId, ctx.user.id)
        ))
        .limit(1);

      return result.length > 0 ? result[0] : null;
    }),

  /**
   * Update signal status (mark as executed or expired)
   */
  updateSignalStatus: protectedProcedure
    .input(z.object({
      id: z.number(),
      status: z.enum(["executed", "expired"]),
    }))
    .mutation(async ({ ctx, input }) => {
      const db = await getDb();
      if (!db) throw new Error("Database not available");

      await db.update(tradingSignals)
        .set({ status: input.status })
        .where(and(
          eq(tradingSignals.id, input.id),
          eq(tradingSignals.userId, ctx.user.id)
        ));

      return { success: true };
    }),

  /**
   * Get webhook URL for TradingView
   */
  getWebhookUrl: protectedProcedure
    .query(async ({ ctx }) => {
      const baseUrl = process.env.VITE_FRONTEND_URL || "http://localhost:3000";
      return {
        webhookUrl: `${baseUrl}/api/trpc/tradingView.receiveAlert`,
        instructions: {
          step1: "Open TradingView and create a new alert",
          step2: "Set your alert conditions (RSI, MACD, etc.)",
          step3: "In alert message tab, select 'Webhook URL'",
          step4: `Paste this URL: ${baseUrl}/api/trpc/tradingView.receiveAlert`,
          step5: "Set the message template to JSON format shown in documentation",
        },
      };
    }),

  /**
   * Get alert template for TradingView
   */
  getAlertTemplate: publicProcedure
    .query(() => {
      return {
        template: `{"symbol": "{{ticker}}", "exchange": "BINANCE", "price": {{close}}, "action": "{{strategy.order.action}}", "indicators": {"rsi": {{plot_rsi}}, "macd": {{plot_macd}}}, "message": "{{strategy.order.comment}}"}`,
        example: {
          symbol: "BTCUSDT",
          exchange: "BINANCE",
          price: 45000.50,
          action: "BUY",
          indicators: {
            rsi: 35,
            macd: 1.2,
          },
          message: "RSI oversold - Buy signal",
        },
      };
    }),
});