import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import App from './App';

// Mock the auth store to simulate authenticated state
vi.mock('./stores/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com', name: 'Test User' },
    login: vi.fn(),
    logout: vi.fn(),
    checkAuth: vi.fn(),
  }),
}));

describe('App routing and layout', () => {
	it('renders login screen when not authenticated', () => {
		// Mock unauthenticated state
		vi.doMock('./stores/authStore', () => ({
			useAuthStore: () => ({
				isAuthenticated: false,
				user: null,
				login: vi.fn(),
				logout: vi.fn(),
				checkAuth: vi.fn(),
			}),
		}));

		render(
			<BrowserRouter>
				<App />
			</BrowserRouter>
		);
		expect(screen.getByText(/Login/i)).toBeInTheDocument();
		expect(screen.getByText(/Sign In/i)).toBeInTheDocument();
	});
});