import { render, screen } from '@testing-library/react';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import type { ChartData } from '@types/trading';

describe('TradingChartsWidget', () => {
	it('renders header with symbol and timeframe', () => {
		const data: ChartData = {
			symbol: 'BTCUSDT',
			timeframe: '1h',
			data: [
				{ time: Math.floor(Date.now() / 1000) - 3600 * 2, open: 1, high: 2, low: 0.5, close: 1.5, volume: 1000 },
				{ time: Math.floor(Date.now() / 1000) - 3600 * 1, open: 1.5, high: 2, low: 1, close: 1.2, volume: 900 },
			],
			indicators: [
				{ type: 'MA', name: 'MA(9)', data: [
					{ time: Math.floor(Date.now() / 1000) - 3600 * 2, value: 1.2 },
					{ time: Math.floor(Date.now() / 1000) - 3600 * 1, value: 1.3 },
				], config: {} },
			],
			signals: [],
			lastUpdate: new Date(),
		};

		render(<TradingChartsWidget data={data} />);
		expect(screen.getByText(/Chart - BTCUSDT \(1h\)/i)).toBeInTheDocument();
	});
});
