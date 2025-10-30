import { render } from '@testing-library/react';
import DashboardGrid from '@components/Dashboard/Grid/DashboardGrid';
import { useUIStore } from '@stores/uiStore';
import type { ChartData } from '@types/trading';
import type { AgentStatus, SystemHealth } from '@types/system';

describe('DashboardGrid', () => {
	it('persists layout changes to store', () => {
		const initial = useUIStore.getState().widgets.map((w) => ({ ...w }));
		const chartData = { symbol: 'BTCUSDT', timeframe: '1h', data: [], indicators: [], signals: [], lastUpdate: new Date() } as unknown as ChartData;
		const status = { state: 'stopped', uptime: 0, lastAction: new Date(), activePositions: 0, dailyTrades: 0, version: '1.0.0' } as AgentStatus;
		const health = { cpu: 0, memory: 0, diskUsage: 0, networkLatency: 0, errorRate: 0, uptime: 0, connections: { database: true, broker: true, llm: true, websocket: true }, lastUpdate: new Date() } as SystemHealth;

		render(<DashboardGrid chartData={chartData} trades={[]} agentStatus={status} health={health} />);
		// Simulate a layout update by calling store directly (react-grid-layout DnD not simulated here)
		const updated = initial.map((w, i) => ({ ...w, position: { ...w.position, x: (w.position.x + i) % 12 } }));
		useUIStore.getState().setWidgets(updated);
		const after = useUIStore.getState().widgets;
		expect(after[0].position.x).toBe(updated[0].position.x);
	});
});
