import React from 'react';

interface ErrorBoundaryState {
	hasError: boolean;
	error?: Error;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
	state: ErrorBoundaryState = { hasError: false };

	static getDerivedStateFromError(error: Error): ErrorBoundaryState {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
		console.error('ErrorBoundary caught', error, errorInfo);
	}

	handleReload = (): void => {
		this.setState({ hasError: false, error: undefined });
		window.location.reload();
	};

	render(): React.ReactNode {
		if (this.state.hasError) {
			return (
				<div className="m-4 rounded border border-red-300 bg-red-50 p-4 text-red-900">
					<div className="mb-2 font-semibold">Something went wrong.</div>
					<div className="mb-3 text-sm">Please try reloading the page. If the problem persists, contact support.</div>
					<button className="rounded border px-3 py-1 text-sm" onClick={this.handleReload}>Reload</button>
				</div>
			);
		}
		return this.props.children;
	}
}

export default ErrorBoundary;
