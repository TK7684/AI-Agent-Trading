import React, { useState } from 'react';
import { Card } from '@components/Common/Card';
import Button from '@components/Common/Button';
import Modal from '@components/Common/Modal';
import Input from '@components/Common/Input';
import type { AgentStatus, RiskLimits, TradingHours } from '@/types/system';
import { useTradingStore } from '@/stores/tradingStore';

interface AgentControlWidgetProps {
	status: AgentStatus | null;
	onStart: () => void;
	onPause: () => void;
	onStop: () => void;
	onUpdateRiskLimits: (limits: RiskLimits) => void;
	onUpdateTradingHours: (hours: TradingHours) => void;
}

const StatusBadge: React.FC<{ status: AgentStatus | null }> = ({ status }) => {
	const color = status?.state === 'running' ? 'bg-green-500' : status?.state === 'paused' ? 'bg-yellow-500' : status?.state === 'stopped' ? 'bg-gray-400' : status?.state === 'error' ? 'bg-red-500' : 'bg-gray-300';
	return (
		<div className="inline-flex items-center gap-2 text-sm">
			<span className={`inline-block h-2 w-2 rounded-full ${color}`} />
			<span className="capitalize">{status?.state ?? 'unknown'}</span>
		</div>
	);
};

export const AgentControlWidget: React.FC<AgentControlWidgetProps> = ({ status, onStart, onPause, onStop, onUpdateRiskLimits, onUpdateTradingHours }) => {
	const { agentStatus } = useTradingStore();
	const effectiveStatus = status || agentStatus;

	const [limits, setLimits] = useState<RiskLimits>({ maxDailyLoss: 1000, maxDrawdown: 20, maxPositions: 5, maxPositionSize: 10000, stopLossPercent: 2, takeProfitPercent: 6 });
	const [hours, setHours] = useState<TradingHours>({ enabled: true, start: '09:30', end: '16:00', timezone: 'UTC', weekendsEnabled: false });
	const [confirmOpen, setConfirmOpen] = useState(false);

	return (
		<Card header={<div className="flex items-center justify-between"><h3 className="text-sm font-semibold">Agent Controls</h3><StatusBadge status={effectiveStatus || null} /></div>}>
			<div className="mb-4 flex flex-wrap items-center gap-2">
				<Button variant="primary" onClick={onStart} disabled={effectiveStatus?.state === 'running'}>Start</Button>
				<Button variant="secondary" onClick={onPause} disabled={effectiveStatus?.state !== 'running'}>Pause</Button>
				<Button variant="ghost" onClick={onStop} disabled={effectiveStatus?.state === 'stopped'}>Stop</Button>
				<Button variant="danger" onClick={() => setConfirmOpen(true)}>Emergency Stop</Button>
			</div>

			<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
				<div>
					<h4 className="mb-2 text-sm font-semibold">Risk Limits</h4>
					<div className="grid grid-cols-2 gap-3">
						<Input label="Max daily loss ($)" type="number" value={limits.maxDailyLoss} onChange={(e) => setLimits({ ...limits, maxDailyLoss: Number(e.target.value) })} />
						<Input label="Max drawdown (%)" type="number" value={limits.maxDrawdown} onChange={(e) => setLimits({ ...limits, maxDrawdown: Number(e.target.value) })} />
						<Input label="Max positions" type="number" value={limits.maxPositions} onChange={(e) => setLimits({ ...limits, maxPositions: Number(e.target.value) })} />
						<Input label="Max position size ($)" type="number" value={limits.maxPositionSize} onChange={(e) => setLimits({ ...limits, maxPositionSize: Number(e.target.value) })} />
						<Input label="Stop loss (%)" type="number" value={limits.stopLossPercent} onChange={(e) => setLimits({ ...limits, stopLossPercent: Number(e.target.value) })} />
						<Input label="Take profit (%)" type="number" value={limits.takeProfitPercent} onChange={(e) => setLimits({ ...limits, takeProfitPercent: Number(e.target.value) })} />
					</div>
					<div className="mt-2">
						<Button variant="primary" onClick={() => onUpdateRiskLimits(limits)}>Save Risk Limits</Button>
					</div>
				</div>
				<div>
					<h4 className="mb-2 text-sm font-semibold">Trading Hours</h4>
					<div className="grid grid-cols-2 gap-3">
						<label className="flex items-center gap-2 text-sm">
							<input type="checkbox" checked={hours.enabled} onChange={(e) => setHours({ ...hours, enabled: e.target.checked })} /> Enable
						</label>
						<Input label="Timezone" value={hours.timezone} onChange={(e) => setHours({ ...hours, timezone: e.target.value })} />
						<Input label="Start (HH:MM)" value={hours.start} onChange={(e) => setHours({ ...hours, start: e.target.value })} />
						<Input label="End (HH:MM)" value={hours.end} onChange={(e) => setHours({ ...hours, end: e.target.value })} />
						<label className="flex items-center gap-2 text-sm">
							<input type="checkbox" checked={hours.weekendsEnabled} onChange={(e) => setHours({ ...hours, weekendsEnabled: e.target.checked })} /> Weekends
						</label>
					</div>
					<div className="mt-2">
						<Button variant="primary" onClick={() => onUpdateTradingHours(hours)}>Save Trading Hours</Button>
					</div>
				</div>
			</div>

			<Modal open={confirmOpen} title="Confirm Emergency Stop" onClose={() => setConfirmOpen(false)}>
				<p className="mb-4 text-sm">This will immediately stop the agent and cancel all open actions. Are you sure?</p>
				<div className="flex justify-end gap-2">
					<Button variant="ghost" onClick={() => setConfirmOpen(false)}>Cancel</Button>
					<Button variant="danger" onClick={() => { setConfirmOpen(false); onStop(); }}>Emergency Stop</Button>
				</div>
			</Modal>
		</Card>
	);
};

export default AgentControlWidget;
