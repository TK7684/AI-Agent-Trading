import React from 'react';
import { Card } from '@components/Common/Card';

interface ChartErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ChartErrorBoundaryProps {
  children: React.ReactNode;
  symbol?: string;
  timeframe?: string;
  onRetry?: () => void;
}

export class ChartErrorBoundary extends React.Component<ChartErrorBoundaryProps, ChartErrorBoundaryState> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Chart Error Boundary caught error:', error, errorInfo);
    this.setState({ errorInfo });
    
    // Log chart-specific error details
    console.error('Chart Error Details:', {
      symbol: this.props.symbol,
      timeframe: this.props.timeframe,
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack
    });
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    if (this.props.onRetry) {
      this.props.onRetry();
    }
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      const { symbol, timeframe } = this.props;
      const chartTitle = symbol && timeframe ? `${symbol} (${timeframe})` : 'Chart';
      
      return (
        <Card header={<h3 className="text-sm font-semibold">Chart - {chartTitle}</h3>}>
          <div className="flex flex-col items-center justify-center h-80 p-6 text-center">
            <div className="mb-4 text-red-500">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Chart Error</h4>
            <p className="text-sm text-gray-600 mb-4">
              Failed to render chart for {chartTitle}. This might be due to invalid data or a rendering issue.
            </p>
            <div className="flex gap-2">
              <button
                onClick={this.handleRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
              >
                Reload Page
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-sm text-gray-500">Error Details</summary>
                <pre className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded overflow-auto max-h-32">
                  {this.state.error.message}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </Card>
      );
    }

    return this.props.children;
  }
}

export default ChartErrorBoundary;