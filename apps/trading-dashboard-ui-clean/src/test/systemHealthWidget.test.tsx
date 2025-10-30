import { render, screen } from '@testing-library/react';
import SystemHealthWidget from '@components/System/SystemHealthWidget';
import type { SystemHealth } from '@types/system';

describe('SystemHealthWidget', () => {
	it('shows alerts when thresholds exceeded and connections status', () => {
		const health: SystemHealth = {
			cpu: 96,
			memory: 90,
			diskUsage: 99,
			networkLatency: 1200,
			errorRate: 12,
			uptime: 1000,
			connections: { database: false, broker: true, llm: false, websocket: true },
			lastUpdate: new Date(),
		};
		render(<SystemHealthWidget health={health} />);
		expect(screen.getByText(/Alerts/i)).toBeInTheDocument();
		expect(screen.getByText(/CPU critical/i)).toBeInTheDocument();
		expect(screen.getByText(/Disk critical/i)).toBeInTheDocument();
		expect(screen.getByText(/Network latency critical/i)).toBeInTheDocument();
		expect(screen.getByText(/Error rate critical/i)).toBeInTheDocument();
		expect(screen.getByText(/Database/i)).toBeInTheDocument();
		// Connection dots render; detailed color checks are not performed here
	});
});
