import { describe, it, expect, beforeEach } from 'vitest';
import { useSystemStore } from '../stores/systemStore';
import type { SystemHealth } from '../types';

describe('SystemStore', () => {
	beforeEach(() => {
		useSystemStore.setState({
			systemHealth: null,
			isConnected: false,
			connectionStatus: { websocket: false, api: false, database: false, broker: false, llm: false },
			isLoadingHealth: false,
		});
	});

	it('sets system health and computes overall health score', () => {
		const health: SystemHealth = {
			cpu: 20,
			memory: 30,
			diskUsage: 40,
			networkLatency: 50,
			errorRate: 1,
			uptime: 1000,
			connections: { database: true, broker: true, llm: true, websocket: true },
			lastUpdate: new Date(),
		};
		useSystemStore.getState().setSystemHealth(health);
		expect(useSystemStore.getState().systemHealth).toEqual(health);
		const score = useSystemStore.getState().getOverallHealthScore();
		expect(score).toBeGreaterThan(0);
		expect(score).toBeLessThanOrEqual(100);
	});

	it('updates connection status and reports critical issues', () => {
		useSystemStore.getState().setConnectionStatus({ database: false, broker: false, llm: false });
		const issues = useSystemStore.getState().getCriticalIssues();
		expect(issues).toEqual(expect.arrayContaining([
			'Database connection lost',
			'Broker connection lost',
			'LLM service unavailable',
		]));
	});

	it('sets connectivity and loading flags', () => {
		useSystemStore.getState().setIsConnected(true);
		useSystemStore.getState().setLoadingHealth(true);
		expect(useSystemStore.getState().isConnected).toBe(true);
		expect(useSystemStore.getState().isLoadingHealth).toBe(true);
	});
});

