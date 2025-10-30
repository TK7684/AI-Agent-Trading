/**
 * Zod validation schemas for trading-related data
 */

import { z } from 'zod';

// Base schemas
export const TradeSideSchema = z.enum(['LONG', 'SHORT']);
export const TradeStatusSchema = z.enum(['OPEN', 'CLOSED', 'CANCELLED']);
export const SignalTypeSchema = z.enum(['BUY', 'SELL']);
export const TimeframeSchema = z.enum(['15m', '1h', '4h', '1d']);

// Performance Metrics Schema
export const PerformanceMetricsSchema = z.object({
  totalPnl: z.number(),
  dailyPnl: z.number(),
  winRate: z.number().min(0).max(100),
  totalTrades: z.number().int().min(0),
  currentDrawdown: z.number().min(0),
  maxDrawdown: z.number().min(0),
  portfolioValue: z.number().positive(),
  dailyChange: z.number(),
  dailyChangePercent: z.number(),
  lastUpdate: z.date(),
});

// Trade Log Entry Schema
export const TradeLogEntrySchema = z.object({
  id: z.string().uuid(),
  timestamp: z.date(),
  symbol: z.string().min(1).max(20),
  side: TradeSideSchema,
  entryPrice: z.number().positive(),
  exitPrice: z.number().positive().optional(),
  quantity: z.number().positive(),
  pnl: z.number().optional(),
  status: TradeStatusSchema,
  pattern: z.string().optional(),
  confidence: z.number().min(0).max(100),
  duration: z.number().int().min(0).optional(),
  fees: z.number().min(0).optional(),
});

// Trading Signal Schema
export const TradingSignalSchema = z.object({
  id: z.string().uuid(),
  symbol: z.string().min(1).max(20),
  type: SignalTypeSchema,
  confidence: z.number().min(0).max(100),
  pattern: z.string().min(1),
  timestamp: z.date(),
  price: z.number().positive(),
  reasoning: z.string().optional(),
});

// Position Schema
export const PositionSchema = z.object({
  symbol: z.string().min(1).max(20),
  side: TradeSideSchema,
  size: z.number().positive(),
  entryPrice: z.number().positive(),
  currentPrice: z.number().positive(),
  unrealizedPnl: z.number(),
  realizedPnl: z.number(),
  timestamp: z.date(),
});

// Portfolio Schema
export const PortfolioSchema = z.object({
  totalValue: z.number().positive(),
  availableBalance: z.number().min(0),
  positions: z.array(PositionSchema),
  dailyPnl: z.number(),
  totalPnl: z.number(),
  lastUpdate: z.date(),
});

// Candlestick Data Schema
export const CandlestickDataSchema = z.object({
  time: z.number().int().positive(),
  open: z.number().positive(),
  high: z.number().positive(),
  low: z.number().positive(),
  close: z.number().positive(),
  volume: z.number().min(0),
}).refine(data => data.high >= Math.max(data.open, data.close), {
  message: "High must be >= max(open, close)",
}).refine(data => data.low <= Math.min(data.open, data.close), {
  message: "Low must be <= min(open, close)",
});

// Indicator Point Schema
export const IndicatorPointSchema = z.object({
  time: z.number().int().positive(),
  value: z.union([z.number(), z.record(z.string(), z.number())]),
});

// Indicator Data Schema
export const IndicatorDataSchema = z.object({
  type: z.enum(['MA', 'RSI', 'MACD', 'BOLLINGER']),
  name: z.string().min(1),
  data: z.array(IndicatorPointSchema),
  config: z.record(z.string(), z.any()),
});

// Signal Marker Schema
export const SignalMarkerSchema = z.object({
  time: z.number().int().positive(),
  position: z.enum(['aboveBar', 'belowBar']),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  shape: z.enum(['arrowUp', 'arrowDown', 'circle']),
  text: z.string().min(1),
  signalId: z.string().uuid().optional(),
});

// Chart Data Schema
export const ChartDataSchema = z.object({
  symbol: z.string().min(1).max(20),
  timeframe: TimeframeSchema,
  data: z.array(CandlestickDataSchema),
  indicators: z.array(IndicatorDataSchema),
  signals: z.array(SignalMarkerSchema),
  lastUpdate: z.date(),
});

// Log Filter Schema
export const LogFilterSchema = z.object({
  dateRange: z.object({
    start: z.date(),
    end: z.date(),
  }).refine(data => data.start <= data.end, {
    message: "Start date must be before or equal to end date",
  }),
  symbols: z.array(z.string().min(1).max(20)),
  status: z.array(TradeStatusSchema),
  profitLoss: z.enum(['all', 'profit', 'loss']),
  searchText: z.string(),
});

// Validation helper functions
export const validatePerformanceMetrics = (data: unknown) => {
  return PerformanceMetricsSchema.safeParse(data);
};

export const validateTradeLogEntry = (data: unknown) => {
  return TradeLogEntrySchema.safeParse(data);
};

export const validateTradingSignal = (data: unknown) => {
  return TradingSignalSchema.safeParse(data);
};

export const validatePortfolio = (data: unknown) => {
  return PortfolioSchema.safeParse(data);
};

export const validateChartData = (data: unknown) => {
  return ChartDataSchema.safeParse(data);
};

export const validateLogFilter = (data: unknown) => {
  return LogFilterSchema.safeParse(data);
};

// Type inference from schemas
export type PerformanceMetricsType = z.infer<typeof PerformanceMetricsSchema>;
export type TradeLogEntryType = z.infer<typeof TradeLogEntrySchema>;
export type TradingSignalType = z.infer<typeof TradingSignalSchema>;
export type PortfolioType = z.infer<typeof PortfolioSchema>;
export type ChartDataType = z.infer<typeof ChartDataSchema>;
export type LogFilterType = z.infer<typeof LogFilterSchema>;