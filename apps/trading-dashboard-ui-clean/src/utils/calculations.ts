/**
 * Financial and trading calculation utility functions
 */

import type { TradeLogEntry, PerformanceMetrics, Position } from '../types/trading';

// P&L Calculations
export const calculatePnL = (entryPrice: number, exitPrice: number, quantity: number, side: 'LONG' | 'SHORT'): number => {
  if (side === 'LONG') {
    return (exitPrice - entryPrice) * quantity;
  } else {
    return (entryPrice - exitPrice) * quantity;
  }
};

export const calculateUnrealizedPnL = (entryPrice: number, currentPrice: number, quantity: number, side: 'LONG' | 'SHORT'): number => {
  return calculatePnL(entryPrice, currentPrice, quantity, side);
};

export const calculatePercentagePnL = (entryPrice: number, exitPrice: number, side: 'LONG' | 'SHORT'): number => {
  if (side === 'LONG') {
    return ((exitPrice - entryPrice) / entryPrice) * 100;
  } else {
    return ((entryPrice - exitPrice) / entryPrice) * 100;
  }
};

// Portfolio Calculations
export const calculatePortfolioValue = (positions: Position[], availableBalance: number): number => {
  const positionsValue = positions.reduce((total, position) => {
    return total + (position.currentPrice * position.size);
  }, 0);
  
  return positionsValue + availableBalance;
};

export const calculateTotalUnrealizedPnL = (positions: Position[]): number => {
  return positions.reduce((total, position) => total + position.unrealizedPnl, 0);
};

export const calculateTotalRealizedPnL = (positions: Position[]): number => {
  return positions.reduce((total, position) => total + position.realizedPnl, 0);
};

// Performance Metrics Calculations
export const calculateWinRate = (trades: TradeLogEntry[]): number => {
  const closedTrades = trades.filter(trade => trade.status === 'CLOSED' && trade.pnl !== undefined);
  if (closedTrades.length === 0) return 0;
  
  const winningTrades = closedTrades.filter(trade => (trade.pnl || 0) > 0);
  return (winningTrades.length / closedTrades.length) * 100;
};

export const calculateAverageWin = (trades: TradeLogEntry[]): number => {
  const winningTrades = trades.filter(trade => 
    trade.status === 'CLOSED' && 
    trade.pnl !== undefined && 
    trade.pnl > 0
  );
  
  if (winningTrades.length === 0) return 0;
  
  const totalWins = winningTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0);
  return totalWins / winningTrades.length;
};

export const calculateAverageLoss = (trades: TradeLogEntry[]): number => {
  const losingTrades = trades.filter(trade => 
    trade.status === 'CLOSED' && 
    trade.pnl !== undefined && 
    trade.pnl < 0
  );
  
  if (losingTrades.length === 0) return 0;
  
  const totalLosses = losingTrades.reduce((sum, trade) => sum + Math.abs(trade.pnl || 0), 0);
  return totalLosses / losingTrades.length;
};

export const calculateProfitFactor = (trades: TradeLogEntry[]): number => {
  const averageWin = calculateAverageWin(trades);
  const averageLoss = calculateAverageLoss(trades);
  
  if (averageLoss === 0) return averageWin > 0 ? Infinity : 0;
  return averageWin / averageLoss;
};

// Drawdown Calculations
export const calculateMaxDrawdown = (trades: TradeLogEntry[]): { maxDrawdown: number; currentDrawdown: number } => {
  const sortedTrades = trades
    .filter(trade => trade.status === 'CLOSED' && trade.pnl !== undefined)
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  
  let peak = 0;
  let currentValue = 0;
  let maxDrawdown = 0;
  let currentDrawdown = 0;
  
  for (const trade of sortedTrades) {
    currentValue += trade.pnl || 0;
    
    if (currentValue > peak) {
      peak = currentValue;
      currentDrawdown = 0;
    } else {
      currentDrawdown = ((peak - currentValue) / peak) * 100;
      maxDrawdown = Math.max(maxDrawdown, currentDrawdown);
    }
  }
  
  return { maxDrawdown, currentDrawdown };
};

// Risk Calculations
export const calculatePositionSize = (
  accountBalance: number,
  riskPercentage: number,
  entryPrice: number,
  stopLossPrice: number
): number => {
  const riskAmount = accountBalance * (riskPercentage / 100);
  const priceRisk = Math.abs(entryPrice - stopLossPrice);
  
  if (priceRisk === 0) return 0;
  
  return riskAmount / priceRisk;
};

export const calculateRiskRewardRatio = (
  entryPrice: number,
  stopLossPrice: number,
  takeProfitPrice: number,
  side: 'LONG' | 'SHORT'
): number => {
  let risk: number;
  let reward: number;
  
  if (side === 'LONG') {
    risk = entryPrice - stopLossPrice;
    reward = takeProfitPrice - entryPrice;
  } else {
    risk = stopLossPrice - entryPrice;
    reward = entryPrice - takeProfitPrice;
  }
  
  if (risk <= 0) return 0;
  return reward / risk;
};

// Technical Analysis Calculations
export const calculateSMA = (prices: number[], period: number): number[] => {
  const sma: number[] = [];
  
  for (let i = period - 1; i < prices.length; i++) {
    const sum = prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    sma.push(sum / period);
  }
  
  return sma;
};

export const calculateEMA = (prices: number[], period: number): number[] => {
  const ema: number[] = [];
  const multiplier = 2 / (period + 1);
  
  // First EMA is SMA
  const firstSMA = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  ema.push(firstSMA);
  
  for (let i = period; i < prices.length; i++) {
    const currentEMA = (prices[i] - ema[ema.length - 1]) * multiplier + ema[ema.length - 1];
    ema.push(currentEMA);
  }
  
  return ema;
};

export const calculateRSI = (prices: number[], period: number = 14): number[] => {
  const rsi: number[] = [];
  const gains: number[] = [];
  const losses: number[] = [];
  
  // Calculate price changes
  for (let i = 1; i < prices.length; i++) {
    const change = prices[i] - prices[i - 1];
    gains.push(change > 0 ? change : 0);
    losses.push(change < 0 ? Math.abs(change) : 0);
  }
  
  // Calculate initial averages
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
  
  // Calculate RSI
  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsiValue = 100 - (100 / (1 + rs));
    rsi.push(rsiValue);
  }
  
  return rsi;
};

// Volatility Calculations
export const calculateVolatility = (prices: number[], period: number = 20): number => {
  if (prices.length < period) return 0;
  
  const returns = [];
  for (let i = 1; i < prices.length; i++) {
    returns.push(Math.log(prices[i] / prices[i - 1]));
  }
  
  const recentReturns = returns.slice(-period);
  const mean = recentReturns.reduce((a, b) => a + b, 0) / recentReturns.length;
  
  const variance = recentReturns.reduce((sum, ret) => sum + Math.pow(ret - mean, 2), 0) / recentReturns.length;
  
  return Math.sqrt(variance * 252); // Annualized volatility
};

// Sharpe Ratio Calculation
export const calculateSharpeRatio = (returns: number[], riskFreeRate: number = 0.02): number => {
  if (returns.length === 0) return 0;
  
  const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
  const excessReturn = avgReturn - riskFreeRate / 252; // Daily risk-free rate
  
  const variance = returns.reduce((sum, ret) => sum + Math.pow(ret - avgReturn, 2), 0) / returns.length;
  const stdDev = Math.sqrt(variance);
  
  return stdDev === 0 ? 0 : excessReturn / stdDev;
};

// Trade Duration Calculations
export const calculateAverageTradeDuration = (trades: TradeLogEntry[]): number => {
  const closedTrades = trades.filter(trade => 
    trade.status === 'CLOSED' && 
    trade.duration !== undefined
  );
  
  if (closedTrades.length === 0) return 0;
  
  const totalDuration = closedTrades.reduce((sum, trade) => sum + (trade.duration || 0), 0);
  return totalDuration / closedTrades.length;
};

// Performance Metrics Aggregation
export const calculatePerformanceMetrics = (
  trades: TradeLogEntry[],
  positions: Position[],
  availableBalance: number
): PerformanceMetrics => {
  const closedTrades = trades.filter(trade => trade.status === 'CLOSED' && trade.pnl !== undefined);
  const totalPnl = closedTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0);
  
  const today = new Date();
  const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const dailyTrades = closedTrades.filter(trade => trade.timestamp >= startOfDay);
  const dailyPnl = dailyTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0);
  
  const portfolioValue = calculatePortfolioValue(positions, availableBalance);
  const { maxDrawdown, currentDrawdown } = calculateMaxDrawdown(closedTrades);
  
  return {
    totalPnl,
    dailyPnl,
    winRate: calculateWinRate(closedTrades),
    totalTrades: closedTrades.length,
    currentDrawdown,
    maxDrawdown,
    portfolioValue,
    dailyChange: dailyPnl,
    dailyChangePercent: portfolioValue > 0 ? (dailyPnl / portfolioValue) * 100 : 0,
    lastUpdate: new Date(),
  };
};