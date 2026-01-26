import { vi } from 'vitest';

// Mock external APIs and services
export const mockGitHubAPI = {
  repository: {
    name: 'test-repo',
    full_name: 'user/test-repo',
    description: 'A test repository',
    stargazers_count: 100,
    forks_count: 50,
    open_issues_count: 10,
    language: 'TypeScript',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-12-01T00:00:00Z',
    pushed_at: '2023-12-01T00:00:00Z',
    size: 1000,
    default_branch: 'main',
  },
  commits: [
    {
      sha: 'abc123',
      commit: {
        author: { name: 'Test User', email: 'test@example.com', date: '2023-12-01T00:00:00Z' },
        message: 'Initial commit',
      },
    },
    {
      sha: 'def456',
      commit: {
        author: { name: 'Test User', email: 'test@example.com', date: '2023-11-01T00:00:00Z' },
        message: 'Add feature',
      },
    },
  ],
  contributors: [
    { id: 1, login: 'user1', type: 'User', contributions: 50 },
    { id: 2, login: 'user2', type: 'User', contributions: 25 },
  ],
};

export const mockCoinGeckoAPI = {
  coin: {
    id: 'bitcoin',
    symbol: 'btc',
    name: 'Bitcoin',
    current_price: 50000,
    market_cap: 1000000000,
    market_cap_rank: 1,
    total_volume: 100000000,
    high_24h: 52000,
    low_24h: 48000,
    price_change_24h: 2000,
    price_change_percentage_24h: 4.0,
    circulating_supply: 19000000,
    total_supply: 21000000,
    max_supply: 21000000,
    ath: 69000,
    ath_change_percentage: -27.5,
    ath_date: '2021-11-10T14:24:11.849Z',
    atl: 65.53,
    atl_change_percentage: 76285.2,
    atl_date: '2013-07-05T00:00:00Z',
    last_updated: '2023-12-01T00:00:00Z',
  },
  trending: [
    {
      item: {
        id: 'ethereum',
        name: 'Ethereum',
        symbol: 'eth',
        market_cap_rank: 2,
        thumb: 'https://example.com/eth.png',
        small: 'https://example.com/eth-small.png',
        large: 'https://example.com/eth-large.png',
        slug: 'ethereum',
        price_btc: 0.05,
        score: 0,
        data: {
          price: '3000',
          price_change_percentage_24h: { usd: 2.5 },
          market_cap: '360000000000',
          market_cap_change_percentage_24h: { usd: 1.8 },
          total_volume: { usd: '15000000000' },
        },
      },
    },
  ],
};

export const mockEmailService = {
  sendEmail: vi.fn().mockResolvedValue({ success: true, messageId: 'test-message-id' }),
};

export const mockLLMService = {
  generateText: vi.fn().mockResolvedValue({
    text: 'This is a mock AI analysis response.',
    usage: { promptTokens: 100, completionTokens: 50, totalTokens: 150 },
  }),
  generateAuditSummary: vi.fn().mockResolvedValue({
    summary: 'This project shows moderate potential with some areas for improvement.',
    recommendations: ['Improve code documentation', 'Increase test coverage'],
    riskFactors: ['Limited community engagement', 'Recent code changes'],
  }),
};

// Mock fetch for API calls
export const mockFetch = vi.fn();

// Mock environment variables
export const mockEnv = {
  DATABASE_URL: 'postgresql://test_user:test_password@localhost:5432/investment_auditor_test',
  JWT_SECRET: 'test-jwt-secret',
  OPENAI_API_KEY: 'test-openai-key',
  GEMINI_API_KEY: 'test-gemini-key',
  COINGECKO_API_KEY: 'test-coingecko-key',
  EMAIL_FROM: 'test@example.com',
  EMAIL_HOST: 'smtp.example.com',
  EMAIL_USER: 'test@example.com',
  EMAIL_PASS: 'test-password',
};

// Setup global mocks
export function setupGlobalMocks() {
  vi.mock('undici', () => ({
    fetch: mockFetch,
  }));
  
  vi.mock('../server/services/emailService', () => ({
    sendProjectNotificationEmail: mockEmailService.sendEmail,
    sendAuditCompletionEmail: mockEmailService.sendEmail,
    sendHotProjectAlert: mockEmailService.sendEmail,
  }));
  
  vi.mock('../server/services/geminiAnalyzer', () => ({
    geminiAnalyzer: mockLLMService,
  }));
  
  // Mock environment variables
  Object.entries(mockEnv).forEach(([key, value]) => {
    process.env[key] = value;
  });
}

// Reset all mocks
export function resetAllMocks() {
  vi.clearAllMocks();
  mockFetch.mockClear();
  mockEmailService.sendEmail.mockClear();
  mockLLMService.generateText.mockClear();
  mockLLMService.generateAuditSummary.mockClear();
}