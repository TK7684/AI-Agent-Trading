/**
 * Trading-related TypeScript interfaces and types
 */

export interface PerformanceMetrics {
  totalPnl: number;
  dailyPnl: number;
  winRate: number;
  totalTrades: number;
  currentDrawdown: number;
  maxDrawdown: number;
  portfolioValue: number;
  dailyChange: number;
  dailyChangePercent: number;
  lastUpdate: Date;
}

export interface TradeLogEntry {
  id: string;
  timestamp: Date;
  symbol: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  pnl?: number;
  status: 'OPEN' | 'CLOSED' | 'CANCELLED';
  pattern?: string;
  confidence: number;
  duration?: number; // in milliseconds
  fees?: number;
}

export interface TradingSignal {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  confidence: number;
  pattern: string;
  timestamp: Date;
  price: number;
  reasoning?: string;
}

export interface Portfolio {
  totalValue: number;
  availableBalance: number;
  positions: Position[];
  dailyPnl: number;
  totalPnl: number;
  lastUpdate: Date;
}

export interface Position {
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  timestamp: Date;
}

export interface ChartData {
  symbol: string;
  timeframe: string;
  data: CandlestickData[];
  indicators: IndicatorData[];
  signals: SignalMarker[];
  lastUpdate: Date;
}

export interface CandlestickData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorData {
  type: 'MA' | 'RSI' | 'MACD' | 'BOLLINGER';
  name: string;
  data: IndicatorPoint[];
  config: Record<string, any>;
}

export interface IndicatorPoint {
  time: number;
  value: number | Record<string, number>;
}

export interface SignalMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown' | 'circle';
  text: string;
  signalId?: string;
}

export interface LogFilter {
  dateRange: { start: Date; end: Date };
  symbols: string[];
  status: ('OPEN' | 'CLOSED' | 'CANCELLED')[];
  profitLoss: 'all' | 'profit' | 'loss';
  searchText: string;
}

export type TradeStatus = 'OPEN' | 'CLOSED' | 'CANCELLED';
export type TradeSide = 'LONG' | 'SHORT';
export type SignalType = 'BUY' | 'SELL';
export type Timeframe = '15m' | '1h' | '4h' | '1d';