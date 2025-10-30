import { render, screen, fireEvent } from '@testing-library/react';
import AgentControlWidget from '@components/Controls/AgentControlWidget';
import type { AgentStatus, RiskLimits, TradingHours } from '@types/system';

const status: AgentStatus = { state: 'stopped', uptime: 0, lastAction: new Date(), activePositions: 0, dailyTrades: 0, version: '1.0.0' };

describe('AgentControlWidget', () => {
	it('renders controls and triggers callbacks', () => {
		const onStart = vi.fn();
		const onPause = vi.fn();
		const onStop = vi.fn();
		const onUpdateRiskLimits = vi.fn();
		const onUpdateTradingHours = vi.fn();

		render(
			<AgentControlWidget
				status={status}
				onStart={onStart}
				onPause={onPause}
				onStop={onStop}
				onUpdateRiskLimits={onUpdateRiskLimits}
				onUpdateTradingHours={onUpdateTradingHours}
			/>
		);

		fireEvent.click(screen.getByText(/Start/i));
		expect(onStart).toHaveBeenCalled();

		fireEvent.click(screen.getByText(/Save Risk Limits/i));
		expect(onUpdateRiskLimits).toHaveBeenCalled();

		fireEvent.click(screen.getByText(/Save Trading Hours/i));
		expect(onUpdateTradingHours).toHaveBeenCalled();

		fireEvent.click(screen.getByText(/Emergency Stop/i));
		fireEvent.click(screen.getByText(/^Emergency Stop$/));
		expect(onStop).toHaveBeenCalled();
	});
});
