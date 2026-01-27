import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from '../../../pages/Auth/LoginPage';

// Mock the trpc client
vi.mock('../../../lib/trpc', () => ({
  trpc: {
    auth: {
      login: {
        useMutation: () => ({
          mutateAsync: vi.fn().mockResolvedValue({
            success: true,
            user: { 
              id: 1, 
              email: 'test@example.com', 
              name: 'Test User',
              role: 'user'
            },
          }),
          isLoading: false,
          error: null,
        }),
      },
      me: {
        useQuery: () => ({
          data: null,
          isLoading: false,
          error: null,
        }),
      },
    },
  },
}));

// Mock the router
vi.mock('wouter', () => ({
  useLocation: () => ({ pathname: '/login' }),
  useNavigate: () => vi.fn(),
}));

describe('LoginPage', () => {
  let queryClient: QueryClient;
  let user: any;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    user = userEvent.setup();
  });

  const renderLoginPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    );
  };

  it('should render login form correctly', () => {
    renderLoginPage();

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
  });

  it('should show validation errors for empty fields', async () => {
    renderLoginPage();

    const loginButton = screen.getByRole('button', { name: /login/i });
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('should show validation error for invalid email', async () => {
    renderLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(emailInput, 'invalid-email');
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
    });
  });

  it('should show validation error for short password', async () => {
    renderLoginPage();

    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(passwordInput, '123');
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('should submit form with valid data', async () => {
    const mockLogin = vi.fn().mockResolvedValue({
      success: true,
      user: { 
        id: 1, 
        email: 'test@example.com', 
        name: 'Test User',
        role: 'user'
      },
    });

    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          login: {
            useMutation: () => ({
              mutateAsync: mockLogin,
              isLoading: false,
              error: null,
            }),
          },
          me: {
            useQuery: () => ({
              data: null,
              isLoading: false,
              error: null,
            }),
          },
        },
      },
    }));

    renderLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(loginButton);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });
  });

  it('should show loading state during submission', async () => {
    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          login: {
            useMutation: () => ({
              mutateAsync: vi.fn().mockResolvedValue({
                success: true,
                user: { id: 1, email: 'test@example.com' },
              }),
              isLoading: true,
              error: null,
            }),
          },
          me: {
            useQuery: () => ({
              data: null,
              isLoading: false,
              error: null,
            }),
          },
        },
      },
    }));

    renderLoginPage();

    const loginButton = screen.getByRole('button', { name: /login/i });
    expect(loginButton).toBeDisabled();
  });

  it('should show error message on login failure', async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error('Invalid credentials'));

    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          login: {
            useMutation: () => ({
              mutateAsync: mockLogin,
              isLoading: false,
              error: new Error('Invalid credentials'),
            }),
          },
          me: {
            useQuery: () => ({
              data: null,
              isLoading: false,
              error: null,
            }),
          },
        },
      },
    }));

    renderLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('should toggle password visibility', async () => {
    renderLoginPage();

    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i });

    // Initially password should be hidden
    expect(passwordInput.type).toBe('password');

    // Click to show password
    await user.click(toggleButton);
    expect(passwordInput.type).toBe('text');

    // Click to hide password
    await user.click(toggleButton);
    expect(passwordInput.type).toBe('password');
  });

  it('should navigate to signup page', async () => {
    const mockNavigate = vi.fn();
    
    vi.doMock('wouter', () => ({
      useLocation: () => ({ pathname: '/login' }),
      useNavigate: () => mockNavigate,
    }));

    renderLoginPage();

    const signupLink = screen.getByRole('link', { name: /sign up/i });
    await user.click(signupLink);

    expect(mockNavigate).toHaveBeenCalledWith('/signup');
  });
});