import React, { useMemo, useState, useCallback, useRef } from 'react';
import { Card } from '@components/Common/Card';
import { VirtualScrollTable } from '@components/Common/VirtualScrollTable';
import type { TradeLogEntry, TradeStatus } from '@/types/trading';
import { formatCurrency, formatDateTime } from '@/utils/formatters';
import { debounce } from '@/utils/performance';

interface TradingLogsWidgetProps {
	trades: TradeLogEntry[];
	onSearch?: (query: string) => void;
	onFilter?: (filters: any) => void;
	isLoading?: boolean;
}

const pageSizes = [10, 20, 50, 100];
const ROW_HEIGHT = 48;
const TABLE_HEIGHT = 400;

function exportCSV(rows: TradeLogEntry[]): string {
	const header = ['id', 'timestamp', 'symbol', 'side', 'entryPrice', 'exitPrice', 'quantity', 'pnl', 'status', 'pattern', 'confidence', 'duration', 'fees'];
	const lines = [header.join(',')].concat(
		rows.map((t) => [
			t.id,
			new Date(t.timestamp).toISOString(),
			t.symbol,
			t.side,
			t.entryPrice,
			t.exitPrice ?? '',
			t.quantity,
			t.pnl ?? '',
			t.status,
			t.pattern ?? '',
			t.confidence,
			t.duration ?? '',
			t.fees ?? '',
		].join(','))
	);
	return lines.join('\n');
}

function exportJSON(rows: TradeLogEntry[]): string {
	return JSON.stringify(rows, null, 2);
}

const TradingLogsWidgetComponent: React.FC<TradingLogsWidgetProps> = ({ 
	trades, 
	onSearch, 
	onFilter, 
	isLoading = false 
}) => {
	const [status, setStatus] = useState<TradeStatus | 'all'>('all');
	const [symbol, setSymbol] = useState<string>('all');
	const [search, setSearch] = useState<string>('');
	const [pnlFilter, setPnlFilter] = useState<'all' | 'profit' | 'loss'>('all');
	const [useVirtualScrolling, setUseVirtualScrolling] = useState(true);

	// Debounced search and filter functions
	const debouncedSearch = useRef(
		debounce((query: string) => {
			if (onSearch) onSearch(query);
		}, 300, { trailing: true })
	).current;

	const debouncedFilter = useRef(
		debounce((filters: any) => {
			if (onFilter) onFilter(filters);
		}, 150, { trailing: true })
	).current;

	const symbols = useMemo(() => Array.from(new Set(trades.map((t) => t.symbol))), [trades]);

	// Optimized filtering with memoization
	const filtered = useMemo(() => {
		return trades.filter((t) => {
			if (status !== 'all' && t.status !== status) return false;
			if (symbol !== 'all' && t.symbol !== symbol) return false;
			if (pnlFilter !== 'all') {
				const pnl = t.pnl ?? 0;
				if (pnlFilter === 'profit' && pnl <= 0) return false;
				if (pnlFilter === 'loss' && pnl >= 0) return false;
			}
			if (search) {
				const q = search.toLowerCase();
				if (!(`${t.symbol} ${t.pattern ?? ''}`.toLowerCase().includes(q))) return false;
			}
			return true;
		});
	}, [trades, status, symbol, pnlFilter, search]);

	// Handle search input changes
	const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
		const value = e.target.value;
		setSearch(value);
		debouncedSearch(value);
	}, [debouncedSearch]);

	// Handle filter changes
	const handleFilterChange = useCallback((filterType: string, value: any) => {
		const newFilters = { status, symbol, pnlFilter, [filterType]: value };
		
		switch (filterType) {
			case 'status':
				setStatus(value);
				break;
			case 'symbol':
				setSymbol(value);
				break;
			case 'pnlFilter':
				setPnlFilter(value);
				break;
		}

		debouncedFilter(newFilters);
	}, [status, symbol, pnlFilter, debouncedFilter]);

	// Define columns for virtual table
	const columns = useMemo(() => [
		{
			key: 'timestamp' as keyof TradeLogEntry,
			header: 'Time',
			width: '140px',
			render: (value: Date) => (
				<span className="text-xs whitespace-nowrap">
					{formatDateTime(value)}
				</span>
			),
		},
		{
			key: 'symbol' as keyof TradeLogEntry,
			header: 'Symbol',
			width: '80px',
			render: (value: string) => (
				<span className="font-medium">{value}</span>
			),
		},
		{
			key: 'side' as keyof TradeLogEntry,
			header: 'Side',
			width: '60px',
			render: (value: string) => (
				<span className={`px-2 py-1 text-xs rounded ${
					value === 'LONG' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
				}`}>
					{value}
				</span>
			),
		},
		{
			key: 'entryPrice' as keyof TradeLogEntry,
			header: 'Entry',
			width: '80px',
			render: (value: number) => (
				<span className="text-sm">{formatCurrency(value)}</span>
			),
		},
		{
			key: 'exitPrice' as keyof TradeLogEntry,
			header: 'Exit',
			width: '80px',
			render: (value: number | undefined) => (
				<span className="text-sm">
					{value !== undefined ? formatCurrency(value) : '-'}
				</span>
			),
		},
		{
			key: 'quantity' as keyof TradeLogEntry,
			header: 'Qty',
			width: '60px',
			render: (value: number) => (
				<span className="text-sm">{value}</span>
			),
		},
		{
			key: 'pnl' as keyof TradeLogEntry,
			header: 'P&L',
			width: '80px',
			render: (value: number | undefined) => {
				if (value === undefined) return <span>-</span>;
				return (
					<span className={`text-sm font-medium ${
						value > 0 ? 'text-green-600' : value < 0 ? 'text-red-600' : 'text-gray-600'
					}`}>
						{formatCurrency(value)}
					</span>
				);
			},
		},
		{
			key: 'status' as keyof TradeLogEntry,
			header: 'Status',
			width: '80px',
			render: (value: TradeStatus) => (
				<span className={`px-2 py-1 text-xs rounded ${
					value === 'OPEN' ? 'bg-blue-100 text-blue-800' :
					value === 'CLOSED' ? 'bg-gray-100 text-gray-800' :
					'bg-yellow-100 text-yellow-800'
				}`}>
					{value}
				</span>
			),
		},
	], []);

	// Row click handler
	const handleRowClick = useCallback((trade: TradeLogEntry, index: number) => {
		console.log('Trade clicked:', trade, index);
		// Add any row click logic here
	}, []);

	// Get row key for virtual scrolling optimization
	const getRowKey = useCallback((trade: TradeLogEntry, index: number) => trade.id, []);

	return (
		<Card header={
			<div className="flex items-center justify-between">
				<h3 className="text-sm font-semibold">Trading Logs</h3>
				<div className="flex items-center gap-2">
					<label className="flex items-center text-xs">
						<input
							type="checkbox"
							checked={useVirtualScrolling}
							onChange={(e) => setUseVirtualScrolling(e.target.checked)}
							className="mr-1"
						/>
						Virtual Scroll
					</label>
					{isLoading && (
						<div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
					)}
				</div>
			</div>
		}>
			{/* Filters */}
			<div className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-5">
				<input 
					className="rounded border border-gray-300 px-3 py-2 text-sm md:col-span-2" 
					placeholder="Search symbol/pattern" 
					value={search} 
					onChange={handleSearchChange}
				/>
				<select 
					className="rounded border border-gray-300 px-2 py-2 text-sm" 
					value={symbol} 
					onChange={(e) => handleFilterChange('symbol', e.target.value)}
				>
					<option value="all">All Symbols</option>
					{symbols.map((s) => (<option key={s} value={s}>{s}</option>))}
				</select>
				<select 
					className="rounded border border-gray-300 px-2 py-2 text-sm" 
					value={status} 
					onChange={(e) => handleFilterChange('status', e.target.value)}
				>
					<option value="all">All Status</option>
					<option value="OPEN">Open</option>
					<option value="CLOSED">Closed</option>
					<option value="CANCELLED">Cancelled</option>
				</select>
				<select 
					className="rounded border border-gray-300 px-2 py-2 text-sm" 
					value={pnlFilter} 
					onChange={(e) => handleFilterChange('pnlFilter', e.target.value)}
				>
					<option value="all">All P&L</option>
					<option value="profit">Profit</option>
					<option value="loss">Loss</option>
				</select>
			</div>

			{/* Results and Export */}
			<div className="mb-3 flex items-center justify-between">
				<div className="text-xs text-gray-500">
					{filtered.length} results
					{useVirtualScrolling && filtered.length > 100 && (
						<span className="ml-2 text-green-600">(Virtual scrolling enabled)</span>
					)}
				</div>
				<div className="flex gap-2">
					<button 
						className="rounded border px-2 py-1 text-xs hover:bg-gray-50" 
						onClick={() => {
							const csv = exportCSV(filtered);
							const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
							const url = URL.createObjectURL(blob);
							const a = document.createElement('a');
							a.href = url; a.download = 'trades.csv'; a.click();
							URL.revokeObjectURL(url);
						}}
					>
						Export CSV
					</button>
					<button 
						className="rounded border px-2 py-1 text-xs hover:bg-gray-50" 
						onClick={() => {
							const json = exportJSON(filtered);
							const blob = new Blob([json], { type: 'application/json' });
							const url = URL.createObjectURL(blob);
							const a = document.createElement('a');
							a.href = url; a.download = 'trades.json'; a.click();
							URL.revokeObjectURL(url);
						}}
					>
						Export JSON
					</button>
				</div>
			</div>

			{/* Table */}
			{useVirtualScrolling && filtered.length > 50 ? (
				<VirtualScrollTable
					data={filtered}
					columns={columns}
					itemHeight={ROW_HEIGHT}
					height={TABLE_HEIGHT}
					onRowClick={handleRowClick}
					getRowKey={getRowKey}
					emptyMessage="No trading logs found"
					className="border-0"
				/>
			) : (
				<div className="border border-gray-200 rounded-lg overflow-hidden">
					<div className="overflow-auto" style={{ maxHeight: TABLE_HEIGHT }}>
						<table className="min-w-full divide-y divide-gray-200">
							<thead className="bg-gray-50 sticky top-0">
								<tr>
									{columns.map((column) => (
										<th
											key={String(column.key)}
											className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
											style={column.width ? { width: column.width } : undefined}
										>
											{column.header}
										</th>
									))}
								</tr>
							</thead>
							<tbody className="bg-white divide-y divide-gray-200">
								{filtered.map((trade, index) => (
									<tr 
										key={trade.id} 
										className="hover:bg-gray-50 cursor-pointer"
										onClick={() => handleRowClick(trade, index)}
									>
										{columns.map((column) => (
											<td
												key={String(column.key)}
												className="px-3 py-2 text-sm text-gray-900"
												style={column.width ? { width: column.width } : undefined}
											>
												{column.render ? column.render(trade[column.key], trade, index) : String(trade[column.key])}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>
					{filtered.length === 0 && (
						<div className="flex items-center justify-center py-8 text-gray-500 text-sm">
							No trading logs found
						</div>
					)}
				</div>
			)}
		</Card>
	);
};

// Memoized component to prevent unnecessary re-renders
export const TradingLogsWidget = React.memo(TradingLogsWidgetComponent, (prevProps, nextProps) => {
	// Custom comparison function for better performance
	return (
		prevProps.trades === nextProps.trades &&
		prevProps.onSearch === nextProps.onSearch &&
		prevProps.onFilter === nextProps.onFilter &&
		prevProps.isLoading === nextProps.isLoading
	);
});

TradingLogsWidget.displayName = 'TradingLogsWidget';

export default TradingLogsWidget;
