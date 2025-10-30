import React, { useState } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { NotificationCenter } from '@components/Notifications/NotificationCenter';
import { useNotificationStore } from '@/stores/notificationStore';

export const Topbar: React.FC = () => {
	const { theme, setTheme, refreshInterval, setRefreshInterval } = useUIStore();
	const { getUnreadCount } = useNotificationStore();
	const [open, setOpen] = useState(false);
	return (
		<header className="sticky top-0 z-40 w-full border-b bg-white">
			<div className="mx-auto flex h-14 items-center justify-between px-4">
				<div className="font-semibold">AI Agent Trading</div>
				<div className="flex items-center gap-3">
					<button aria-label="Notifications" className="relative rounded border px-2 py-1 text-sm" onClick={() => setOpen((v) => !v)}>
						🔔
						{getUnreadCount() > 0 && (
							<span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-red-600 px-1 text-xs text-white">
								{getUnreadCount()}
							</span>
						)}
					</button>
					<select
						value={theme}
						onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
						className="rounded border border-gray-300 px-2 py-1 text-sm"
					>
						<option value="light">Light</option>
						<option value="dark">Dark</option>
					</select>
					<select
						value={refreshInterval}
						onChange={(e) => setRefreshInterval(Number(e.target.value))}
						className="rounded border border-gray-300 px-2 py-1 text-sm"
					>
						<option value={1000}>1s</option>
						<option value={5000}>5s</option>
						<option value={10000}>10s</option>
						<option value={30000}>30s</option>
					</select>
				</div>
			</div>
			{open && (
				<div className="absolute right-2 top-14 z-50 w-[520px] max-w-[95vw]">
					<NotificationCenter />
				</div>
			)}
		</header>
	);
};

export default Topbar;
