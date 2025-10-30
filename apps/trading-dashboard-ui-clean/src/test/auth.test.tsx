import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Login } from '@components/Auth/Login';
import ProtectedRoute from '@components/Auth/ProtectedRoute';
import { useAuthStore } from '@stores/authStore';

function Secret() { return <div>Secret</div>; }

describe('Authentication', () => {
	beforeEach(() => {
		useAuthStore.setState({ token: null, refreshToken: null, expiresAt: null, user: null, authenticated: false });
	});

	it('redirects to login when not authenticated', () => {
		render(
			<MemoryRouter initialEntries={["/secret"]}>
				<Routes>
					<Route path="/login" element={<div>Login Page</div>} />
					<Route path="/secret" element={<ProtectedRoute><Secret /></ProtectedRoute>} />
				</Routes>
			</MemoryRouter>
		);
		expect(screen.getByText(/Login Page/i)).toBeInTheDocument();
	});

	it('logs in and sets auth store', () => {
		render(
			<MemoryRouter>
				<Login />
			</MemoryRouter>
		);
		fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'a@b.com' } });
		fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'pass' } });
		fireEvent.click(screen.getByText(/Sign In/i));
		expect(useAuthStore.getState().authenticated).toBe(true);
	});
});
