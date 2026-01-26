/**
 * Trending Alerts Service
 * Monitors trending crypto projects and alerts users about significant changes
 */

interface TrendingProject {
  id: string;
  name: string;
  symbol: string;
  rank: number;
  priceChange24h: number;
  marketCap: number;
  volume24h: number;
  recommendationScore: number;
  status: string;
  category: string;
  price: number;
  briefSummary: string;
  description: string;
  tags: string[];
  website?: string;
  githubUrl?: string;
  twitterUrl?: string;
  telegramUrl?: string;
  contractAddress?: string;
  chain?: string;
}

interface AlertCondition {
  type: "new_entry" | "price_spike" | "volume_spike" | "score_dropped" | "score_increased";
  threshold?: number;
  message: string;
}

interface TrendingAlert {
  id: string;
  projectId: string;
  projectName: string;
  projectSymbol: string;
  type: AlertCondition["type"];
  message: string;
  severity: "info" | "warning" | "critical";
  data: any;
  timestamp: Date;
}

// In-memory cache for previous trending state
let previousTrendingState: Map<string, TrendingProject> = new Map();
let lastCheckTime: Date | null = null;

/**
 * Fetch current trending projects from the discovery service
 */
async function fetchTrendingProjects(): Promise<TrendingProject[]> {
  try {
    // In production, this would call the actual discovery service
    // For now, return empty array as this is a placeholder
    return [];
  } catch (error) {
    console.error("[TrendingAlerts] Failed to fetch trending projects:", error);
    return [];
  }
}

/**
 * Compare current trending state with previous state and generate alerts
 */
export async function checkForTrendingAlerts(): Promise<TrendingAlert[]> {
  const alerts: TrendingAlert[] = [];
  const currentProjects = await fetchTrendingProjects();
  const currentTime = new Date();

  // Skip if first run or less than 1 hour since last check
  if (previousTrendingState.size === 0) {
    previousTrendingState = new Map(currentProjects.map((p) => [p.id, p]));
    lastCheckTime = currentTime;
    return [];
  }

  const oneHourAgo = new Date(currentTime.getTime() - 60 * 60 * 1000);
  if (lastCheckTime && lastCheckTime > oneHourAgo) {
    return []; // Too soon to check again
  }

  // Check for new entries in trending
  for (const project of currentProjects) {
    const previousProject = previousTrendingState.get(project.id);

    if (!previousProject) {
      // New project entered trending
      alerts.push({
        id: `alert-${project.id}-${Date.now()}`,
        projectId: project.id,
        projectName: project.name,
        projectSymbol: project.symbol,
        type: "new_entry",
        message: `${project.name} (${project.symbol}) is now trending!`,
        severity: project.recommendationScore >= 70 ? "info" : "warning",
        data: {
          rank: project.rank,
          score: project.recommendationScore,
          priceChange24h: project.priceChange24h,
        },
        timestamp: currentTime,
      });
      continue;
    }

    // Check for significant price increase (>20% in 24h)
    if (project.priceChange24h > 20 && previousProject.priceChange24h <= 20) {
      alerts.push({
        id: `alert-price-${project.id}-${Date.now()}`,
        projectId: project.id,
        projectName: project.name,
        projectSymbol: project.symbol,
        type: "price_spike",
        message: `${project.name} price surged ${project.priceChange24h.toFixed(1)}% in 24h!`,
        severity: project.priceChange24h > 50 ? "critical" : "warning",
        data: {
          priceChange24h: project.priceChange24h,
          currentPrice: project.price,
        },
        timestamp: currentTime,
      });
    }

    // Check for score improvements (project improved significantly)
    const scoreIncrease = project.recommendationScore - previousProject.recommendationScore;
    if (scoreIncrease >= 10) {
      alerts.push({
        id: `alert-score-${project.id}-${Date.now()}`,
        projectId: project.id,
        projectName: project.name,
        projectSymbol: project.symbol,
        type: "score_increased",
        message: `${project.name} score improved by ${scoreIncrease} points!`,
        severity: "info",
        data: {
          previousScore: previousProject.recommendationScore,
          currentScore: project.recommendationScore,
          increase: scoreIncrease,
        },
        timestamp: currentTime,
      });
    }

    // Check for score drops (project degraded significantly)
    if (scoreIncrease <= -10) {
      alerts.push({
        id: `alert-score-drop-${project.id}-${Date.now()}`,
        projectId: project.id,
        projectName: project.name,
        projectSymbol: project.symbol,
        type: "score_dropped",
        message: `${project.name} score dropped by ${Math.abs(scoreIncrease)} points`,
        severity: scoreIncrease <= -20 ? "critical" : "warning",
        data: {
          previousScore: previousProject.recommendationScore,
          currentScore: project.recommendationScore,
          decrease: Math.abs(scoreIncrease),
        },
        timestamp: currentTime,
      });
    }
  }

  // Update state for next check
  previousTrendingState = new Map(currentProjects.map((p) => [p.id, p]));
  lastCheckTime = currentTime;

  return alerts;
}

/**
 * Get formatted alerts for display
 */
export function formatAlertForDisplay(alert: TrendingAlert): {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "critical";
  projectId: string;
  projectName: string;
  projectSymbol: string;
  timestamp: Date;
  data: any;
} {
  return {
    id: alert.id,
    title: getAlertTitle(alert.type),
    message: alert.message,
    type: alert.severity,
    projectId: alert.projectId,
    projectName: alert.projectName,
    projectSymbol: alert.projectSymbol,
    timestamp: alert.timestamp,
    data: alert.data,
  };
}

function getAlertTitle(type: AlertCondition["type"]): string {
  switch (type) {
    case "new_entry":
      return "🔥 New Trending Project";
    case "price_spike":
      return "📈 Price Surge Alert";
    case "volume_spike":
      return "💰 Volume Spike Alert";
    case "score_dropped":
      return "⚠️ Score Drop Alert";
    case "score_increased":
      return "✨ Score Improved";
    default:
      return "📊 Trending Alert";
  }
}

/**
 * Reset the trending state (useful for testing)
 */
export function resetTrendingState() {
  previousTrendingState.clear();
  lastCheckTime = null;
}

/**
 * Get current trending state size
 */
export function getTrendingStateSize(): number {
  return previousTrendingState.size;
}
