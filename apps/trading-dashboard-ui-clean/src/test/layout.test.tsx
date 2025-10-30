import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Sidebar } from '@components/Dashboard/Layout/Sidebar';
import { Topbar } from '@components/Dashboard/Layout/Topbar';
import { useUIStore } from '@stores/uiStore';

const Providers: React.FC<{ children: React.ReactNode }> = ({ children }) => (
	<BrowserRouter>{children}</BrowserRouter>
);

describe('Layout components', () => {
	beforeEach(() => {
		useUIStore.setState({ sidebarCollapsed: false, theme: 'light', refreshInterval: 5000 });
	});

	it('renders Sidebar and toggles collapse', () => {
		render(<Sidebar />, { wrapper: Providers });
		expect(screen.getByText(/Trading Dashboard/i)).toBeInTheDocument();
		const toggle = screen.getByRole('button', { name: /toggle sidebar/i });
		fireEvent.click(toggle);
		expect(useUIStore.getState().sidebarCollapsed).toBe(true);
	});

	it('renders Topbar and changes theme and refresh interval', () => {
		render(<Topbar />, { wrapper: Providers });
		expect(screen.getByText(/AI Agent Trading/i)).toBeInTheDocument();
		const selects = screen.getAllByRole('combobox');
		fireEvent.change(selects[0], { target: { value: 'dark' } });
		expect(useUIStore.getState().theme).toBe('dark');
		fireEvent.change(selects[1], { target: { value: '10000' } });
		expect(useUIStore.getState().refreshInterval).toBe(10000);
	});
});
