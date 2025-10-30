import { ApiService } from './apiService';
import { WebSocketService } from './websocketService';
import { useTradingStore } from '@/stores/tradingStore';
import { useSystemStore } from '@/stores/systemStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { useAuthStore } from '@/stores/authStore';
import type { AnyWebSocketMessage, NotificationUpdate } from '@/types/websocket';

class SyncService {
	private api: ApiService;
	private ws: WebSocketService;
	// private isConfigured = false;
	private unsubscribeAuth?: () => void;

	constructor(api?: ApiService, ws?: WebSocketService) {
		this.api = api || new ApiService();
		this.ws = ws || new WebSocketService({});
		this.ws.setEventHandlers({ onMessage: (msg) => this.routeMessage(msg) });
	}

	private configureAuth(): void {
		const { token } = useAuthStore.getState();
		if (token) {
			this.api.setAuthToken(token);
			this.ws.setToken(token);
			// this.isConfigured = true;
		}
		// Subscribe to future auth changes
		if (!this.unsubscribeAuth) {
			// Zustand subscribe signature: (listener) => unsubscribe
			this.unsubscribeAuth = (useAuthStore as any).subscribe((state: any) => {
				if (state.token) {
					this.api.setAuthToken(state.token);
					this.ws.setToken(state.token);
					// this.isConfigured = true;
				} else {
					// this.isConfigured = false;
				}
			});
		}
	}

	async initialize(): Promise<void> {
		this.configureAuth();
		const trading = useTradingStore.getState();
		const system = useSystemStore.getState();

		const [perfRes, logsRes, statusRes, healthRes] = await Promise.all([
			this.api.get<any>('/trading/performance'),
			this.api.get<any>('/trading/trades', { page: 1, pageSize: 50 }),
			this.api.get<any>('/system/agents'),
			this.api.get<any>('/system/health'),
		]);

		if (perfRes.success && perfRes.data) trading.setPerformanceMetrics(perfRes.data);
		if (logsRes.success && logsRes.data?.items) trading.setTradingLogs(logsRes.data.items);
		if (statusRes.success && statusRes.data) trading.setAgentStatus(statusRes.data);
		if (healthRes.success && healthRes.data) system.setSystemHealth(healthRes.data);
	}

	async connect(): Promise<void> {
		this.configureAuth();
		await this.ws.connect();
		this.ws.subscribe('trading', () => {});
		this.ws.subscribe('system', () => {});
		this.ws.subscribe('notifications', () => {});
	}

	private routeMessage(message: AnyWebSocketMessage): void {
		const trading = useTradingStore.getState();
		const system = useSystemStore.getState();
		const notif = useNotificationStore.getState();

		switch (message.type) {
			case 'PNL_UPDATE':
				trading.setPerformanceMetrics(message.data as any);
				break;
			case 'TRADE_OPENED':
			case 'TRADE_CLOSED':
			case 'TRADE_UPDATED':
				trading.addTradingLog(message.data as any);
				break;
			case 'STATUS_CHANGE':
				system.setIsConnected(true);
				trading.setAgentStatus(message.data as any);
				break;
			case 'METRICS_UPDATE':
			case 'HEALTH_CHECK':
				system.setSystemHealth(message.data as any);
				break;
			case 'NOTIFICATION_NEW':
				notif.addNotification({ 
					type: (message as NotificationUpdate).data.type, 
					title: (message as any).data.title, 
					message: (message as any).data.message,
					persistent: false,
					priority: 'normal',
					category: 'system'
				});
				break;
			default:
				break;
		}
	}
}

export const syncService = new SyncService();

export default syncService;
