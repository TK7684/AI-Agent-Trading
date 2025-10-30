/**
 * Zod validation schemas for system-related data
 */

import { z } from 'zod';

// Base schemas
export const AgentStateSchema = z.enum(['running', 'paused', 'stopped', 'error', 'starting', 'stopping']);
export const AlertSeveritySchema = z.enum(['low', 'medium', 'high', 'critical']);
export const SystemStateSchema = z.enum(['healthy', 'warning', 'critical', 'unknown']);

// Connection Status Schema
export const ConnectionStatusSchema = z.object({
  database: z.boolean(),
  broker: z.boolean(),
  llm: z.boolean(),
  websocket: z.boolean(),
});

// System Health Schema
export const SystemHealthSchema = z.object({
  cpu: z.number().min(0).max(100),
  memory: z.number().min(0).max(100),
  diskUsage: z.number().min(0).max(100),
  networkLatency: z.number().min(0),
  errorRate: z.number().min(0).max(100),
  uptime: z.number().int().min(0),
  connections: ConnectionStatusSchema,
  lastUpdate: z.date(),
});

// System Alert Schema
export const SystemAlertSchema = z.object({
  id: z.string().uuid(),
  type: z.enum(['performance', 'connection', 'error', 'warning']),
  severity: AlertSeveritySchema,
  title: z.string().min(1).max(200),
  message: z.string().min(1).max(1000),
  timestamp: z.date(),
  resolved: z.boolean(),
  source: z.string().min(1).max(100),
});

// Risk Limits Schema
export const RiskLimitsSchema = z.object({
  maxDailyLoss: z.number().positive(),
  maxDrawdown: z.number().min(0).max(100),
  maxPositions: z.number().int().positive(),
  maxPositionSize: z.number().positive(),
  stopLossPercent: z.number().min(0).max(100),
  takeProfitPercent: z.number().min(0).max(100),
});

// Trading Hours Schema
export const TradingHoursSchema = z.object({
  enabled: z.boolean(),
  start: z.string().regex(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/, "Invalid time format (HH:MM)"),
  end: z.string().regex(/^([01]?[0-9]|2[0-3]):[0-5][0-9]$/, "Invalid time format (HH:MM)"),
  timezone: z.string().min(1),
  weekendsEnabled: z.boolean(),
});

// LLM Config Schema
export const LLMConfigSchema = z.object({
  provider: z.string().min(1),
  model: z.string().min(1),
  temperature: z.number().min(0).max(2),
  maxTokens: z.number().int().positive(),
  timeout: z.number().int().positive(),
});

// Agent Config Schema
export const AgentConfigSchema = z.object({
  symbols: z.array(z.string().min(1).max(20)).min(1),
  timeframes: z.array(z.enum(['15m', '1h', '4h', '1d'])).min(1),
  riskLimits: RiskLimitsSchema,
  tradingHours: TradingHoursSchema,
  llmConfig: LLMConfigSchema,
  enabled: z.boolean(),
});

// Agent Status Schema
export const AgentStatusSchema = z.object({
  state: AgentStateSchema,
  uptime: z.number().int().min(0),
  lastAction: z.date(),
  activePositions: z.number().int().min(0),
  dailyTrades: z.number().int().min(0),
  version: z.string().min(1),
  configHash: z.string().optional(),
});

// System Performance Metrics Schema
export const SystemPerformanceMetricsSchema = z.object({
  responseTime: z.number().min(0),
  successRate: z.number().min(0).max(100),
  errorCount: z.number().int().min(0),
  requestCount: z.number().int().min(0),
  lastHour: z.object({
    requests: z.number().int().min(0),
    errors: z.number().int().min(0),
    avgResponseTime: z.number().min(0),
  }),
});

// Database Metrics Schema
export const DatabaseMetricsSchema = z.object({
  connectionCount: z.number().int().min(0),
  queryTime: z.number().min(0),
  slowQueries: z.number().int().min(0),
  connectionPool: z.object({
    active: z.number().int().min(0),
    idle: z.number().int().min(0),
    total: z.number().int().min(0),
  }),
});

// Broker Metrics Schema
export const BrokerMetricsSchema = z.object({
  connectionStatus: z.boolean(),
  latency: z.number().min(0),
  orderExecutionTime: z.number().min(0),
  failedOrders: z.number().int().min(0),
  successfulOrders: z.number().int().min(0),
});

// Validation helper functions
export const validateSystemHealth = (data: unknown) => {
  return SystemHealthSchema.safeParse(data);
};

export const validateSystemAlert = (data: unknown) => {
  return SystemAlertSchema.safeParse(data);
};

export const validateAgentStatus = (data: unknown) => {
  return AgentStatusSchema.safeParse(data);
};

export const validateAgentConfig = (data: unknown) => {
  return AgentConfigSchema.safeParse(data);
};

export const validateRiskLimits = (data: unknown) => {
  return RiskLimitsSchema.safeParse(data);
};

export const validateTradingHours = (data: unknown) => {
  return TradingHoursSchema.safeParse(data);
};

export const validateLLMConfig = (data: unknown) => {
  return LLMConfigSchema.safeParse(data);
};

export const validateSystemPerformanceMetrics = (data: unknown) => {
  return SystemPerformanceMetricsSchema.safeParse(data);
};

export const validateDatabaseMetrics = (data: unknown) => {
  return DatabaseMetricsSchema.safeParse(data);
};

export const validateBrokerMetrics = (data: unknown) => {
  return BrokerMetricsSchema.safeParse(data);
};

// Type inference from schemas
export type SystemHealthType = z.infer<typeof SystemHealthSchema>;
export type SystemAlertType = z.infer<typeof SystemAlertSchema>;
export type AgentStatusType = z.infer<typeof AgentStatusSchema>;
export type AgentConfigType = z.infer<typeof AgentConfigSchema>;
export type RiskLimitsType = z.infer<typeof RiskLimitsSchema>;
export type TradingHoursType = z.infer<typeof TradingHoursSchema>;
export type LLMConfigType = z.infer<typeof LLMConfigSchema>;
export type SystemPerformanceMetricsType = z.infer<typeof SystemPerformanceMetricsSchema>;
export type DatabaseMetricsType = z.infer<typeof DatabaseMetricsSchema>;
export type BrokerMetricsType = z.infer<typeof BrokerMetricsSchema>;