import { pgEnum, pgTable, serial, integer, text, timestamp, varchar } from "drizzle-orm/pg-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = pgTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by database.
   * Use this for relations between tables.
   */
  id: serial("id").primaryKey(),
  /** User identifier (openId) returned from OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  passwordHash: varchar("passwordHash", { length: 255 }), // For email/password authentication
  role: varchar("role", { length: 20 }).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Projects table - เก็บข้อมูลโปรเจกต์คริปโตที่ต้องการตรวจสอบ
 */
export const projects = pgTable("projects", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(), // user who created this audit
  name: varchar("name", { length: 255 }).notNull(),
  description: text("description"),

  // Project links
  githubUrl: varchar("githubUrl", { length: 512 }),
  contractAddress: varchar("contractAddress", { length: 128 }),
  chain: varchar("chain", { length: 64 }), // ethereum, bsc, polygon, etc.
  websiteUrl: varchar("websiteUrl", { length: 512 }),
  twitterUrl: varchar("twitterUrl", { length: 512 }),
  telegramUrl: varchar("telegramUrl", { length: 512 }),
  discordUrl: varchar("discordUrl", { length: 512 }),

  // Audit status
  status: varchar("status", { length: 20 }).default("pending").notNull(),

  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().notNull(),
});

export type Project = typeof projects.$inferSelect;
export type InsertProject = typeof projects.$inferInsert;

/**
 * Audit Reports table - เก็บผลการตรวจสอบแต่ละด้าน
 */
export const auditReports = pgTable("auditReports", {
  id: serial("id").primaryKey(),
  projectId: integer("projectId").notNull(),

  // GitHub Analysis Scores (0-100)
  githubScore: integer("githubScore"),
  githubData: text("githubData"), // JSON string

  // Tokenomics & Contract Risk Scores (0-100)
  tokenomicsScore: integer("tokenomicsScore"),
  tokenomicsData: text("tokenomicsData"), // JSON string
  contractRiskScore: integer("contractRiskScore"),
  contractRiskData: text("contractRiskData"), // JSON string

  // Social Media Scores (0-100)
  twitterScore: integer("twitterScore"),
  twitterData: text("twitterData"), // JSON string
  telegramScore: integer("telegramScore"),
  telegramData: text("telegramData"), // JSON string
  discordScore: integer("discordScore"),
  discordData: text("discordData"), // JSON string

  // Overall Analysis
  overallScore: integer("overallScore"), // รวมคะแนนทั้งหมด (0-100)
  riskLevel: varchar("riskLevel", { length: 20 }),
  aiAnalysis: text("aiAnalysis"), // AI-generated summary and recommendations

  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().notNull(),
});

export type AuditReport = typeof auditReports.$inferSelect;
export type InsertAuditReport = typeof auditReports.$inferInsert;

/**
 * Watchlist table - บันทึกโปรเจกต์ที่ผู้ใช้สนใจ
 */
export const watchlist = pgTable("watchlist", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  projectId: integer("projectId").notNull(),
  addedAt: timestamp("addedAt").defaultNow().notNull(),
  notes: text("notes"),
  alertPrice: varchar("alertPrice", { length: 64 }),
  alertScore: integer("alertScore"),
});

export type Watchlist = typeof watchlist.$inferSelect;
export type InsertWatchlist = typeof watchlist.$inferInsert;

/**
 * Comparisons table - เก็บการเปรียบเทียบโปรเจกต์
 */
export const comparisons = pgTable("comparisons", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  name: varchar("name", { length: 255 }).notNull(),
  projectIds: text("projectIds").notNull(), // JSON array of project IDs
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().notNull(),
});

export type Comparison = typeof comparisons.$inferSelect;
export type InsertComparison = typeof comparisons.$inferInsert;

/**
 * Alert settings table - ตั้งค่าการแจ้งเตือน
 */
export const alertSettings = pgTable("alertSettings", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  projectId: integer("projectId").notNull(),
  priceChangePercent: integer("priceChangePercent"), // Alert if price changes by X%
  scoreChangePoints: integer("scoreChangePoints"), // Alert if score changes by X points
  enabled: integer("enabled").default(1).notNull(), // 1 = true, 0 = false
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type AlertSettings = typeof alertSettings.$inferSelect;
export type InsertAlertSettings = typeof alertSettings.$inferInsert;

/**
 * Unicorn Scans table - เก็บประวัติการสแกนหา Unicorn assets
 */
export const unicornScans = pgTable("unicornScans", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  scanType: varchar("scanType", { length: 64 }), // crypto, stocks, all
  status: varchar("status", { length: 20 }).default("pending").notNull(),
  candidatesFound: integer("candidatesFound").default(0),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  completedAt: timestamp("completedAt"),
});

export type UnicornScan = typeof unicornScans.$inferSelect;
export type InsertUnicornScan = typeof unicornScans.$inferInsert;

/**
 * Unicorn Candidates table - เก็บผลการวิเคราะห์ Unicorn assets
 */
export const unicornCandidates = pgTable("unicornCandidates", {
  id: serial("id").primaryKey(),
  scanId: integer("scanId").notNull(),
  symbol: varchar("symbol", { length: 64 }).notNull(),
  name: varchar("name", { length: 255 }),

  // Scanner metrics
  marketCap: integer("marketCap"),
  priceFromAth: integer("priceFromAth"), // % down from ATH
  volumeSpike: integer("volumeSpike"), // % above average
  currentPrice: varchar("currentPrice", { length: 64 }),

  // Researcher metrics
  githubScore: integer("githubScore"), // 0-100
  techScore: integer("techScore"), // 0-100
  socialScore: integer("socialScore"), // 0-100
  teamActive: integer("teamActive").default(0), // boolean as int

  // Sniper metrics
  rsiDivergence: integer("rsiDivergence").default(0), // boolean as int
  wyckoffSpring: integer("wyckoffSpring").default(0), // boolean as int
  entryPrice: varchar("entryPrice", { length: 64 }),
  stopLoss: varchar("stopLoss", { length: 64 }),
  takeProfit: varchar("takeProfit", { length: 64 }),

  // Final scores
  scannerScore: integer("scannerScore"), // 0-100
  fundamentalScore: integer("fundamentalScore"), // 0-100
  technicalScore: integer("technicalScore"), // 0-100
  unicornScore: integer("unicornScore"), // 0-100
  recommendation: varchar("recommendation", { length: 20 }),

  analysis: text("analysis"), // JSON string with full details

  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type UnicornCandidate = typeof unicornCandidates.$inferSelect;
export type InsertUnicornCandidate = typeof unicornCandidates.$inferInsert;

/**
 * TradingView Alerts table - เก็บการแจ้งเตือนจาก TradingView
 */
export const tradingViewAlerts = pgTable("tradingViewAlerts", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  symbol: varchar("symbol", { length: 64 }).notNull(),
  exchange: varchar("exchange", { length: 64 }).default("BINANCE"),
  action: varchar("action", { length: 20 }).notNull(), // BUY, SELL, HOLD
  price: varchar("price", { length: 64 }),
  indicators: text("indicators"), // JSON string with RSI, MACD, etc.
  message: text("message"),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
  processed: integer("processed").default(0), // 0 = false, 1 = true
});

export type TradingViewAlert = typeof tradingViewAlerts.$inferSelect;
export type InsertTradingViewAlert = typeof tradingViewAlerts.$inferInsert;

/**
 * Trading Signals table - เก็บสัญญาณการซื้อขายที่รวมกัน
 */
export const tradingSignals = pgTable("tradingSignals", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  projectId: integer("projectId"), // Link to audit project if available
  symbol: varchar("symbol", { length: 64 }).notNull(),
  signalType: varchar("signalType", { length: 20 }).notNull(), // BUY, SELL, HOLD

  // Signal sources
  tradingViewSignal: integer("tradingViewSignal").default(0), // boolean as int
  auditSignal: integer("auditSignal").default(0), // boolean as int
  geminiSignal: integer("geminiSignal").default(0), // boolean as int

  // Scores
  confidence: integer("confidence"), // 0-100
  auditScore: integer("auditScore"), // 0-100 from project audit
  technicalScore: integer("technicalScore"), // 0-100 from indicators

  // Trading recommendations
  entryPrice: varchar("entryPrice", { length: 64 }),
  stopLoss: varchar("stopLoss", { length: 64 }),
  takeProfit: varchar("takeProfit", { length: 64 }),
  positionSize: varchar("positionSize", { length: 64 }), // % of portfolio

  reasoning: text("reasoning"), // Combined AI reasoning
  riskLevel: varchar("riskLevel", { length: 20 }), // low, medium, high, critical

  status: varchar("status", { length: 20 }).default("active"), // active, executed, expired
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  expiresAt: timestamp("expiresAt"),
});

export type TradingSignal = typeof tradingSignals.$inferSelect;
export type InsertTradingSignal = typeof tradingSignals.$inferInsert;

/**
 * Market Data table - เก็บข้อมูลราคาล่าสุด
 */
export const marketData = pgTable("marketData", {
  id: serial("id").primaryKey(),
  symbol: varchar("symbol", { length: 64 }).notNull().unique(),
  price: varchar("price", { length: 64 }),
  change24h: varchar("change24h", { length: 64 }),
  volume24h: varchar("volume24h", { length: 64 }),
  marketCap: varchar("marketCap", { length: 64 }),
  high24h: varchar("high24h", { length: 64 }),
  low24h: varchar("low24h", { length: 64 }),
  ath: varchar("ath", { length: 64 }),
  athChange: varchar("athChange", { length: 64 }),
  lastUpdate: timestamp("lastUpdate").defaultNow().notNull(),
});

export type MarketData = typeof marketData.$inferSelect;
export type InsertMarketData = typeof marketData.$inferInsert;

/**
 * Notifications table - เก็บการแจ้งเตือนในระบบ
 */
export const notifications = pgTable("notifications", {
  id: serial("id").primaryKey(),
  userId: integer("userId").notNull(),
  type: varchar("type", { length: 20 }).notNull(), // info, warning, error, success
  title: varchar("title", { length: 255 }).notNull(),
  message: text("message").notNull(),
  data: text("data"), // JSON string with additional data
  read: integer("read").default(0), // 0 = false, 1 = true
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type Notification = typeof notifications.$inferSelect;
export type InsertNotification = typeof notifications.$inferInsert;