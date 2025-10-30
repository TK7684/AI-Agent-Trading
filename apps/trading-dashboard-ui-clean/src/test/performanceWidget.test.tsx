import { render, screen } from '@testing-library/react';
import { PerformanceWidget } from '@components/Trading/PerformanceWidget';
import { useTradingStore } from '@stores/tradingStore';

const setMetrics = () => {
	useTradingStore.setState({
		performanceMetrics: {
			totalPnl: 1234.56,
			dailyPnl: 12.34,
			winRate: 66.7,
			totalTrades: 42,
			currentDrawdown: 5.2,
			maxDrawdown: 12.3,
			portfolioValue: 25000,
			dailyChange: 12.34,
			dailyChangePercent: 0.05,
			lastUpdate: new Date(),
		},
	});
};

describe('PerformanceWidget', () => {
	it('renders key metrics', () => {
		setMetrics();
		render(<PerformanceWidget />);
		expect(screen.getByText(/Performance/i)).toBeInTheDocument();
		expect(screen.getByText(/Total PnL/i)).toBeInTheDocument();
		expect(screen.getByText(/Daily PnL/i)).toBeInTheDocument();
		expect(screen.getByText(/Win Rate/i)).toBeInTheDocument();
		expect(screen.getByText(/Portfolio Value/i)).toBeInTheDocument();
		expect(screen.getByText(/Drawdown/i)).toBeInTheDocument();
	});
});
