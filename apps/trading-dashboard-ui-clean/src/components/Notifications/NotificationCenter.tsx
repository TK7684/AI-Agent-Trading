import React, { useMemo, useState } from 'react';
import { useNotificationStore } from '@/stores/notificationStore';
import type { Notification } from '@/types/notifications';
import { Card } from '@components/Common/Card';

export const NotificationCenter: React.FC = () => {
	const { notifications, removeNotification, markAsRead, markAllAsRead, clearAll, getUnreadCount } = useNotificationStore();
	const [searchText, setSearchText] = useState('');
	const [typeFilter, setTypeFilter] = useState<Notification['type'] | 'all'>('all');

	const filtered = useMemo(() => {
		return notifications.filter((n) => {
			const matchesText = !searchText || n.title.toLowerCase().includes(searchText.toLowerCase()) || n.message.toLowerCase().includes(searchText.toLowerCase());
			const matchesType = typeFilter === 'all' || n.type === typeFilter;
			return matchesText && matchesType;
		});
	}, [notifications, searchText, typeFilter]);

	return (
		<Card
			header={
				<div className="flex items-center justify-between">
					<h3 className="text-sm font-semibold">Notifications</h3>
					<div className="text-xs text-gray-500">Unread: {getUnreadCount()}</div>
				</div>
			}
		>
			<div className="mb-3 flex items-center gap-2">
				<input
					placeholder="Search notifications..."
					value={searchText}
					onChange={(e) => setSearchText(e.target.value)}
					className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
				/>
				<select
					value={typeFilter}
					onChange={(e) => setTypeFilter(e.target.value as any)}
					className="rounded border border-gray-300 px-2 py-2 text-sm"
				>
					<option value="all">All</option>
					<option value="info">Info</option>
					<option value="success">Success</option>
					<option value="warning">Warning</option>
					<option value="error">Error</option>
					<option value="trade">Trade</option>
					<option value="system">System</option>
					<option value="agent">Agent</option>
				</select>
				<button className="rounded border px-2 py-2 text-sm" onClick={markAllAsRead}>Mark all read</button>
				<button className="rounded border px-2 py-2 text-sm" onClick={clearAll}>Clear</button>
			</div>
			<div className="max-h-80 overflow-auto divide-y">
				{filtered.length === 0 ? (
					<div className="py-6 text-center text-sm text-gray-500">No notifications</div>
				) : (
					filtered.map((n) => (
						<div key={n.id} className="flex items-start justify-between gap-2 py-3">
							<div>
								<div className="text-sm font-medium">
									{n.title} {n.read ? null : <span className="ml-2 inline-block h-2 w-2 rounded-full bg-blue-500 align-middle" />}
								</div>
								<div className="text-xs text-gray-600">{n.message}</div>
								<div className="mt-1 text-xs text-gray-400">{n.timestamp.toLocaleString()}</div>
							</div>
							<div className="flex items-center gap-2">
								{!n.read && (
									<button className="rounded border px-2 py-1 text-xs" onClick={() => markAsRead(n.id)}>Mark read</button>
								)}
								<button className="rounded border px-2 py-1 text-xs" onClick={() => removeNotification(n.id)}>Dismiss</button>
							</div>
						</div>
					))
				)}
			</div>
		</Card>
	);
};

export default NotificationCenter;
