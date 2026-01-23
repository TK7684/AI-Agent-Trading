/**
 * Unicorn Hunter Service
 * Integrates with the Python CrewAI microservice for finding high-potential crypto assets
 */

import { ENV } from "../_core/env";

const UNICORN_HUNTER_API_URL = ENV.unicornHunterApiUrl || "http://localhost:8000";

/**
 * Start a new unicorn hunt scan
 */
export async function startUnicornScan(params: {
  scanType: "crypto" | "stocks" | "all";
  minMarketCap?: number;
  maxMarketCap?: number;
  minPriceDrop?: number;
  minVolumeSpike?: number;
}): Promise<{ scanId: string; status: string }> {
  try {
    const response = await fetch(`${UNICORN_HUNTER_API_URL}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        scan_type: params.scanType,
        min_market_cap: params.minMarketCap || 10000000,
        max_market_cap: params.maxMarketCap || 100000000,
        min_price_drop: params.minPriceDrop || 80,
        min_volume_spike: params.minVolumeSpike || 300,
      }),
    });

    if (!response.ok) {
      throw new Error(`Unicorn Hunter API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return {
      scanId: data.scan_id,
      status: data.status,
    };
  } catch (error) {
    console.error("Failed to start unicorn scan:", error);
    throw new Error("Failed to start unicorn scan. Is the Python service running?");
  }
}

/**
 * Get the status of a running scan
 */
export async function getScanStatus(scanId: string): Promise<{
  scanId: string;
  status: string;
  message: string;
}> {
  try {
    const response = await fetch(`${UNICORN_HUNTER_API_URL}/status/${scanId}`);

    if (!response.ok) {
      throw new Error(`Unicorn Hunter API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to get scan status:", error);
    throw new Error("Failed to get scan status");
  }
}

/**
 * Get the results of a completed scan
 */
export async function getScanResults(scanId: string): Promise<{
  scanId: string;
  status: string;
  candidates: any[];
  summary: {
    total_scanned: number;
    candidates_found: number;
    scan_type: string;
  };
}> {
  try {
    const response = await fetch(`${UNICORN_HUNTER_API_URL}/results/${scanId}`);

    if (!response.ok) {
      throw new Error(`Unicorn Hunter API error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to get scan results:", error);
    throw new Error("Failed to get scan results");
  }
}

/**
 * Poll for scan completion
 */
export async function pollScanCompletion(
  scanId: string,
  maxAttempts: number = 60,
  intervalMs: number = 5000
): Promise<{ success: boolean; candidates?: any[]; error?: string }> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const status = await getScanStatus(scanId);

      if (status.status === "completed") {
        const results = await getScanResults(scanId);
        return {
          success: true,
          candidates: results.candidates,
        };
      }

      if (status.status === "failed") {
        return {
          success: false,
          error: status.message || "Scan failed",
        };
      }

      // Still running, wait and retry
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    } catch (error) {
      console.error(`Poll attempt ${i + 1} failed:`, error);
      if (i === maxAttempts - 1) {
        throw error;
      }
    }
  }

  return {
    success: false,
    error: "Scan timed out",
  };
}

/**
 * Health check for the Unicorn Hunter service
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${UNICORN_HUNTER_API_URL}/health`, {
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Process scan results and save to database
 */
export async function processAndSaveScanResults(
  scanId: string,
  dbScanId: number
): Promise<void> {
  const results = await getScanResults(scanId);

  // Import here to avoid circular dependency
  const { saveCandidates, updateScanStatus } = await import("../db-unicorn");

  // Save candidates to database
  await saveCandidates(dbScanId, results.candidates);

  // Update scan status
  await updateScanStatus(dbScanId, "completed", results.candidates.length);
}
