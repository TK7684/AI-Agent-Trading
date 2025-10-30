import React, { useEffect, useMemo, useState } from 'react';
import { useTradingStore } from '@/stores/tradingStore';
import { Card } from '@components/Common/Card';
import { formatCurrency, formatPercentage } from '@/utils/formatters';

const AnimatedNumber: React.FC<{ 
	value: number; 
	formatter: (n: number) => string; 
	positiveColor?: string; 
	negativeColor?: string; 
}> = React.memo(({ value, formatter, positiveColor = 'text-green-600', negativeColor = 'text-red-600' }) => {
	const [display, setDisplay] = useState(value);
	const [changed, setChanged] = useState<'up' | 'down' | null>(null);

	useEffect(() => {
		// Only update if value actually changed to prevent unnecessary animations
		if (value !== display) {
			setChanged(value > display ? 'up' : value < display ? 'down' : null);
			setDisplay(value);
			const t = setTimeout(() => setChanged(null), 500);
			return () => clearTimeout(t);
		}
	}, [value, display]);

	return (
		<span className={changed === 'up' ? positiveColor : changed === 'down' ? negativeColor : undefined}>
			{formatter(display)}
		</span>
	);
}, (prevProps, nextProps) => {
	// Only re-render if value actually changed
	return prevProps.value === nextProps.value && prevProps.formatter === nextProps.formatter;
});

const PerformanceWidgetInner: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
	const { performanceMetrics, getTotalPnL } = useTradingStore();

	// Memoized calculations with dependency optimization
	const totals = useMemo(() => {
		const totalPnL = performanceMetrics?.totalPnl ?? getTotalPnL();
		return {
			totalPnL,
			dailyPnl: performanceMetrics?.dailyPnl ?? 0,
			winRate: performanceMetrics?.winRate ?? 0,
			portfolioValue: performanceMetrics?.portfolioValue ?? 0,
			dailyChange: performanceMetrics?.dailyChange ?? 0,
			dailyChangePercent: performanceMetrics?.dailyChangePercent ?? 0,
			maxDrawdown: performanceMetrics?.maxDrawdown ?? 0,
			currentDrawdown: performanceMetrics?.currentDrawdown ?? 0,
			lastUpdate: performanceMetrics?.lastUpdate ?? new Date(),
		};
	}, [
		performanceMetrics?.totalPnl,
		performanceMetrics?.dailyPnl,
		performanceMetrics?.winRate,
		performanceMetrics?.portfolioValue,
		performanceMetrics?.dailyChange,
		performanceMetrics?.dailyChangePercent,
		performanceMetrics?.maxDrawdown,
		performanceMetrics?.currentDrawdown,
		performanceMetrics?.lastUpdate,
		getTotalPnL
	]);

	// Memoized formatters to prevent recreation on every render
	const formatters = useMemo(() => ({
		currency: (n: number) => formatCurrency(n),
		percentage: (n: number) => formatPercentage(n),
	}), []);

	return (
		<Card
			header={<div className="flex items-center justify-between">
				<h3 className="text-sm font-semibold">Performance</h3>
				<span className="text-xs text-gray-500 sm:inline hidden">Updated {totals.lastUpdate.toLocaleTimeString()}</span>
			</div>}
		>
			{compact ? (
				<div className="grid grid-cols-2 gap-3">
					<div>
						<div className="text-xs text-gray-500">Total</div>
						<AnimatedNumber value={totals.totalPnL} formatter={formatters.currency} />
					</div>
					<div>
						<div className="text-xs text-gray-500">Daily</div>
						<AnimatedNumber value={totals.dailyPnl} formatter={formatters.currency} />
					</div>
				</div>
			) : (
				<div className="grid grid-cols-2 gap-4 md:grid-cols-3">
					<div>
						<div className="text-xs text-gray-500">Total PnL</div>
						<AnimatedNumber value={totals.totalPnL} formatter={formatters.currency} />
					</div>
					<div>
						<div className="text-xs text-gray-500">Daily PnL</div>
						<AnimatedNumber value={totals.dailyPnl} formatter={formatters.currency} />
					</div>
					<div>
						<div className="text-xs text-gray-500">Win Rate</div>
						<AnimatedNumber value={totals.winRate} formatter={formatters.percentage} />
					</div>
					<div>
						<div className="text-xs text-gray-500">Portfolio Value</div>
						<AnimatedNumber value={totals.portfolioValue} formatter={formatters.currency} />
					</div>
					<div>
						<div className="text-xs text-gray-500">Daily Change</div>
						<div className="flex items-baseline gap-2">
							<AnimatedNumber value={totals.dailyChange} formatter={formatters.currency} />
							<span className={totals.dailyChange >= 0 ? 'text-green-600' : 'text-red-600'}>
								{formatters.percentage(totals.dailyChangePercent)}
							</span>
						</div>
					</div>
					<div>
						<div className="text-xs text-gray-500">Drawdown</div>
						<div className="flex items-baseline gap-2">
							<span className="text-sm">Max {formatters.percentage(totals.maxDrawdown)}</span>
							<span className="text-xs text-gray-500">Current {formatters.percentage(totals.currentDrawdown)}</span>
						</div>
					</div>
				</div>
			)}
		</Card>
	);
};

export const PerformanceWidget = React.memo(PerformanceWidgetInner, (prevProps, nextProps) => {
	// Only re-render if compact prop changes
	return prevProps.compact === nextProps.compact;
});

PerformanceWidget.displayName = 'PerformanceWidget';

export default PerformanceWidget;
