import React, { useMemo, useCallback } from 'react';
import { Layout, Responsive, WidthProvider, ResponsiveProps } from 'react-grid-layout';
import { useUIStore } from '@/stores/uiStore';
import { UI_CONSTANTS } from '@/utils/constants';
import { PerformanceWidget } from '@components/Trading/PerformanceWidget';
import { TradingChartsWidget } from '@components/Charts/TradingChartsWidget';
import { TradingLogsWidget } from '@components/Trading/TradingLogsWidget';
import AgentControlWidget from '@components/Controls/AgentControlWidget';
import SystemHealthWidget from '@components/System/SystemHealthWidget';
import type { ChartData, TradeLogEntry } from '@/types/trading';
import type { AgentStatus, RiskLimits, TradingHours, SystemHealth } from '@/types/system';

const ResponsiveGridLayout = WidthProvider(Responsive as unknown as React.ComponentType<ResponsiveProps>);

interface DashboardGridProps {
	chartData: ChartData;
	trades: TradeLogEntry[];
	agentStatus: AgentStatus;
	health: SystemHealth;
}

export const DashboardGrid: React.FC<DashboardGridProps> = ({ trades, agentStatus, health }) => {
	const { widgets, setWidgets, getVisibleWidgets } = useUIStore();
	const visible = getVisibleWidgets();

	const layout: Layout[] = useMemo(() => visible.map((w) => ({ i: w.id, x: w.position.x, y: w.position.y, w: w.position.w, h: w.position.h })), [visible]);

	const onLayoutChange = useCallback((currentLayout: Layout[]) => {
		const nextWidgets = widgets.map((w) => {
			const l = currentLayout.find((n) => n.i === w.id);
			return l ? { ...w, position: { x: l.x, y: l.y, w: l.w, h: l.h } } : w;
		});
		setWidgets(nextWidgets);
	}, [widgets, setWidgets]);

	return (
		<div>
			<ResponsiveGridLayout
				className="layout"
				layouts={{ lg: layout, md: layout, sm: layout, xs: layout, xxs: layout }}
				breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
				cols={UI_CONSTANTS.GRID_LAYOUT.cols as any}
				rowHeight={UI_CONSTANTS.GRID_LAYOUT.rowHeight}
				margin={UI_CONSTANTS.GRID_LAYOUT.margin as [number, number]}
				containerPadding={UI_CONSTANTS.GRID_LAYOUT.containerPadding as [number, number]}
				onLayoutChange={(_, allLayouts) => {
					// Use lg layout if available, else pick any
					const anyLayout = allLayouts.lg || allLayouts.md || allLayouts.sm || allLayouts.xs || allLayouts.xxs || [];
					onLayoutChange(anyLayout as unknown as Layout[]);
				}}
			>
				{visible.map((w) => (
					<div key={w.id} data-grid={{ i: w.id }}>
						{w.type === 'performance' && <PerformanceWidget />}
						{w.type === 'chart' && <TradingChartsWidget symbol="BTCUSDT" timeframe="1h" />}
						{w.type === 'logs' && <TradingLogsWidget trades={trades} />}
						{w.type === 'controls' && (
							<AgentControlWidget
								status={agentStatus}
								onStart={() => console.log('Start agent')}
								onPause={() => console.log('Pause agent')}
								onStop={() => console.log('Stop agent')}
								onUpdateRiskLimits={(limits: RiskLimits) => console.log('Update limits', limits)}
								onUpdateTradingHours={(hours: TradingHours) => console.log('Update hours', hours)}
							/>
						)}
						{w.type === 'system' && <SystemHealthWidget health={health} />}
					</div>
				))}
			</ResponsiveGridLayout>
		</div>
	);
};

export default DashboardGrid;
