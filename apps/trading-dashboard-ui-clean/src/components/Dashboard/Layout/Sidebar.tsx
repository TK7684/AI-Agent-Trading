import React, { useRef } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { NavLink } from 'react-router-dom';

export const Sidebar: React.FC = () => {
	const { sidebarCollapsed, setSidebarCollapsed } = useUIStore();
	const touchStartX = useRef<number | null>(null);

	return (
		<aside
			className={`transition-all border-r border-gray-200 bg-white ${sidebarCollapsed ? 'w-16' : 'w-64'}`}
			onTouchStart={(e) => { touchStartX.current = e.touches[0].clientX; }}
			onTouchEnd={(e) => {
				if (touchStartX.current == null) return;
				const dx = e.changedTouches[0].clientX - touchStartX.current;
				if (!sidebarCollapsed && dx < -50) setSidebarCollapsed(true);
				if (sidebarCollapsed && dx > 50) setSidebarCollapsed(false);
				touchStartX.current = null;
			}}
		>
			<div className="p-3 flex items-center justify-between border-b">
				<span className="font-semibold">{sidebarCollapsed ? 'TD' : 'Trading Dashboard'}</span>
				<button
					aria-label="Toggle Sidebar"
					className="text-sm text-gray-600 hover:text-gray-900"
					onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
				>
					{sidebarCollapsed ? '›' : '‹'}
				</button>
			</div>
			<nav className="p-2 flex flex-col gap-1">
				<NavLink to="/dashboard" className={({ isActive }) => `rounded px-3 py-2 ${isActive ? 'bg-gray-100 font-medium' : 'hover:bg-gray-50'}`}>
					Dashboard
				</NavLink>
				<NavLink to="/" className={({ isActive }) => `rounded px-3 py-2 ${isActive ? 'bg-gray-100 font-medium' : 'hover:bg-gray-50'}`}>
					Home
				</NavLink>
			</nav>
		</aside>
	);
};

export default Sidebar;
