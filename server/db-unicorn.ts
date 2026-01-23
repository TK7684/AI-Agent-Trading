/**
 * Database operations for Unicorn Hunter scans and candidates
 */

import { getDb } from "./db";
import { unicornScans, unicornCandidates } from "../drizzle/schema";
import { eq, desc } from "drizzle-orm";

/**
 * Create a new unicorn scan record
 */
export async function createUnicornScan(data: {
  userId: number;
  scanType: string;
}): Promise<number> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(unicornScans).values({
    userId: data.userId,
    scanType: data.scanType,
    status: "pending",
  });

  // Return the inserted ID
  const scan = await db
    .select()
    .from(unicornScans)
    .where(eq(unicornScans.userId, data.userId))
    .orderBy(desc(unicornScans.createdAt))
    .limit(1);

  return scan[0]?.id || 0;
}

/**
 * Update scan status
 */
export async function updateScanStatus(
  scanId: number,
  status: "pending" | "running" | "completed" | "failed",
  candidatesFound?: number
): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const updateData: any = { status };

  if (status === "completed") {
    updateData.completedAt = new Date();
  }

  if (candidatesFound !== undefined) {
    updateData.candidatesFound = candidatesFound;
  }

  await db.update(unicornScans).set(updateData).where(eq(unicornScans.id, scanId));
}

/**
 * Get scan by ID
 */
export async function getScanById(scanId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const scan = await db
    .select()
    .from(unicornScans)
    .where(eq(unicornScans.id, scanId))
    .limit(1);

  return scan[0] || null;
}

/**
 * Get all scans for a user
 */
export async function getScansByUserId(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return await db
    .select()
    .from(unicornScans)
    .where(eq(unicornScans.userId, userId))
    .orderBy(desc(unicornScans.createdAt));
}

/**
 * Save candidates for a scan
 */
export async function saveCandidates(scanId: number, candidates: any[]): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  // Clear existing candidates for this scan
  await db.delete(unicornCandidates).where(eq(unicornCandidates.scanId, scanId));

  // Insert new candidates
  for (const candidate of candidates) {
    // Calculate overall unicorn score
    const unicornScore = calculateUnicornScore(candidate);

    await db.insert(unicornCandidates).values({
      scanId,
      symbol: candidate.symbol || "",
      name: candidate.name || "",

      // Scanner metrics
      marketCap: candidate.market_cap || 0,
      priceFromAth: candidate.price_from_ath || 0,
      volumeSpike: candidate.volume_spike || 0,
      currentPrice: String(candidate.current_price || candidate.entry_price || ""),

      // Researcher metrics
      githubScore: candidate.github_score || 0,
      techScore: candidate.tech_score || 0,
      socialScore: candidate.social_score || 0,
      teamActive: candidate.team_active || 0,

      // Sniper metrics
      rsiDivergence: candidate.rsi_divergence || 0,
      wyckoffSpring: candidate.wyckoff_spring || 0,
      entryPrice: String(candidate.entry_price || ""),
      stopLoss: String(candidate.stop_loss || ""),
      takeProfit: String(candidate.take_profit || ""),

      // Final scores
      scannerScore: candidate.scanner_score || 0,
      fundamentalScore: candidate.fundamental_score || 0,
      technicalScore: candidate.technical_score || 0,
      unicornScore,
      recommendation: candidate.recommendation || "WAIT",

      analysis: JSON.stringify(candidate),
    });
  }
}

/**
 * Get candidates for a scan
 */
export async function getCandidatesByScanId(scanId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  return await db
    .select()
    .from(unicornCandidates)
    .where(eq(unicornCandidates.scanId, scanId))
    .orderBy(desc(unicornCandidates.unicornScore));
}

/**
 * Calculate overall unicorn score
 */
function calculateUnicornScore(candidate: any): number {
  const scannerScore = candidate.scanner_score || 0;
  const fundamentalScore = candidate.fundamental_score || 0;
  const technicalScore = candidate.technical_score || 0;

  // Weighted average: Scanner 30%, Fundamental 40%, Technical 30%
  return Math.round(
    scannerScore * 0.3 + fundamentalScore * 0.4 + technicalScore * 0.3
  );
}

/**
 * Get latest scan for a user
 */
export async function getLatestScan(userId: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const scans = await db
    .select()
    .from(unicornScans)
    .where(eq(unicornScans.userId, userId))
    .orderBy(desc(unicornScans.createdAt))
    .limit(1);

  return scans[0] || null;
}

/**
 * Delete a scan and its candidates
 */
export async function deleteScan(scanId: number): Promise<void> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  // Delete candidates first (foreign key)
  await db.delete(unicornCandidates).where(eq(unicornCandidates.scanId, scanId));

  // Delete scan
  await db.delete(unicornScans).where(eq(unicornScans.id, scanId));
}
