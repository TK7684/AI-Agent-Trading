import React from 'react';
import { useUIStore } from '@/stores/uiStore';

export const WidgetLibrary: React.FC = () => {
	const { widgets, addWidget, removeWidget, updateWidget } = useUIStore();

	const add = (type: 'performance' | 'chart' | 'logs' | 'controls' | 'system') => {
		const id = `${type}-${Math.random().toString(36).slice(2)}`;
		addWidget({ id, type, position: { x: 0, y: Infinity, w: 4, h: 4 }, visible: true, config: {} });
	};

	return (
		<div className="rounded border p-3">
			<div className="mb-2 text-sm font-semibold">Widget Library</div>
			<div className="mb-3 flex flex-wrap gap-2">
				<button className="rounded border px-2 py-1 text-xs" onClick={() => add('performance')}>Add Performance</button>
				<button className="rounded border px-2 py-1 text-xs" onClick={() => add('chart')}>Add Chart</button>
				<button className="rounded border px-2 py-1 text-xs" onClick={() => add('logs')}>Add Logs</button>
				<button className="rounded border px-2 py-1 text-xs" onClick={() => add('controls')}>Add Controls</button>
				<button className="rounded border px-2 py-1 text-xs" onClick={() => add('system')}>Add System</button>
			</div>
			<div className="max-h-48 overflow-auto text-sm">
				{widgets.map((w) => (
					<div key={w.id} className="flex items-center justify-between border-b py-2 last:border-0">
						<div className="flex items-center gap-2">
							<span className="text-xs uppercase">{w.type}</span>
							<span className="text-gray-500">{w.id}</span>
						</div>
						<div className="flex items-center gap-2">
							<label className="text-xs">
								<input type="checkbox" className="mr-1" checked={w.visible} onChange={(e) => updateWidget(w.id, { visible: e.target.checked })} />
								Visible
							</label>
							<button className="rounded border px-2 py-1 text-xs" onClick={() => removeWidget(w.id)}>Remove</button>
						</div>
					</div>
				))}
			</div>
		</div>
	);
};

export default WidgetLibrary;
