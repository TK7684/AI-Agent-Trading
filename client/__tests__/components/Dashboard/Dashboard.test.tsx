import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from '../../../pages/Dashboard';

// Mock the trpc client
const mockProjects = [
  {
    id: 1,
    name: 'Test Project 1',
    description: 'First test project',
    status: 'completed',
    createdAt: new Date('2023-12-01'),
    overallScore: 75,
    riskLevel: 'medium',
  },
  {
    id: 2,
    name: 'Test Project 2',
    description: 'Second test project',
    status: 'analyzing',
    createdAt: new Date('2023-12-02'),
  },
];

vi.mock('../../../lib/trpc', () => ({
  trpc: {
    auth: {
      me: {
        useQuery: () => ({
          data: { 
            id: 1, 
            email: 'test@example.com', 
            name: 'Test User',
            role: 'user'
          },
          isLoading: false,
          error: null,
        }),
      },
    },
    project: {
      list: {
        useQuery: () => ({
          data: mockProjects,
          isLoading: false,
          error: null,
        }),
      },
    },
  },
}));

// Mock the router
vi.mock('wouter', () => ({
  useLocation: () => ({ pathname: '/dashboard' }),
  useNavigate: () => vi.fn(),
}));

describe('Dashboard', () => {
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

  const renderDashboard = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <Dashboard />
      </QueryClientProvider>
    );
  };

  it('should render dashboard correctly', () => {
    renderDashboard();

    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/test user/i)).toBeInTheDocument();
    expect(screen.getByText(/test@example.com/i)).toBeInTheDocument();
  });

  it('should display user projects', () => {
    renderDashboard();

    expect(screen.getByText(/test project 1/i)).toBeInTheDocument();
    expect(screen.getByText(/test project 2/i)).toBeInTheDocument();
    expect(screen.getByText(/first test project/i)).toBeInTheDocument();
    expect(screen.getByText(/second test project/i)).toBeInTheDocument();
  });

  it('should show project status badges', () => {
    renderDashboard();

    expect(screen.getByText(/completed/i)).toBeInTheDocument();
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
  });

  it('should show project scores and risk levels', () => {
    renderDashboard();

    expect(screen.getByText(/75/i)).toBeInTheDocument();
    expect(screen.getByText(/medium risk/i)).toBeInTheDocument();
  });

  it('should navigate to project details when clicking on a project', async () => {
    const mockNavigate = vi.fn();
    
    vi.doMock('wouter', () => ({
      useLocation: () => ({ pathname: '/dashboard' }),
      useNavigate: () => mockNavigate,
    }));

    renderDashboard();

    const projectCard = screen.getByText(/test project 1/i);
    await user.click(projectCard);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/audit/1');
    });
  });

  it('should show loading state while fetching projects', () => {
    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          me: {
            useQuery: () => ({
              data: { 
                id: 1, 
                email: 'test@example.com', 
                name: 'Test User',
                role: 'user'
              },
              isLoading: false,
              error: null,
            }),
          },
        },
        project: {
          list: {
            useQuery: () => ({
              data: [],
              isLoading: true,
              error: null,
            }),
          },
        },
      },
    }));

    renderDashboard();

    expect(screen.getByTestId('projects-loading')).toBeInTheDocument();
  });

  it('should show error message when projects fail to load', () => {
    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          me: {
            useQuery: () => ({
              data: { 
                id: 1, 
                email: 'test@example.com', 
                name: 'Test User',
                role: 'user'
              },
              isLoading: false,
              error: null,
            }),
          },
        },
        project: {
          list: {
            useQuery: () => ({
              data: [],
              isLoading: false,
              error: new Error('Failed to load projects'),
            }),
          },
        },
      },
    }));

    renderDashboard();

    expect(screen.getByText(/failed to load projects/i)).toBeInTheDocument();
  });

  it('should show empty state when user has no projects', () => {
    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          me: {
            useQuery: () => ({
              data: { 
                id: 1, 
                email: 'test@example.com', 
                name: 'Test User',
                role: 'user'
              },
              isLoading: false,
              error: null,
            }),
          },
        },
        project: {
          list: {
            useQuery: () => ({
              data: [],
              isLoading: false,
              error: null,
            }),
          },
        },
      },
    }));

    renderDashboard();

    expect(screen.getByText(/no projects yet/i)).toBeInTheDocument();
    expect(screen.getByText(/create your first project to get started/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create new project/i })).toBeInTheDocument();
  });

  it('should navigate to new project page when clicking create button', async () => {
    const mockNavigate = vi.fn();
    
    vi.doMock('wouter', () => ({
      useLocation: () => ({ pathname: '/dashboard' }),
      useNavigate: () => mockNavigate,
    }));

    vi.doMock('../../../lib/trpc', () => ({
      trpc: {
        auth: {
          me: {
            useQuery: () => ({
              data: { 
                id: 1, 
                email: 'test@example.com', 
                name: 'Test User',
                role: 'user'
              },
              isLoading: false,
              error: null,
            }),
          },
        },
        project: {
          list: {
            useQuery: () => ({
              data: [],
              isLoading: false,
              error: null,
            }),
          },
        },
      },
    }));

    renderDashboard();

    const createButton = screen.getByRole('button', { name: /create new project/i });
    await user.click(createButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/new-audit');
    });
  });

  it('should filter projects by status', async () => {
    renderDashboard();

    // Check if filter buttons exist
    expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /completed/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyzing/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /pending/i })).toBeInTheDocument();

    // Filter by completed status
    const completedButton = screen.getByRole('button', { name: /completed/i });
    await user.click(completedButton);

    // Should only show completed projects
    await waitFor(() => {
      expect(screen.getByText(/test project 1/i)).toBeInTheDocument();
      expect(screen.queryByText(/test project 2/i)).not.toBeInTheDocument();
    });
  });

  it('should sort projects by creation date', async () => {
    renderDashboard();

    // Check if sort dropdown exists
    expect(screen.getByRole('button', { name: /sort by/i })).toBeInTheDocument();

    // Open sort dropdown
    const sortButton = screen.getByRole('button', { name: /sort by/i });
    await user.click(sortButton);

    // Select oldest first
    const oldestFirstOption = screen.getByText(/oldest first/i);
    await user.click(oldestFirstOption);

    // Projects should be reordered
    await waitFor(() => {
      const projectCards = screen.getAllByTestId('project-card');
      expect(projectCards[0]).toHaveTextContent(/test project 1/i);
      expect(projectCards[1]).toHaveTextContent(/test project 2/i);
    });
  });
});