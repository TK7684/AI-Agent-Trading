import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../stores/uiStore';

// Reset a subset of persisted state between tests
const resetUI = () => {
	useUIStore.setState({
		widgets: [
			{ id: 'performance', type: 'performance', position: { x: 0, y: 0, w: 6, h: 4 }, visible: true, config: {} },
			{ id: 'chart', type: 'chart', position: { x: 6, y: 0, w: 6, h: 8 }, visible: true, config: { symbol: 'BTCUSDT', timeframe: '1h' } },
			{ id: 'logs', type: 'logs', position: { x: 0, y: 4, w: 6, h: 4 }, visible: true, config: { pageSize: 20 } },
			{ id: 'controls', type: 'controls', position: { x: 0, y: 8, w: 4, h: 4 }, visible: true, config: {} },
			{ id: 'system', type: 'system', position: { x: 4, y: 8, w: 4, h: 4 }, visible: true, config: {} },
		],
		sidebarCollapsed: false,
		theme: 'light',
		compactMode: false,
		refreshInterval: 5000,
		autoRefresh: true,
		activeModal: null,
	});
};

describe('UIStore', () => {
	beforeEach(() => {
		resetUI();
	});

	it('manages widgets and selectors', () => {
		expect(useUIStore.getState().getVisibleWidgets().length).toBeGreaterThan(0);
		useUIStore.getState().updateWidget('performance', { visible: false });
		expect(useUIStore.getState().getVisibleWidgets().find((w) => w.id === 'performance')).toBeUndefined();
		const widget = useUIStore.getState().getWidgetById('chart');
		expect(widget?.id).toBe('chart');

		useUIStore.getState().addWidget({ id: 'extra', type: 'logs', position: { x: 0, y: 12, w: 4, h: 4 }, visible: true, config: {} });
		expect(useUIStore.getState().widgets.find((w) => w.id === 'extra')).toBeTruthy();
		useUIStore.getState().removeWidget('extra');
		expect(useUIStore.getState().widgets.find((w) => w.id === 'extra')).toBeFalsy();
	});

	it('toggles sidebar, theme, compact, refresh, modal', () => {
		useUIStore.getState().setSidebarCollapsed(true);
		useUIStore.getState().setTheme('dark');
		useUIStore.getState().setCompactMode(true);
		useUIStore.getState().setRefreshInterval(10000);
		useUIStore.getState().setAutoRefresh(false);
		useUIStore.getState().setActiveModal('settings');

		expect(useUIStore.getState().sidebarCollapsed).toBe(true);
		expect(useUIStore.getState().theme).toBe('dark');
		expect(useUIStore.getState().compactMode).toBe(true);
		expect(useUIStore.getState().refreshInterval).toBe(10000);
		expect(useUIStore.getState().autoRefresh).toBe(false);
		expect(useUIStore.getState().activeModal).toBe('settings');
	});

	it('resets layout to defaults', () => {
		useUIStore.getState().setWidgets([]);
		useUIStore.getState().resetLayout();
		expect(useUIStore.getState().widgets.length).toBeGreaterThan(0);
	});
});

