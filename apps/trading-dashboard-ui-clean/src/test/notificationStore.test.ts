import { describe, it, expect, beforeEach } from 'vitest';
import { useNotificationStore } from '../stores/notificationStore';
import type { Notification } from '../types';

describe('NotificationStore', () => {
	beforeEach(() => {
		useNotificationStore.setState({
			notifications: [],
			soundEnabled: true,
			maxNotifications: 100,
		});
	});

	it('adds notifications and enforces max size', () => {
		for (let i = 0; i < 105; i++) {
			useNotificationStore.getState().addNotification({
				type: 'info',
				title: `n${i}`,
				message: 'msg',
			});
		}
		expect(useNotificationStore.getState().notifications.length).toBeLessThanOrEqual(100);
	});

	it('marks notifications read and clears', () => {
		useNotificationStore.getState().addNotification({ type: 'warning', title: 'a', message: 'b' });
		const id = useNotificationStore.getState().notifications[0].id;
		useNotificationStore.getState().markAsRead(id);
		expect(useNotificationStore.getState().getUnreadCount()).toBe(0);
		useNotificationStore.getState().clearAll();
		expect(useNotificationStore.getState().notifications.length).toBe(0);
	});

	it('filters by type and toggles settings', () => {
		useNotificationStore.getState().addNotification({ type: 'error', title: 'e', message: 'm' });
		useNotificationStore.getState().addNotification({ type: 'info', title: 'i', message: 'm' });
		const errors = useNotificationStore.getState().getNotificationsByType('error');
		expect(errors.every((n) => n.type === 'error')).toBe(true);

		useNotificationStore.getState().setSoundEnabled(false);
		useNotificationStore.getState().setMaxNotifications(5);
		expect(useNotificationStore.getState().soundEnabled).toBe(false);
		expect(useNotificationStore.getState().maxNotifications).toBe(5);
	});
});

