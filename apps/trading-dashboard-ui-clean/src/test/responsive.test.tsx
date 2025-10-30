import { render, screen, fireEvent } from '@testing-library/react';
import { PerformanceWidget } from '@components/Trading/PerformanceWidget';
import { Sidebar } from '@components/Dashboard/Layout/Sidebar';
import { useUIStore } from '@stores/uiStore';

describe('Responsive behavior', () => {
	it('renders compact PerformanceWidget content when compact prop set', () => {
		render(<PerformanceWidget compact />);
		expect(screen.getByText(/Total/i)).toBeInTheDocument();
		expect(screen.getByText(/Daily/i)).toBeInTheDocument();
	});

	it('sidebar swipe toggles collapsed state (simulate by click)', () => {
		useUIStore.setState({ sidebarCollapsed: false });
		render(<Sidebar />);
		const toggle = screen.getByRole('button', { name: /toggle sidebar/i });
		fireEvent.click(toggle);
		expect(useUIStore.getState().sidebarCollapsed).toBe(true);
	});
});
