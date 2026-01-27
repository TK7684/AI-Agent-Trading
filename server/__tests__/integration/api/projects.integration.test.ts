/**
 * Projects API Integration Tests
 * Tests the project router with database interactions
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { eq } from 'drizzle-orm';
import { getTestDb, resetTestDb, seedTestDb } from '../../../../test-utils/database';
import { createTestCaller, createAuthenticatedCaller, createUnauthenticatedCaller } from '../../../../test-utils/trpc';
import { users, projects, auditReports } from '@drizzle/schema';

// Mock external services
vi.mock('../../../services/githubAnalyzer', () => ({
  analyzeGitHub: vi.fn(() => Promise.resolve({
    score: 75,
    data: { commits: 100, contributors: 5 },
    analysis: 'Good GitHub activity',
    strengths: ['Active development'],
    issues: ['Low documentation'],
  })),
}));

vi.mock('../../../services/contractAnalyzer', () => ({
  analyzeTokenomics: vi.fn(() => Promise.resolve({
    score: 80,
    data: { name: 'Test Token', symbol: 'TEST' },
    analysis: 'Healthy tokenomics',
    strengths: ['Fair distribution'],
    issues: [],
  })),
  analyzeContractRisk: vi.fn(() => Promise.resolve({
    score: 85,
    data: { name: 'Test Contract', verified: true },
    analysis: 'Secure contract',
    risks: [],
    safetyFeatures: ['Verified source code'],
  })),
}));

vi.mock('../../../services/socialAnalyzer', () => ({
  analyzeTwitter: vi.fn(() => Promise.resolve({
    score: 70,
    data: { followers: 1000 },
    analysis: 'Moderate Twitter presence',
  })),
  analyzeTelegram: vi.fn(() => Promise.resolve({
    score: 65,
    data: { members: 500 },
    analysis: 'Growing Telegram community',
  })),
  analyzeDiscord: vi.fn(() => Promise.resolve({
    score: 60,
    data: { members: 300 },
    analysis: 'Small Discord community',
  })),
}));

vi.mock('../../../_core/llm', () => ({
  invokeLLM: vi.fn(() => Promise.resolve({
    choices: [{ message: { content: 'AI-generated analysis summary' } }],
  })),
}));

describe('Projects API Integration Tests', () => {
  let db: Awaited<ReturnType<typeof getTestDb>>;
  let testUser: { id: number; email: string; name: string | null; role: string };

  beforeEach(async () => {
    db = await getTestDb();
    await resetTestDb();

    // Create a test user
    const [user] = await db.insert(users).values({
      openId: 'test-user-openid',
      email: 'projecttest@example.com',
      name: 'Project Test User',
      role: 'user',
    }).returning();

    testUser = user;
  });

  afterEach(async () => {
    vi.clearAllMocks();
  });

  describe('Project Creation', () => {
    it('should create a new project successfully', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.project.create({
        name: 'Test Project',
        description: 'A test project for integration testing',
        githubUrl: 'https://github.com/user/test-repo',
        contractAddress: '0x1234567890123456789012345678901234567890',
        chain: 'ethereum',
        websiteUrl: 'https://example.com',
        twitterUrl: 'https://twitter.com/testproject',
        telegramUrl: 'https://t.me/testproject',
        discordUrl: 'https://discord.gg/testproject',
      });

      expect(result).toBeDefined();
      expect(result.projectId).toBeDefined();

      // Verify project was created in database
      const [project] = await db.select().from(projects).where(eq(projects.id, Number(result.projectId)));
      expect(project).toBeDefined();
      expect(project.name).toBe('Test Project');
      expect(project.userId).toBe(testUser.id);
      expect(project.status).toBe('pending');
    });

    it('should require authentication for project creation', async () => {
      const caller = await createUnauthenticatedCaller();

      await expect(caller.project.create({
        name: 'Test Project',
        description: 'Should fail',
        githubUrl: 'https://github.com/user/test-repo',
      })).rejects.toThrow();
    });

    it('should reject project creation with invalid data', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      // Missing required field (name)
      await expect(caller.project.create({
        name: '',
        description: 'Project without name',
      })).rejects.toThrow();
    });

    it('should create project with only GitHub URL', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.project.create({
        name: 'GitHub Only Project',
        githubUrl: 'https://github.com/user/github-only',
      });

      expect(result.projectId).toBeDefined();

      const [project] = await db.select().from(projects).where(eq(projects.id, Number(result.projectId)));
      expect(project.githubUrl).toBe('https://github.com/user/github-only');
      expect(project.contractAddress).toBeNull();
    });

    it('should create project with only contract address', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.project.create({
        name: 'Contract Only Project',
        contractAddress: '0x1234567890abcdef1234567890abcdef12345678',
        chain: 'bsc',
      });

      expect(result.projectId).toBeDefined();

      const [project] = await db.select().from(projects).where(eq(projects.id, Number(result.projectId)));
      expect(project.contractAddress).toBe('0x1234567890abcdef1234567890abcdef12345678');
      expect(project.chain).toBe('bsc');
      expect(project.githubUrl).toBeNull();
    });
  });

  describe('Project Retrieval', () => {
    beforeEach(async () => {
      // Create test projects
      await db.insert(projects).values([
        {
          userId: testUser.id,
          name: 'Project 1',
          description: 'First test project',
          githubUrl: 'https://github.com/user/project1',
          status: 'completed',
        },
        {
          userId: testUser.id,
          name: 'Project 2',
          description: 'Second test project',
          contractAddress: '0x1234567890123456789012345678901234567890',
          chain: 'ethereum',
          status: 'analyzing',
        },
      ]);
    });

    it('should get user projects', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.project.list();

      expect(result).toBeDefined();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(2);
      expect(result[0].name).toBe('Project 1');
      expect(result[1].name).toBe('Project 2');
    });

    it('should get project by ID', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const [project] = await db.select().from(projects).where(eq(projects.name, 'Project 1'));

      const result = await caller.project.getById({ id: project.id });

      expect(result).toBeDefined();
      expect(result.name).toBe('Project 1');
      expect(result.description).toBe('First test project');
    });

    it('should return null for non-existent project', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const result = await caller.project.getById({ id: 99999 });

      expect(result).toBeNull();
    });

    it('should not allow access to other users projects', async () => {
      // Create another user
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      // Create a project owned by the first user
      const [project] = await db.select().from(projects).where(eq(projects.name, 'Project 1'));

      // Try to access with different user
      const caller = await createAuthenticatedCaller(otherUser);

      const result = await caller.project.getById({ id: project.id });

      // Should return null or throw error depending on implementation
      expect(result === null || result === undefined).toBe(true);
    });
  });

  describe('Project Analysis', () => {
    it('should analyze a project successfully', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      // Create a project
      const [project] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'To Analyze',
        githubUrl: 'https://github.com/user/to-analyze',
        contractAddress: '0x1234567890123456789012345678901234567890',
        chain: 'ethereum',
        status: 'pending',
      }).returning();

      // Analyze the project
      await caller.project.analyze({ projectId: project.id });

      // Check project status was updated
      const [updatedProject] = await db.select().from(projects).where(eq(projects.id, project.id));
      expect(updatedProject.status).toBe('completed');

      // Check audit report was created
      const [report] = await db.select().from(auditReports).where(eq(auditReports.projectId, project.id));
      expect(report).toBeDefined();
      expect(report.overallScore).toBeGreaterThan(0);
      expect(report.riskLevel).toBeDefined();
    });

    it('should handle analysis for project without GitHub URL', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const [project] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'Contract Only',
        contractAddress: '0x1234567890123456789012345678901234567890',
        chain: 'ethereum',
        status: 'pending',
      }).returning();

      // Should not throw error
      await caller.project.analyze({ projectId: project.id });

      const [updatedProject] = await db.select().from(projects).where(eq(projects.id, project.id));
      expect(updatedProject.status).toBe('completed');
    });

    it('should handle analysis for project without contract address', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const [project] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'GitHub Only',
        githubUrl: 'https://github.com/user/github-only',
        status: 'pending',
      }).returning();

      // Should not throw error
      await caller.project.analyze({ projectId: project.id });

      const [updatedProject] = await db.select().from(projects).where(eq(projects.id, project.id));
      expect(updatedProject.status).toBe('completed');
    });

    it('should handle analysis failures gracefully', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const [project] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'Will Fail',
        githubUrl: 'https://github.com/nonexistent/fake-repo-xyz123',
        contractAddress: '0xinvalid',
        status: 'pending',
      }).returning();

      // Should not throw error even if analysis fails
      await caller.project.analyze({ projectId: project.id });

      const [updatedProject] = await db.select().from(projects).where(eq(projects.id, project.id));
      // Status should be either completed (with partial results) or failed
      expect(['completed', 'failed']).toContain(updatedProject.status);
    });
  });

  describe('Project Update and Delete', () => {
    it('should update project status', async () => {
      const caller = await createAuthenticatedCaller(testUser);

      const [project] = await db.insert(projects).values({
        userId: testUser.id,
        name: 'To Update',
        githubUrl: 'https://github.com/user/to-update',
        status: 'pending',
      }).returning();

      // Update status
      await caller.project.updateStatus({
        projectId: project.id,
        status: 'analyzing',
      });

      const [updatedProject] = await db.select().from(projects).where(eq(projects.id, project.id));
      expect(updatedProject.status).toBe('analyzing');
    });
  });

  describe('Project Permissions', () => {
    it('should prevent users from accessing others projects via list', async () => {
      // Create another user with their own project
      const [otherUser] = await db.insert(users).values({
        openId: 'other-user-openid',
        email: 'other@example.com',
        name: 'Other User',
        role: 'user',
      }).returning();

      await db.insert(projects).values({
        userId: otherUser.id,
        name: 'Other User Project',
        status: 'completed',
      });

      // First user's list should only show their projects
      const caller = await createAuthenticatedCaller(testUser);
      const result = await caller.project.list();

      expect(result).toBeDefined();
      expect(result.length).toBe(0); // No projects for testUser
    });
  });
});
