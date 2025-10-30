import { describe, it, expect } from 'vitest';
import { ApiService } from '@services/apiService';

// Minimal mock fetch for deduplication behavior
const originalFetch = global.fetch;

describe('Performance optimizations', () => {
	it('deduplicates in-flight GET requests', async () => {
		let calls = 0;
		(global as any).fetch = async () => {
			calls += 1;
			return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } as any });
		};
		const api = new ApiService('http://localhost');
		const p1 = api.get<any>('/test', { q: 'x' });
		const p2 = api.get<any>('/test', { q: 'x' });
		await Promise.all([p1, p2]);
		expect(calls).toBe(1);
		(global as any).fetch = originalFetch;
	});
});
