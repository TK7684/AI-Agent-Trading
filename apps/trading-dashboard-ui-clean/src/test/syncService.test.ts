import { describe, it, expect, beforeEach, vi } from 'vitest';
import { syncService } from '@services/syncService';
import { useTradingStore } from '@stores/tradingStore';
import { useSystemStore } from '@stores/systemStore';

const originalFetch = global.fetch;

describe('syncService', () => {
	beforeEach(() => {
		useTradingStore.setState({ performanceMetrics: null, tradingLogs: [], agentStatus: null, isLoadingMetrics: false, isLoadingLogs: false, isLoadingStatus: false });
		useSystemStore.setState({ systemHealth: null, isConnected: false, connectionStatus: { websocket: false, api: false, database: false, broker: false, llm: false }, isLoadingHealth: false });
		(global as any).fetch = vi.fn(async (url: any) => {
			if (String(url).includes('/trading/performance')) return new Response(JSON.stringify({ totalPnl: 1, dailyPnl: 1, winRate: 50, totalTrades: 1, currentDrawdown: 0, maxDrawdown: 0, portfolioValue: 100, dailyChange: 1, dailyChangePercent: 1, lastUpdate: new Date() }), { status: 200, headers: { 'Content-Type': 'application/json' } as any });
			if (String(url).includes('/trading/trades')) return new Response(JSON.stringify({ items: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } as any });
			if (String(url).includes('/system/agents')) return new Response(JSON.stringify({ state: 'running', uptime: 0, lastAction: new Date(), activePositions: 0, dailyTrades: 0, version: '1.0.0' }), { status: 200, headers: { 'Content-Type': 'application/json' } as any });
			if (String(url).includes('/system/health')) return new Response(JSON.stringify({ cpu: 1, memory: 1, diskUsage: 1, networkLatency: 1, errorRate: 0, uptime: 0, connections: { database: true, broker: true, llm: true, websocket: true }, lastUpdate: new Date() }), { status: 200, headers: { 'Content-Type': 'application/json' } as any });
			return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } as any });
		});
	});

	it('initializes stores from API', async () => {
		await syncService.initialize();
		expect(useTradingStore.getState().performanceMetrics).not.toBeNull();
		expect(useSystemStore.getState().systemHealth).not.toBeNull();
	});
});
