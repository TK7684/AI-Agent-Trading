import { describe, it, expect, beforeEach } from 'vitest';
import { useTradingStore } from '../stores/tradingStore';
import type { TradeLogEntry, PerformanceMetrics, AgentStatus } from '../types';

describe('TradingStore', () => {
	beforeEach(() => {
		useTradingStore.setState({
			performanceMetrics: null,
			tradingLogs: [],
			agentStatus: null,
			isLoadingMetrics: false,
			isLoadingLogs: false,
			isLoadingStatus: false,
		});
	});

	it('sets performance metrics', () => {
		const metrics: PerformanceMetrics = {
			totalPnl: 1000,
			dailyPnl: 100,
			winRate: 60,
			totalTrades: 10,
			currentDrawdown: 2,
			maxDrawdown: 5,
			portfolioValue: 11000,
			dailyChange: 100,
			dailyChangePercent: 1,
			lastUpdate: new Date(),
		};
		useTradingStore.getState().setPerformanceMetrics(metrics);
		expect(useTradingStore.getState().performanceMetrics).toEqual(metrics);
	});

	it('adds and updates trading logs', () => {
		const base: Omit<TradeLogEntry, 'id'> = {
			timestamp: new Date(),
			symbol: 'BTCUSDT',
			side: 'LONG',
			entryPrice: 100,
			quantity: 1,
			status: 'OPEN',
			confidence: 0.8,
		};
		const log: TradeLogEntry = { id: 't1', ...base };
		useTradingStore.getState().addTradingLog(log);
		expect(useTradingStore.getState().tradingLogs.length).toBe(1);

		useTradingStore.getState().updateTradingLog('t1', { status: 'CLOSED', exitPrice: 120, pnl: 20 });
		const updated = useTradingStore.getState().tradingLogs[0];
		expect(updated.status).toBe('CLOSED');
		expect(updated.exitPrice).toBe(120);
		expect(updated.pnl).toBe(20);
	});

	it('computes total PnL and win rate', () => {
		const now = new Date();
		const logs: TradeLogEntry[] = [
			{ id: '1', timestamp: now, symbol: 'A', side: 'LONG', entryPrice: 100, exitPrice: 110, quantity: 1, pnl: 10, status: 'CLOSED', confidence: 0.7 },
			{ id: '2', timestamp: now, symbol: 'B', side: 'SHORT', entryPrice: 200, exitPrice: 190, quantity: 1, pnl: 10, status: 'CLOSED', confidence: 0.7 },
			{ id: '3', timestamp: now, symbol: 'C', side: 'LONG', entryPrice: 50, status: 'OPEN', quantity: 1, confidence: 0.7 },
			{ id: '4', timestamp: now, symbol: 'D', side: 'LONG', entryPrice: 100, exitPrice: 90, quantity: 1, pnl: -10, status: 'CLOSED', confidence: 0.7 },
		];
		useTradingStore.getState().setTradingLogs(logs);
		expect(useTradingStore.getState().getTotalPnL()).toBe(10);
		expect(useTradingStore.getState().getWinRate()).toBeCloseTo((2 / 3) * 100);
		const active = useTradingStore.getState().getActivePositions();
		expect(active).toHaveLength(1);
		expect(active[0].id).toBe('3');
	});

	it('sets agent status and loading flags', () => {
		const status: AgentStatus = {
			state: 'running',
			uptime: 100,
			lastAction: new Date(),
			activePositions: 2,
			dailyTrades: 5,
			version: '1.0.0',
		};
		useTradingStore.getState().setAgentStatus(status);
		expect(useTradingStore.getState().agentStatus).toEqual(status);

		useTradingStore.getState().setLoadingMetrics(true);
		useTradingStore.getState().setLoadingLogs(true);
		useTradingStore.getState().setLoadingStatus(true);
		expect(useTradingStore.getState().isLoadingMetrics).toBe(true);
		expect(useTradingStore.getState().isLoadingLogs).toBe(true);
		expect(useTradingStore.getState().isLoadingStatus).toBe(true);
	});
});

