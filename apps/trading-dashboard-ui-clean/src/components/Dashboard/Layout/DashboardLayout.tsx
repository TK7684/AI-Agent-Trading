import React from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

interface DashboardLayoutProps {
	children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
	return (
		<div className="min-h-screen bg-gray-50 text-gray-900">
			<Topbar />
			<div className="flex">
				<Sidebar />
				<main className="flex-1 p-4">
					{children}
				</main>
			</div>
		</div>
	);
};

export default DashboardLayout;
