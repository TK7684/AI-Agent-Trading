import React, { useMemo } from 'react';
import { Card } from '@components/Common/Card';
import type { SystemHealth } from '@/types/system';
// import { UI_CONSTANTS } from '@/utils/constants';

interface SystemHealthWidgetProps {
	health: SystemHealth;
}

const Bar: React.FC<{ label: string; value: number; warning: number; critical: number; unit?: string }> = ({ label, value, warning, critical, unit = '%' }) => {
	const color = value >= critical ? 'bg-red-500' : value >= warning ? 'bg-yellow-500' : 'bg-green-500';
	return (
		<div>
			<div className="mb-1 flex items-center justify-between text-xs">
				<span>{label}</span>
				<span>{value}{unit}</span>
			</div>
			<div className="h-2 w-full rounded bg-gray-200">
				<div className={`h-2 rounded ${color}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
			</div>
		</div>
	);
};

const ConnectionDot: React.FC<{ label: string; up: boolean }> = ({ label, up }) => (
	<div className="flex items-center gap-2 text-sm">
		<span className={`inline-block h-2 w-2 rounded-full ${up ? 'bg-green-500' : 'bg-red-500'}`} />
		<span>{label}</span>
	</div>
);

function formatUptime(seconds: number): string {
	const d = Math.floor(seconds / 86400);
	const h = Math.floor((seconds % 86400) / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	return `${d}d ${h}h ${m}m`;
}

export const SystemHealthWidget: React.FC<SystemHealthWidgetProps> = ({ health }) => {
	const alerts = useMemo(() => {
		const a: string[] = [];
		if (health.cpu >= 95) a.push('CPU critical'); else if (health.cpu >= 80) a.push('CPU high');
		if (health.memory >= 95) a.push('Memory critical'); else if (health.memory >= 85) a.push('Memory high');
		if (health.diskUsage >= 98) a.push('Disk critical'); else if (health.diskUsage >= 90) a.push('Disk high');
		if (health.networkLatency >= 1000) a.push('Network latency critical'); else if (health.networkLatency >= 500) a.push('Network latency high');
		if (health.errorRate >= 10) a.push('Error rate critical'); else if (health.errorRate >= 5) a.push('Error rate high');
		return a;
	}, [health]);

	return (
		<Card header={<h3 className="text-sm font-semibold">System Health</h3>}>
			<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
				<div className="flex flex-col gap-3">
					<Bar label="CPU" value={health.cpu} warning={80} critical={95} />
					<Bar label="Memory" value={health.memory} warning={85} critical={95} />
					<Bar label="Disk" value={health.diskUsage} warning={90} critical={98} />
					<Bar label="Latency" value={Math.min(100, Math.round((health.networkLatency / 1000) * 100))} warning={50} critical={90} unit="%" />
					<Bar label="Error Rate" value={health.errorRate} warning={5} critical={10} />
				</div>
				<div className="flex flex-col gap-3">
					<div className="rounded border p-3">
						<div className="mb-2 text-xs font-semibold">Connections</div>
						<div className="grid grid-cols-2 gap-2">
							<ConnectionDot label="Database" up={health.connections.database} />
							<ConnectionDot label="Broker" up={health.connections.broker} />
							<ConnectionDot label="LLM" up={health.connections.llm} />
							<ConnectionDot label="WebSocket" up={health.connections.websocket} />
						</div>
					</div>
					<div className="rounded border p-3">
						<div className="text-xs">Uptime</div>
						<div className="text-sm font-medium">{formatUptime(health.uptime)}</div>
						<div className="mt-2 text-xs text-gray-500">Updated {health.lastUpdate.toLocaleTimeString()}</div>
					</div>
					{alerts.length > 0 && (
						<div className="rounded border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900">
							<div className="mb-1 font-semibold">Alerts</div>
							<ul className="list-disc pl-4">
								{alerts.map((a, i) => (<li key={i}>{a}</li>))}
							</ul>
						</div>
					)}
				</div>
			</div>
		</Card>
	);
};

export default SystemHealthWidget;
