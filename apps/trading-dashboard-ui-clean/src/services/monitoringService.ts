// Lightweight monitoring service stub. If VITE_SENTRY_DSN is provided, this attempts to initialize Sentry via a global if present.

interface MonitoringOptions {
	dsn?: string;
	env?: string;
}

class MonitoringService {
	private initialized = false;

	init(options: MonitoringOptions): void {
		if (this.initialized) return;
		const dsn = options.dsn || (import.meta as any).env?.VITE_SENTRY_DSN;
		if (!dsn) {
			return;
		}
		// If Sentry SDK is available globally, initialize; otherwise, log.
		// You can include Sentry via npm or a script tag if CSP allows.
		const Sentry = (window as any).Sentry;
		if (Sentry && Sentry.init) {
			Sentry.init({ dsn, environment: options.env || (import.meta as any).env?.VITE_SENTRY_ENV || 'production' });
			this.initialized = true;
			console.log('Sentry initialized');
		} else {
			console.warn('Sentry DSN provided but SDK not found. Add @sentry/browser or a script include.');
		}
	}

	captureException(error: unknown): void {
		const Sentry = (window as any).Sentry;
		if (Sentry && Sentry.captureException) {
			Sentry.captureException(error);
		} else {
			console.error('Capture exception:', error);
		}
	}
}

export const monitoringService = new MonitoringService();

export default monitoringService;
