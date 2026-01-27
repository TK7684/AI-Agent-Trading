/**
 * Database helper functions สำหรับฟีเจอร์ขั้นสูง
 * - Watchlist management
 * - Comparison management
 * - Alert settings
 */

import { eq, and } from "drizzle-orm";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { watchlist, comparisons, alertSettings, projects } from '@drizzle/schema';

let _db: ReturnType<typeof drizzle> | null = null;
let _client: postgres.Sql | null = null;

async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _client = postgres(process.env.DATABASE_URL, {
        onnotice: () => {}, // Ignore notices
      });
      _db = drizzle(_client);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

// ============ WATCHLIST FUNCTIONS ============

export async function addToWatchlist(userId: number, projectId: number, notes?: string) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.insert(watchlist).values({
    userId,
    projectId,
    notes,
  });
}

export async function removeFromWatchlist(userId: number, projectId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.delete(watchlist).where(
    and(eq(watchlist.userId, userId), eq(watchlist.projectId, projectId))
  );
}

export async function getUserWatchlist(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db
    .select({
      id: watchlist.id,
      projectId: watchlist.projectId,
      projectName: projects.name,
      projectSymbol: projects.description,
      addedAt: watchlist.addedAt,
      notes: watchlist.notes,
      alertPrice: watchlist.alertPrice,
      alertScore: watchlist.alertScore,
    })
    .from(watchlist)
    .innerJoin(projects, eq(watchlist.projectId, projects.id))
    .where(eq(watchlist.userId, userId));

  return result;
}

export async function updateWatchlistNote(watchlistId: number, notes: string) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(watchlist).set({ notes }).where(eq(watchlist.id, watchlistId));
}

export async function isInWatchlist(userId: number, projectId: number): Promise<boolean> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db
    .select({ id: watchlist.id })
    .from(watchlist)
    .where(and(eq(watchlist.userId, userId), eq(watchlist.projectId, projectId)))
    .limit(1);

  return result.length > 0;
}

// ============ COMPARISON FUNCTIONS ============

export async function createComparison(userId: number, name: string, projectIds: number[]) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(comparisons).values({
    userId,
    name,
    projectIds: JSON.stringify(projectIds),
  });

  return result;
}

export async function getUserComparisons(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.select().from(comparisons).where(eq(comparisons.userId, userId));

  return result.map(comp => ({
    ...comp,
    projectIds: JSON.parse(comp.projectIds) as number[],
  }));
}

export async function getComparison(comparisonId: number, userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db
    .select()
    .from(comparisons)
    .where(and(eq(comparisons.id, comparisonId), eq(comparisons.userId, userId)))
    .limit(1);

  if (result.length === 0) return null;

  return {
    ...result[0],
    projectIds: JSON.parse(result[0].projectIds) as number[],
  };
}

export async function updateComparison(comparisonId: number, name: string, projectIds: number[]) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db
    .update(comparisons)
    .set({
      name,
      projectIds: JSON.stringify(projectIds),
      updatedAt: new Date(),
    })
    .where(eq(comparisons.id, comparisonId));
}

export async function deleteComparison(comparisonId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.delete(comparisons).where(eq(comparisons.id, comparisonId));
}

// ============ ALERT SETTINGS FUNCTIONS ============

export async function createAlertSetting(
  userId: number,
  projectId: number,
  priceChangePercent?: number,
  scoreChangePoints?: number
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.insert(alertSettings).values({
    userId,
    projectId,
    priceChangePercent,
    scoreChangePoints,
    enabled: 1,
  });
}

export async function getUserAlertSettings(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db
    .select()
    .from(alertSettings)
    .where(and(eq(alertSettings.userId, userId), eq(alertSettings.enabled, 1)));

  return result;
}

export async function updateAlertSetting(
  alertId: number,
  priceChangePercent?: number,
  scoreChangePoints?: number
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const updateData: any = {};
  if (priceChangePercent !== undefined) updateData.priceChangePercent = priceChangePercent;
  if (scoreChangePoints !== undefined) updateData.scoreChangePoints = scoreChangePoints;

  await db.update(alertSettings).set(updateData).where(eq(alertSettings.id, alertId));
}

export async function disableAlertSetting(alertId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  await db.update(alertSettings).set({ enabled: 0 }).where(eq(alertSettings.id, alertId));
}
