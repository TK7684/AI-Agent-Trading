import React, { useEffect } from 'react';
import './Dashboard.css';
import DashboardGrid from '@components/Dashboard/Grid/DashboardGrid';
import WidgetLibrary from '@components/Dashboard/WidgetLibrary';
import type { ChartData, TradeLogEntry } from '@/types/trading';
import type { AgentStatus, SystemHealth } from '@/types/system';
import { syncService } from '@/services/syncService';

const demoChartData: ChartData = {
	symbol: 'BTCUSDT',
	timeframe: '1h',
	data: [
		{ time: Math.floor(Date.now() / 1000) - 3600 * 4, open: 100, high: 105, low: 95, close: 102, volume: 1000 },
		{ time: Math.floor(Date.now() / 1000) - 3600 * 3, open: 102, high: 108, low: 101, close: 107, volume: 1200 },
		{ time: Math.floor(Date.now() / 1000) - 3600 * 2, open: 107, high: 110, low: 103, close: 104, volume: 900 },
		{ time: Math.floor(Date.now() / 1000) - 3600 * 1, open: 104, high: 106, low: 100, close: 101, volume: 800 },
	],
	indicators: [
		{ type: 'MA', name: 'MA(9)', data: [
			{ time: Math.floor(Date.now() / 1000) - 3600 * 4, value: 100 },
			{ time: Math.floor(Date.now() / 1000) - 3600 * 3, value: 104 },
			{ time: Math.floor(Date.now() / 1000) - 3600 * 2, value: 105 },
			{ time: Math.floor(Date.now() / 1000) - 3600 * 1, value: 103 },
		], config: {} },
	],
	signals: [
		{ time: Math.floor(Date.now() / 1000) - 3600 * 3, position: 'belowBar', color: 'green', shape: 'arrowUp', text: 'BUY' },
		{ time: Math.floor(Date.now() / 1000) - 3600 * 2, position: 'aboveBar', color: 'red', shape: 'arrowDown', text: 'SELL' },
	],
	lastUpdate: new Date(),
};

const demoTrades: TradeLogEntry[] = [
	{ id: '1', timestamp: new Date(Date.now() - 86400000), symbol: 'BTCUSDT', side: 'LONG', entryPrice: 100, exitPrice: 110, quantity: 0.5, pnl: 5, status: 'CLOSED', confidence: 75, fees: 0.1 },
	{ id: '2', timestamp: new Date(Date.now() - 43200000), symbol: 'ETHUSDT', side: 'SHORT', entryPrice: 2000, exitPrice: 1950, quantity: 1, pnl: 50, status: 'CLOSED', confidence: 65, fees: 0.2 },
	{ id: '3', timestamp: new Date(Date.now() - 3600000), symbol: 'BTCUSDT', side: 'LONG', entryPrice: 105, quantity: 0.2, status: 'OPEN', confidence: 60 },
	{ id: '4', timestamp: new Date(Date.now() - 7200000), symbol: 'SOLUSDT', side: 'LONG', entryPrice: 30, exitPrice: 28, quantity: 10, pnl: -20, status: 'CLOSED', confidence: 70 },
];

const mockStatus: AgentStatus = { state: 'stopped', uptime: 0, lastAction: new Date(), activePositions: 0, dailyTrades: 0, version: '1.0.0' };

const demoHealth: SystemHealth = {
	cpu: 42,
	memory: 67,
	diskUsage: 55,
	networkLatency: 220,
	errorRate: 1.5,
	uptime: 123456,
	connections: { database: true, broker: true, llm: false, websocket: true },
	lastUpdate: new Date(),
};

const Dashboard: React.FC = () => {
  useEffect(() => {
    syncService.initialize().then(() => syncService.connect()).catch(console.error);
  }, []);

  return (
    <div className="dashboard">
      <div className="mb-4">
        <WidgetLibrary />
      </div>
      <DashboardGrid chartData={demoChartData} trades={demoTrades} agentStatus={mockStatus} health={demoHealth} />
    </div>
  );
};

export { Dashboard };
export default Dashboard;