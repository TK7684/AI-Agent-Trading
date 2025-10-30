import React from 'react';
import { Card } from '@components/Common/Card';
import Spinner from '@components/Common/Spinner';

interface ChartLoadingStateProps {
  symbol?: string;
  timeframe?: string;
  message?: string;
}

export const ChartLoadingState: React.FC<ChartLoadingStateProps> = ({ 
  symbol, 
  timeframe, 
  message = 'Loading chart data...' 
}) => {
  const chartTitle = symbol && timeframe ? `${symbol} (${timeframe})` : 'Chart';
  
  return (
    <Card header={<h3 className="text-sm font-semibold">Chart - {chartTitle}</h3>}>
      <div className="flex flex-col items-center justify-center h-80 p-6">
        <Spinner size={32} />
        <p className="mt-4 text-sm text-gray-600">{message}</p>
        {symbol && timeframe && (
          <p className="mt-2 text-xs text-gray-500">
            Fetching data for {symbol} ({timeframe})
          </p>
        )}
      </div>
    </Card>
  );
};

export default ChartLoadingState;