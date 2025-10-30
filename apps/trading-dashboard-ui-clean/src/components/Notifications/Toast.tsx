import React, { useEffect } from 'react';
import clsx from 'clsx';
import type { ToastNotification } from '@/types/notifications';

interface ToastProps {
	toast: ToastNotification;
	onDismiss: (id: string) => void;
}

const typeClasses: Record<ToastNotification['type'], string> = {
	info: 'border-blue-200 bg-blue-50 text-blue-900',
	success: 'border-green-200 bg-green-50 text-green-900',
	warning: 'border-yellow-200 bg-yellow-50 text-yellow-900',
	error: 'border-red-200 bg-red-50 text-red-900',
	trade: 'border-purple-200 bg-purple-50 text-purple-900',
	system: 'border-gray-200 bg-gray-50 text-gray-900',
	agent: 'border-indigo-200 bg-indigo-50 text-indigo-900',
};

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss }) => {
	useEffect(() => {
		if (!toast.duration) return;
		const t = setTimeout(() => onDismiss(toast.id), toast.duration);
		return () => clearTimeout(t);
	}, [toast.id, toast.duration]);

	return (
		<div className={clsx('w-80 rounded-md border p-3 shadow-md', typeClasses[toast.type])} role="status">
			<div className="flex items-start justify-between gap-2">
				<div>
					<div className="text-sm font-semibold">{toast.title}</div>
					<div className="text-sm opacity-90">{toast.message}</div>
				</div>
				<button aria-label="Dismiss" className="text-sm opacity-70 hover:opacity-100" onClick={() => onDismiss(toast.id)}>✕</button>
			</div>
			{toast.actions?.length ? (
				<div className="mt-2 flex gap-2">
					{toast.actions.map((a) => (
						<button key={a.id} className="rounded border px-2 py-1 text-xs" onClick={a.action} disabled={a.disabled}>
							{a.label}
						</button>
					))}
				</div>
			) : null}
		</div>
	);
};

export default Toast;
