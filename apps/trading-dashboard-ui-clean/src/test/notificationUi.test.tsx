import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationCenter } from '@components/Notifications/NotificationCenter';
import ToastContainer from '@components/Notifications/ToastContainer';
import { useNotificationStore } from '@stores/notificationStore';

const seedNotifications = () => {
	useNotificationStore.setState({ notifications: [] });
	useNotificationStore.getState().addNotification({ type: 'info', title: 'Hello', message: 'World' });
	useNotificationStore.getState().addNotification({ type: 'error', title: 'Error', message: 'Something failed' });
};

describe('Notification UI', () => {
	it('filters notifications by type and searches text', () => {
		seedNotifications();
		render(<NotificationCenter />);
		fireEvent.change(screen.getByDisplayValue('all'), { target: { value: 'error' } });
		expect(screen.getByText(/Error/i)).toBeInTheDocument();
		const search = screen.getByPlaceholderText(/Search notifications/i);
		fireEvent.change(search, { target: { value: 'hello' } });
		expect(screen.queryByText(/Error/i)).not.toBeInTheDocument();
	});

	it('renders toast for unread and dismisses it', () => {
		seedNotifications();
		render(<ToastContainer />);
		expect(screen.getByText(/Hello/i)).toBeInTheDocument();
		const close = screen.getByRole('button', { name: /dismiss/i });
		fireEvent.click(close);
		expect(screen.queryByText(/Hello/i)).not.toBeInTheDocument();
	});
});
