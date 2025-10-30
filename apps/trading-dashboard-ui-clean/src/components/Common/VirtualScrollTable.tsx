import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { calculateVirtualScroll } from '@/utils/performance';

interface Column<T> {
  key: keyof T;
  header: string;
  width?: string;
  render?: (value: any, item: T, index: number) => React.ReactNode;
  className?: string;
}

interface VirtualScrollTableProps<T> {
  data: T[];
  columns: Column<T>[];
  itemHeight: number;
  height: number;
  overscan?: number;
  className?: string;
  onRowClick?: (item: T, index: number) => void;
  getRowKey?: (item: T, index: number) => string | number;
  emptyMessage?: string;
  stickyHeader?: boolean;
}

export function VirtualScrollTable<T>({
  data,
  columns,
  itemHeight,
  height,
  overscan = 5,
  className = '',
  onRowClick,
  getRowKey,
  emptyMessage = 'No data available',
  stickyHeader = true,
}: VirtualScrollTableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  // Calculate virtual scroll parameters
  const virtualScroll = useMemo(() => {
    return calculateVirtualScroll(data.length, {
      itemHeight,
      containerHeight: height,
      overscan,
      scrollTop,
    });
  }, [data.length, itemHeight, height, overscan, scrollTop]);

  // Get visible items
  const visibleItems = useMemo(() => {
    return data.slice(virtualScroll.startIndex, virtualScroll.endIndex + 1);
  }, [data, virtualScroll.startIndex, virtualScroll.endIndex]);

  // Handle scroll events with throttling
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = event.currentTarget.scrollTop;
    setScrollTop(newScrollTop);
  }, []);

  // Render table header
  const renderHeader = () => (
    <thead 
      className={`bg-gray-50 ${stickyHeader ? 'sticky top-0 z-10' : ''}`}
      style={stickyHeader ? { position: 'sticky', top: 0 } : undefined}
    >
      <tr>
        {columns.map((column) => (
          <th
            key={String(column.key)}
            className={`px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${column.className || ''}`}
            style={column.width ? { width: column.width } : undefined}
          >
            {column.header}
          </th>
        ))}
      </tr>
    </thead>
  );

  // Render table row
  const renderRow = useCallback((item: T, index: number, actualIndex: number) => {
    const key = getRowKey ? getRowKey(item, actualIndex) : actualIndex;
    
    return (
      <tr
        key={key}
        className={`border-b border-gray-200 hover:bg-gray-50 ${onRowClick ? 'cursor-pointer' : ''}`}
        onClick={onRowClick ? () => onRowClick(item, actualIndex) : undefined}
        style={{
          position: 'absolute',
          top: (virtualScroll.startIndex + index) * itemHeight,
          left: 0,
          right: 0,
          height: itemHeight,
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {columns.map((column) => {
          const value = item[column.key];
          const content = column.render ? column.render(value, item, actualIndex) : String(value);
          
          return (
            <td
              key={String(column.key)}
              className={`px-3 py-2 text-sm text-gray-900 ${column.className || ''}`}
              style={column.width ? { width: column.width, flexShrink: 0 } : { flex: 1 }}
            >
              {content}
            </td>
          );
        })}
      </tr>
    );
  }, [columns, virtualScroll.startIndex, itemHeight, onRowClick, getRowKey]);

  // Empty state
  if (data.length === 0) {
    return (
      <div className={`border border-gray-200 rounded-lg ${className}`}>
        <table className="min-w-full divide-y divide-gray-200">
          {renderHeader()}
        </table>
        <div 
          className="flex items-center justify-center text-gray-500 text-sm"
          style={{ height: height - 40 }} // Subtract header height
        >
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className={`border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      <div
        ref={containerRef}
        className="overflow-auto"
        style={{ height }}
        onScroll={handleScroll}
      >
        <table className="min-w-full divide-y divide-gray-200">
          {renderHeader()}
          <tbody 
            className="bg-white divide-y divide-gray-200 relative"
            style={{ height: virtualScroll.totalHeight }}
          >
            {visibleItems.map((item, index) => 
              renderRow(item, index, virtualScroll.startIndex + index)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default VirtualScrollTable;