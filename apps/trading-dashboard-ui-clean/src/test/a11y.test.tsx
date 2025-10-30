import { render, screen } from '@testing-library/react';
import { Topbar } from '@components/Dashboard/Layout/Topbar';
import { Sidebar } from '@components/Dashboard/Layout/Sidebar';
import { NotificationCenter } from '@components/Notifications/NotificationCenter';
import { useNotificationStore } from '@stores/notificationStore';

describe('Accessibility basics', () => {
	it('Topbar has comboboxes and notification button', () => {
		render(<Topbar />);
		expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0);
		expect(screen.getByRole('button', { name: /Notifications/i })).toBeInTheDocument();
	});

	it('Sidebar nav links are accessible', () => {
		render(<Sidebar />);
		expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument();
	});

	it('NotificationCenter items are readable', () => {
		useNotificationStore.setState({ notifications: [] });
		render(<NotificationCenter />);
		expect(screen.getByText(/Notifications/i)).toBeInTheDocument();
	});
});
