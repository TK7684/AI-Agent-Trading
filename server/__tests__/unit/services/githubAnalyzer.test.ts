import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { analyzeGitHub } from '../../../services/githubAnalyzer';
import { mockGitHubAPI, setupGlobalMocks, resetAllMocks } from '../../../../test-utils/mocks';

// Create mock fetch
const mockFetch = vi.fn();

// Mock the LLM service
vi.mock('../../../_core/llm', () => ({
  invokeLLM: vi.fn().mockResolvedValue({
    choices: [{
      message: {
        content: 'Mock AI analysis response'
      }
    }]
  })
}));

// Mock the cache service to disable caching in tests
vi.mock('../../../services/analysisCache', () => ({
  getCachedGitHubAnalysis: vi.fn(() => null),
  setCachedGitHubAnalysis: vi.fn(),
  getCachedMarketData: vi.fn(() => null),
  setCachedMarketData: vi.fn(),
  getCachedGoPlusSecurity: vi.fn(() => null),
  setCachedGoPlusSecurity: vi.fn(),
}));

describe('GitHub Analyzer', () => {
  beforeEach(() => {
    setupGlobalMocks();
    vi.clearAllMocks();
    // Mock global fetch
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    resetAllMocks();
    vi.unstubAllGlobals();
  });

  it('should analyze a valid GitHub repository', async () => {
    // Mock API responses
    mockFetch
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.repository,
        ok: true,
        headers: {
          get: (name: string) => null
        }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.contributors,
        ok: true,
        headers: {
          get: (name: string) => name === 'Link' ? '<https://api.github.com/repos/user/test-repo/contributors?page=2>; rel="next", <https://api.github.com/repos/user/test-repo/contributors?page=2>; rel="last"' : null
        }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.commits,
        ok: true,
        headers: {
          get: (name: string) => name === 'Link' ? '<https://api.github.com/repos/user/test-repo/commits?page=50>; rel="last"' : null
        }
      });

    const result = await analyzeGitHub('https://github.com/user/test-repo');

    expect(result).toBeDefined();
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(100);
    expect(result.data).toBeDefined();
    expect(result.data.stars).toBe(mockGitHubAPI.repository.stargazers_count);
    expect(result.data.forks).toBe(mockGitHubAPI.repository.forks_count);
    expect(result.data.openIssues).toBe(mockGitHubAPI.repository.open_issues_count);
    expect(result.analysis).toBeDefined();
    expect(result.strengths).toBeDefined();
    expect(result.issues).toBeDefined();
  });

  it('should calculate appropriate score based on repository metrics', async () => {
    // Create a repository with good metrics
    const goodRepo = {
      ...mockGitHubAPI.repository,
      stargazers_count: 1000,
      forks_count: 500,
      open_issues_count: 5,
      pushed_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
      created_at: '2023-01-01T00:00:00Z',
      updated_at: new Date().toISOString(),
    };

    mockFetch
      .mockResolvedValueOnce({
        json: async () => goodRepo,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.contributors,
        ok: true,
        headers: { get: (name: string) => name === 'Link' ? '<https://api.github.com/repos/user/good-repo/contributors?page=10>; rel="last"' : null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.commits,
        ok: true,
        headers: { get: (name: string) => name === 'Link' ? '<https://api.github.com/repos/user/good-repo/commits?page=100>; rel="last"' : null }
      });

    const result = await analyzeGitHub('https://github.com/user/good-repo');

    expect(result.score).toBeGreaterThan(70);
    expect(result.strengths.length).toBeGreaterThan(0);
  });

  it('should handle repositories with poor metrics', async () => {
    // Create a repository with poor metrics
    const poorRepo = {
      ...mockGitHubAPI.repository,
      stargazers_count: 5,
      forks_count: 1,
      open_issues_count: 50,
      pushed_at: '2020-01-01T00:00:00Z', // Very old commit
      created_at: '2020-01-01T00:00:00Z',
      updated_at: '2020-01-01T00:00:00Z',
    };

    mockFetch
      .mockResolvedValueOnce({
        json: async () => poorRepo,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.contributors.slice(0, 1),
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.commits.slice(0, 2),
        ok: true,
        headers: { get: () => null }
      });

    const result = await analyzeGitHub('https://github.com/user/poor-repo');

    expect(result.score).toBeLessThan(40);
    expect(result.issues.length).toBeGreaterThan(0);
  });

  it('should handle invalid GitHub URLs', async () => {
    const result = await analyzeGitHub('invalid-url');

    expect(result.score).toBe(0);
    expect(result.issues).toContain('Invalid or inaccessible GitHub repository');
  });

  it('should handle private repositories', async () => {
    mockFetch.mockResolvedValueOnce({
      json: async () => ({ message: 'Not Found' }),
      ok: false,
      status: 404,
      headers: { get: () => null }
    });

    const result = await analyzeGitHub('https://github.com/user/private-repo');

    expect(result.score).toBe(0);
    expect(result.issues).toContain('Invalid or inaccessible GitHub repository');
  });

  it('should handle API rate limiting', async () => {
    mockFetch.mockResolvedValueOnce({
      json: async () => ({ message: 'API rate limit exceeded' }),
      ok: false,
      status: 403,
      headers: { get: () => null }
    });

    const result = await analyzeGitHub('https://github.com/user/test-repo');

    expect(result.score).toBe(0);
    expect(result.issues).toContain('Invalid or inaccessible GitHub repository');
  });

  it('should handle network errors', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const result = await analyzeGitHub('https://github.com/user/test-repo');

    expect(result.score).toBe(0);
    expect(result.issues).toContain('Invalid or inaccessible GitHub repository');
  });

  it('should extract repository owner and name correctly', async () => {
    mockFetch
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.repository,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.contributors,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.commits,
        ok: true,
        headers: { get: () => null }
      });

    await analyzeGitHub('https://github.com/complex-user-name/complex-repo-name-123');

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.github.com/repos/complex-user-name/complex-repo-name-123',
      expect.objectContaining({
        headers: expect.objectContaining({
          'Accept': 'application/vnd.github.v3+json',
          'User-Agent': 'Crypto-Project-Auditor'
        })
      })
    );
  });

  it('should handle repositories with no commits', async () => {
    mockFetch
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.repository,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.contributors,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => [],
        ok: true,
        headers: { get: () => null }
      });

    const result = await analyzeGitHub('https://github.com/user/empty-repo');

    expect(result.score).toBeLessThan(30);
    expect(result.issues.length).toBeGreaterThan(0);
  });

  it('should handle repositories with no contributors', async () => {
    mockFetch
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.repository,
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => [],
        ok: true,
        headers: { get: () => null }
      })
      .mockResolvedValueOnce({
        json: async () => mockGitHubAPI.commits,
        ok: true,
        headers: { get: () => null }
      });

    const result = await analyzeGitHub('https://github.com/user/no-contributors-repo');

    expect(result.score).toBeLessThan(40);
    expect(result.issues.length).toBeGreaterThan(0);
  });
});
