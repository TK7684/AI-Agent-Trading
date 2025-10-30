/**
 * Test file for types and schemas validation
 */

import { describe, it, expect } from 'vitest';
import {
  validatePerformanceMetrics,
  validateTradeLogEntry,
  validateTradingSignal,
  validateSystemHealth,
  validateAgentStatus,
  validateNotification,
} from '../schemas';
import type {
  PerformanceMetrics,
  TradeLogEntry,
  TradingSignal,
  SystemHealth,
  AgentStatus,
  Notification,
} from '../types';

describe('Trading Types and Schemas', () => {
  it('should validate performance metrics correctly', () => {
    const validMetrics: PerformanceMetrics = {
      totalPnl: 1500.50,
      dailyPnl: 250.75,
      winRate: 65.5,
      totalTrades: 42,
      currentDrawdown: 5.2,
      maxDrawdown: 12.8,
      portfolioValue: 50000,
      dailyChange: 250.75,
      dailyChangePercent: 0.5,
      lastUpdate: new Date(),
    };

    const result = validatePerformanceMetrics(validMetrics);
    expect(result.success).toBe(true);
  });

  it('should validate trade log entry correctly', () => {
    const validTrade: TradeLogEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      symbol: 'BTCUSDT',
      side: 'LONG',
      entryPrice: 45000,
      exitPrice: 46000,
      quantity: 0.1,
      pnl: 100,
      status: 'CLOSED',
      pattern: 'Bullish Engulfing',
      confidence: 85.5,
      duration: 3600000, // 1 hour in ms
      fees: 5.50,
    };

    const result = validateTradeLogEntry(validTrade);
    expect(result.success).toBe(true);
  });

  it('should validate trading signal correctly', () => {
    const validSignal: TradingSignal = {
      id: crypto.randomUUID(),
      symbol: 'ETHUSDT',
      type: 'BUY',
      confidence: 78.2,
      pattern: 'Golden Cross',
      timestamp: new Date(),
      price: 2500.50,
      reasoning: 'Strong bullish momentum with volume confirmation',
    };

    const result = validateTradingSignal(validSignal);
    expect(result.success).toBe(true);
  });

  it('should validate system health correctly', () => {
    const validHealth: SystemHealth = {
      cpu: 45.2,
      memory: 68.7,
      diskUsage: 32.1,
      networkLatency: 25,
      errorRate: 0.5,
      uptime: 86400, // 1 day in seconds
      connections: {
        database: true,
        broker: true,
        llm: true,
        websocket: true,
      },
      lastUpdate: new Date(),
    };

    const result = validateSystemHealth(validHealth);
    expect(result.success).toBe(true);
  });

  it('should validate agent status correctly', () => {
    const validStatus: AgentStatus = {
      state: 'running',
      uptime: 7200, // 2 hours
      lastAction: new Date(),
      activePositions: 3,
      dailyTrades: 15,
      version: '1.0.0',
      configHash: 'abc123def456',
    };

    const result = validateAgentStatus(validStatus);
    expect(result.success).toBe(true);
  });

  it('should validate notification correctly', () => {
    const validNotification: Notification = {
      id: crypto.randomUUID(),
      type: 'trade',
      title: 'Trade Executed',
      message: 'Successfully opened LONG position on BTCUSDT',
      timestamp: new Date(),
      read: false,
      persistent: false,
      priority: 'normal',
      category: 'trading',
    };

    const result = validateNotification(validNotification);
    expect(result.success).toBe(true);
  });

  it('should reject invalid data', () => {
    const invalidMetrics = {
      totalPnl: 'invalid', // Should be number
      winRate: 150, // Should be <= 100
      totalTrades: -5, // Should be >= 0
    };

    const result = validatePerformanceMetrics(invalidMetrics);
    expect(result.success).toBe(false);
  });
});

describe('Utility Functions', () => {
  it('should format currency correctly', async () => {
    const { formatCurrency } = await import('../utils/formatters');
    
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
    expect(formatCurrency(-500.25)).toBe('-$500.25');
  });

  it('should calculate P&L correctly', async () => {
    const { calculatePnL } = await import('../utils/calculations');
    
    // LONG position profit
    expect(calculatePnL(100, 110, 10, 'LONG')).toBe(100);
    
    // SHORT position profit
    expect(calculatePnL(110, 100, 10, 'SHORT')).toBe(100);
    
    // LONG position loss
    expect(calculatePnL(110, 100, 10, 'LONG')).toBe(-100);
  });

  it('should calculate win rate correctly', async () => {
    const { calculateWinRate } = await import('../utils/calculations');
    
    const trades: TradeLogEntry[] = [
      {
        id: '1',
        timestamp: new Date(),
        symbol: 'BTCUSDT',
        side: 'LONG',
        entryPrice: 100,
        quantity: 1,
        status: 'CLOSED',
        confidence: 80,
        pnl: 10, // Win
      },
      {
        id: '2',
        timestamp: new Date(),
        symbol: 'ETHUSDT',
        side: 'LONG',
        entryPrice: 100,
        quantity: 1,
        status: 'CLOSED',
        confidence: 75,
        pnl: -5, // Loss
      },
    ];
    
    expect(calculateWinRate(trades)).toBe(50); // 1 win out of 2 trades = 50%
  });
});