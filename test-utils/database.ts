import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import * as schema from '../drizzle/schema';
import { eq } from 'drizzle-orm';

let testDb: ReturnType<typeof drizzle> | null = null;
let testClient: postgres.Sql | null = null;

export async function getTestDb() {
  if (!testDb) {
    const connectionString = process.env.TEST_DATABASE_URL || 
      'postgresql://test_user:test_password@localhost:5432/investment_auditor_test';
    
    try {
      testClient = postgres(connectionString);
      testDb = drizzle(testClient, { schema });
      
      // Run migrations if needed
      await migrate(testDb, { migrationsFolder: './drizzle' });
    } catch (error) {
      console.error('[Test Database] Failed to initialize:', error);
      throw error;
    }
  }
  
  return testDb;
}

export async function resetTestDb() {
  const db = await getTestDb();
  if (!db) return;
  
  try {
    // Delete all data in correct order (respect foreign keys)
    await db.delete(schema.unicornCandidates);
    await db.delete(schema.unicornScans);
    await db.delete(schema.auditReports);
    await db.delete(schema.projects);
    await db.delete(schema.users);
  } catch (error) {
    console.error('[Test Database] Failed to reset:', error);
    throw error;
  }
}

export async function seedTestDb() {
  const db = await getTestDb();
  if (!db) throw new Error('Test database not available');
  
  try {
    // Create test users
    const [testUser] = await db.insert(schema.users).values({
      openId: 'test-open-id',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user',
    }).returning();
    
    const [adminUser] = await db.insert(schema.users).values({
      openId: 'admin-open-id',
      email: 'admin@example.com',
      name: 'Admin User',
      role: 'admin',
    }).returning();
    
    // Create test projects
    const [testProject] = await db.insert(schema.projects).values({
      userId: testUser.id,
      name: 'Test Project',
      description: 'A test project for auditing',
      githubUrl: 'https://github.com/user/test-repo',
      contractAddress: '0x1234567890123456789012345678901234567890',
      chain: 'ethereum',
      websiteUrl: 'https://example.com',
      twitterUrl: 'https://twitter.com/testproject',
      telegramUrl: 'https://t.me/testproject',
      discordUrl: 'https://discord.gg/testproject',
      status: 'pending',
    }).returning();
    
    // Create test audit report
    const [testReport] = await db.insert(schema.auditReports).values({
      projectId: testProject.id,
      githubScore: 75,
      tokenomicsScore: 80,
      contractRiskScore: 85,
      twitterScore: 70,
      telegramScore: 65,
      discordScore: 60,
      overallScore: 72,
      riskLevel: 'medium',
      githubData: JSON.stringify({ test: 'data' }),
      tokenomicsData: JSON.stringify({ test: 'data' }),
      contractRiskData: JSON.stringify({ test: 'data' }),
      twitterData: JSON.stringify({ test: 'data' }),
      telegramData: JSON.stringify({ test: 'data' }),
      discordData: JSON.stringify({ test: 'data' }),
      aiAnalysis: 'This is a test AI analysis of the project.',
    }).returning();
    
    return { 
      testUser, 
      adminUser, 
      testProject, 
      testReport,
      db 
    };
  } catch (error) {
    console.error('[Test Database] Failed to seed:', error);
    throw error;
  }
}

export async function closeTestDb() {
  if (testClient) {
    await testClient.end();
    testClient = null;
    testDb = null;
  }
}

// Helper function to create a mock user session
export function createMockUser(overrides: Partial<typeof schema.users.$inferInsert> = {}) {
  return {
    id: 1,
    openId: 'test-open-id',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user' as const,
    ...overrides,
  };
}

// Helper function to create a mock project
export function createMockProject(overrides: Partial<typeof schema.projects.$inferInsert> = {}) {
  return {
    id: 1,
    userId: 1,
    name: 'Test Project',
    description: 'A test project',
    githubUrl: 'https://github.com/user/test-repo',
    status: 'pending' as const,
    ...overrides,
  };
}

// Helper function to create a mock audit report
export function createMockAuditReport(overrides: Partial<typeof schema.auditReports.$inferInsert> = {}) {
  return {
    id: 1,
    projectId: 1,
    overallScore: 75,
    riskLevel: 'medium' as const,
    ...overrides,
  };
}