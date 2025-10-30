import React, { useCallback, useMemo } from 'react';
import { Toast } from './Toast';
import { useNotificationStore } from '@/stores/notificationStore';
import type { ToastNotification } from '@/types/notifications';

export const ToastContainer: React.FC = () => {
	const { notifications, removeNotification } = useNotificationStore();

	// Create transient toasts from notifications that are not read
	const toasts: ToastNotification[] = useMemo(() => {
		return notifications
			.filter((n) => !n.read)
			.slice(0, 5)
			.map((n) => ({ id: n.id, type: n.type, title: n.title, message: n.message, duration: 5000 }));
	}, [notifications]);

	const handleDismiss = useCallback((id: string) => {
		removeNotification(id);
	}, [removeNotification]);

	if (toasts.length === 0) return null;
	return (
		<div className="pointer-events-none fixed inset-x-0 top-2 z-50 flex flex-col items-center gap-2">
			{toasts.map((t) => (
				<div key={t.id} className="pointer-events-auto">
					<Toast toast={t} onDismiss={handleDismiss} />
				</div>
			))}
		</div>
	);
};

export default ToastContainer;
