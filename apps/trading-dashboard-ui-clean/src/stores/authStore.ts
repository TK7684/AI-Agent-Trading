import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';

interface UserInfo {
	id: string;
	email: string;
	name: string;
	roles: string[];
}

interface AuthState {
	token: string | null;
	refreshToken: string | null;
	expiresAt: number | null; // epoch ms
	user: UserInfo | null;
	authenticated: boolean;

	setSession: (token: string, refreshToken: string, expiresInSec: number, user: UserInfo) => void;
	clearSession: () => void;
	isExpired: () => boolean;
	hasRole: (role: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
	devtools(
		persist(
			(set, get) => ({
				token: null,
				refreshToken: null,
				expiresAt: null,
				user: null,
				authenticated: false,

				setSession: (token, refreshToken, expiresInSec, user) =>
					set({
						token,
						refreshToken,
						expiresAt: Date.now() + expiresInSec * 1000,
						user,
						authenticated: true,
					}),

				clearSession: () => set({ token: null, refreshToken: null, expiresAt: null, user: null, authenticated: false }),

				isExpired: () => {
					const { expiresAt } = get();
					return !expiresAt || Date.now() >= expiresAt;
				},

				hasRole: (role) => {
					const { user } = get();
					return !!user?.roles?.includes(role);
				},
			}),
			{ name: 'auth-store' }
		)
	)
);

export default useAuthStore;
