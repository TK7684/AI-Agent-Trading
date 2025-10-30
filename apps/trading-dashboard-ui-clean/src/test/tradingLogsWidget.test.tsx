import { render, screen, fireEvent } from '@testing-library/react';
import { TradingLogsWidget } from '@components/Trading/TradingLogsWidget';
import type { TradeLogEntry } from '@types/trading';

const trades: TradeLogEntry[] = [
	{ id: '1', timestamp: new Date(), symbol: 'BTCUSDT', side: 'LONG', entryPrice: 100, exitPrice: 110, quantity: 1, pnl: 10, status: 'CLOSED', confidence: 70 },
	{ id: '2', timestamp: new Date(), symbol: 'ETHUSDT', side: 'SHORT', entryPrice: 200, exitPrice: 190, quantity: 1, pnl: 10, status: 'CLOSED', confidence: 60 },
	{ id: '3', timestamp: new Date(), symbol: 'BTCUSDT', side: 'LONG', entryPrice: 120, quantity: 1, status: 'OPEN', confidence: 50 },
	{ id: '4', timestamp: new Date(), symbol: 'SOLUSDT', side: 'LONG', entryPrice: 30, exitPrice: 28, quantity: 10, pnl: -20, status: 'CLOSED', confidence: 55 },
];

describe('TradingLogsWidget', () => {
	it('filters by symbol, status and search', () => {
		render(<TradingLogsWidget trades={trades} />);
		const symbolSelect = screen.getByDisplayValue('All Symbols');
		fireEvent.change(symbolSelect, { target: { value: 'BTCUSDT' } });
		expect(screen.getAllByText(/BTCUSDT/).length).toBeGreaterThan(0);

		const statusSelect = screen.getByDisplayValue('All Status');
		fireEvent.change(statusSelect, { target: { value: 'CLOSED' } });
		expect(screen.queryByText(/OPEN/)).not.toBeInTheDocument();

		const search = screen.getByPlaceholderText(/Search symbol\/pattern/i);
		fireEvent.change(search, { target: { value: 'SOL' } });
		expect(screen.getByText(/SOLUSDT/)).toBeInTheDocument();
	});

	it('paginates results', () => {
		const many = Array.from({ length: 25 }).map((_, i) => ({ ...trades[0], id: `id-${i}`, timestamp: new Date() }));
		render(<TradingLogsWidget trades={many as any} />);
		expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
		fireEvent.click(screen.getByText(/Next/));
		expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument();
	});
});
