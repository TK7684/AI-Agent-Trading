import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiService } from '@services/apiService';
import { WebSocketService } from '@services/websocketService';

const originalFetch = global.fetch;
const OriginalWebSocket = global.WebSocket;

class MockWebSocket {
	static instances: MockWebSocket[] = [];
	onopen: ((ev: any) => any) | null = null;
	onmessage: ((ev: any) => any) | null = null;
	onclose: ((ev: any) => any) | null = null;
	onerror: ((ev: any) => any) | null = null;
	url: string;
	listeners: Record<string, Function[]> = {};
	constructor(url: string) {
		this.url = url;
		MockWebSocket.instances.push(this);
		setTimeout(() => this.onopen && this.onopen({} as any), 0);
	}
	addEventListener(type: string, cb: any) { (this.listeners[type] ||= []).push(cb); }
	removeEventListener() {}
	send(_data: any) {}
	close() { this.onclose && this.onclose({ code: 1000, reason: 'close' } as any); }
	dispatch(type: string, data: any) { (this.listeners[type]||[]).forEach((cb) => cb(data)); }
}

beforeEach(() => {
	(global as any).fetch = vi.fn(async () => new Response(JSON.stringify({ hello: 'world' }), { status: 200, headers: { 'Content-Type': 'application/json' } as any }));
	(global as any).WebSocket = MockWebSocket as any;
});

afterEach(() => {
	(global as any).fetch = originalFetch;
	(global as any).WebSocket = OriginalWebSocket;
});

describe('Integration: API & WebSocket', () => {
	it('calls API and parses JSON', async () => {
		const api = new ApiService('http://localhost');
		const res = await api.get<any>('/test');
		expect(res.success).toBe(true);
		expect(res.data).toEqual({ hello: 'world' });
	});

	it('connects WebSocket and receives message', async () => {
		const ws = new WebSocketService({ url: 'ws://localhost' });
		let got = false;
		ws.setEventHandlers({ onMessage: () => { got = true; } });
		await ws.connect();
		const instance = MockWebSocket.instances[0];
		instance.dispatch('message', { data: JSON.stringify({ type: 'PING', data: {} }) });
		expect(got).toBe(true);
	});
});
