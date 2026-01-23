/**
 * Gemini AI Analyzer Service
 * Uses Google Gemini API for AI analysis (FREE or very low cost)
 * Replaces expensive OpenAI API
 */

import { GoogleGenerativeAI, GenerativeModel } from "@google/generative-ai";

// Types
export interface GeminiAnalysisResult {
  recommendation: "STRONG_BUY" | "BUY" | "HOLD" | "WAIT" | "AVOID";
  strengths: string[];
  risks: string[];
  entryPrice?: string;
  stopLoss?: string;
  takeProfit?: string;
  confidence: number;
  reasoning: string;
}

export interface TradingSignalResult {
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  reasoning: string;
}

class GeminiAnalyzer {
  private genAI: GoogleGenerativeAI | null = null;
  private model: GenerativeModel | null = null;
  private initialized = false;

  constructor() {
    this.initialize();
  }

  private initialize() {
    const apiKey = process.env.GEMINI_API_KEY;

    if (!apiKey) {
      console.warn("[Gemini] GEMINI_API_KEY not configured. AI analysis will be disabled.");
      return;
    }

    try {
      this.genAI = new GoogleGenerativeAI(apiKey);
      this.model = this.genAI.getGenerativeModel({ model: "gemini-2.0-flash-exp" });
      this.initialized = true;
      console.log("[Gemini] Initialized successfully");
    } catch (error) {
      console.error("[Gemini] Failed to initialize:", error);
    }
  }

  private ensureInitialized(): void {
    if (!this.initialized || !this.model) {
      throw new Error("Gemini API is not initialized. Set GEMINI_API_KEY environment variable.");
    }
  }

  /**
   * Analyze a crypto project based on audit scores
   */
  async analyzeProject(data: {
    name: string;
    symbol: string;
    description?: string;
    auditScores: {
      githubScore?: number | null;
      tokenomicsScore?: number | null;
      contractRiskScore?: number | null;
      socialScore?: number | null;
      overallScore: number;
      riskLevel: string;
    };
  }): Promise<GeminiAnalysisResult> {
    this.ensureInitialized();

    const { name, symbol, description, auditScores } = data;

    const prompt = `You are a cryptocurrency investment analyst. Analyze this project:

PROJECT: ${name}
Symbol: ${symbol}
Description: ${description || "N/A"}

AUDIT SCORES:
- GitHub Score: ${auditScores.githubScore || "N/A"}/100
- Tokenomics Score: ${auditScores.tokenomicsScore || "N/A"}/100
- Contract Risk Score: ${auditScores.contractRiskScore || "N/A"}/100
- Social Media Score: ${auditScores.socialScore || "N/A"}/100
- Overall Score: ${auditScores.overallScore}/100
- Risk Level: ${auditScores.riskLevel}

Provide your analysis in this exact JSON format:
{
  "recommendation": "STRONG_BUY" | "BUY" | "HOLD" | "WAIT" | "AVOID",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "entryPrice": "Suggested entry price (or null)",
  "stopLoss": "Stop loss percentage (e.g., '5%')",
  "takeProfit": "Take profit levels (e.g., '15%')",
  "confidence": 0-100,
  "reasoning": "Brief explanation of your analysis"
}

Be concise and actionable.`;

    try {
      const result = await this.model!.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      // Parse JSON from response (handle markdown code blocks)
      let jsonText = text.trim();
      if (jsonText.startsWith("```json")) {
        jsonText = jsonText.slice(7);
      }
      if (jsonText.startsWith("```")) {
        jsonText = jsonText.slice(3);
      }
      if (jsonText.endsWith("```")) {
        jsonText = jsonText.slice(0, -3);
      }
      jsonText = jsonText.trim();

      const analysis = JSON.parse(jsonText);

      return {
        recommendation: analysis.recommendation || "HOLD",
        strengths: analysis.strengths || [],
        risks: analysis.risks || [],
        entryPrice: analysis.entryPrice,
        stopLoss: analysis.stopLoss,
        takeProfit: analysis.takeProfit,
        confidence: analysis.confidence || 50,
        reasoning: analysis.reasoning || "",
      };
    } catch (error) {
      console.error("[Gemini] Analysis failed:", error);

      // Return fallback analysis
      return {
        recommendation: auditScores.overallScore >= 70 ? "BUY" : auditScores.overallScore >= 50 ? "HOLD" : "WAIT",
        strengths: ["Overall score: " + auditScores.overallScore],
        risks: ["AI analysis unavailable"],
        confidence: auditScores.overallScore,
        reasoning: "Based on overall audit score of " + auditScores.overallScore + "/100",
      };
    }
  }

  /**
   * Generate trading signal based on audit score and market data
   */
  async generateTradingSignal(data: {
    auditScore: number;
    riskLevel: string;
    marketData?: {
      price: number;
      change24h: number;
      volume?: number;
    };
    tradingViewSignal?: string;
  }): Promise<TradingSignalResult> {
    this.ensureInitialized();

    const { auditScore, riskLevel, marketData, tradingViewSignal } = data;

    let prompt = `Generate a trading signal based on:
- Audit Score: ${auditScore}/100
- Risk Level: ${riskLevel}`;

    if (marketData) {
      prompt += `
- Current Price: $${marketData.price}
- 24h Change: ${marketData.change24h}%
- Volume: ${marketData.volume || "N/A"}`;
    }

    if (tradingViewSignal) {
      prompt += `
- TradingView Signal: ${tradingViewSignal}`;
    }

    prompt += `

Provide your signal as JSON:
{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "reasoning": "Brief explanation"
}`;

    try {
      const result = await this.model!.generateContent(prompt);
      const response = await result.response;
      const text = response.text();

      // Parse JSON
      let jsonText = text.trim();
      if (jsonText.startsWith("```json")) {
        jsonText = jsonText.slice(7);
      }
      if (jsonText.startsWith("```")) {
        jsonText = jsonText.slice(3);
      }
      if (jsonText.endsWith("```")) {
        jsonText = jsonText.slice(0, -3);
      }
      jsonText = jsonText.trim();

      const signal = JSON.parse(jsonText);

      return {
        action: signal.action || "HOLD",
        confidence: signal.confidence || 50,
        reasoning: signal.reasoning || "",
      };
    } catch (error) {
      console.error("[Gemini] Signal generation failed:", error);

      // Fallback logic
      let action: "BUY" | "SELL" | "HOLD" = "HOLD";
      if (auditScore >= 70 && marketData?.change24h && marketData.change24h < -5) {
        action = "BUY";
      } else if (auditScore < 40) {
        action = "SELL";
      }

      return {
        action,
        confidence: auditScore,
        reasoning: "Fallback signal based on audit score",
      };
    }
  }

  /**
   * Generate comprehensive audit summary
   */
  async generateAuditSummary(data: {
    projectName: string;
    description?: string;
    scores: {
      github?: number | null;
      tokenomics?: number | null;
      contractRisk?: number | null;
      twitter?: number | null;
      telegram?: number | null;
      discord?: number | null;
    };
    overallScore: number;
    riskLevel: string;
  }): Promise<string> {
    this.ensureInitialized();

    const { projectName, description, scores, overallScore, riskLevel } = data;

    const prompt = `You are a comprehensive crypto project auditor. Provide a detailed final assessment based on all analysis results.

Project: ${projectName}
Description: ${description || "N/A"}

=== SCORES ===
GitHub Score: ${scores.github || "N/A"}/100
Tokenomics Score: ${scores.tokenomics || "N/A"}/100
Contract Risk Score: ${scores.contractRisk || "N/A"}/100
Twitter Score: ${scores.twitter || "N/A"}/100
Telegram Score: ${scores.telegram || "N/A"}/100
Discord Score: ${scores.discord || "N/A"}/100

Overall Score: ${overallScore}/100
Risk Level: ${riskLevel.toUpperCase()}

Provide:
1. Executive Summary (2-3 sentences)
2. Key Strengths (3-5 points)
3. Critical Concerns (3-5 points)
4. Investment Recommendation (STRONG BUY / BUY / HOLD / SELL / STRONG SELL)
5. Risk Assessment Summary

Be concise but thorough. Focus on actionable insights.`;

    try {
      const result = await this.model!.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error("[Gemini] Audit summary generation failed:", error);

      // Fallback summary
      return `AUDIT SUMMARY FOR ${projectName}

Overall Score: ${overallScore}/100
Risk Level: ${riskLevel.toUpperCase()}

Executive Summary:
This project has achieved an overall score of ${overallScore}/100, indicating ${overallScore >= 70 ? "strong" : (overallScore >= 50 ? "moderate" : "weak")} fundamentals.

Investment Recommendation: ${overallScore >= 80 ? "STRONG BUY" : overallScore >= 70 ? "BUY" : overallScore >= 50 ? "HOLD" : overallScore >= 40 ? "SELL" : "STRONG SELL"}

Key Strengths:
- Overall audit score of ${overallScore}/100
- Risk assessment: ${riskLevel}

Critical Concerns:
- AI-generated summary unavailable
- Manual review recommended

Risk Assessment Summary:
${riskLevel === "low" ? "This project presents a lower risk profile based on the audit scores." :
  riskLevel === "medium" ? "This project has moderate risk factors to consider." :
  riskLevel === "high" ? "This project carries significant risk factors." :
  "This project has critical risk issues - exercise extreme caution."}

Note: This summary was generated due to API unavailability. Full AI analysis is recommended.`;
    }
  }

  /**
   * Check if Gemini is properly configured
   */
  isConfigured(): boolean {
    return this.initialized;
  }

  /**
   * Get model info
   */
  getModelInfo(): { model: string; configured: boolean } {
    return {
      model: "gemini-2.0-flash-exp",
      configured: this.initialized,
    };
  }
}

// Export singleton instance
export const geminiAnalyzer = new GeminiAnalyzer();

/**
 * Update project analysis with Gemini AI
 * Can be called during the audit pipeline
 */
export async function analyzeProjectWithGemini(data: {
  projectId: number;
  name: string;
  symbol: string;
  description?: string;
  auditScores: {
    githubScore?: number | null;
    tokenomicsScore?: number | null;
    contractRiskScore?: number | null;
    socialScore?: number | null;
    overallScore: number;
    riskLevel: string;
  };
}): Promise<{
  recommendation: string;
  reasoning: string;
  confidence: number;
}> {
  try {
    const analysis = await geminiAnalyzer.analyzeProject(data);

    return {
      recommendation: analysis.recommendation,
      reasoning: analysis.reasoning,
      confidence: analysis.confidence,
    };
  } catch (error) {
    console.error("[Gemini] Project analysis failed:", error);
    throw error;
  }
}

/**
 * Generate combined signal with Gemini AI
 */
export async function generateGeminiSignal(data: {
  auditScore: number;
  riskLevel: string;
  marketData?: {
    price: number;
    change24h: number;
    volume?: number;
  };
  tradingViewSignal?: string;
}): Promise<{
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  reasoning: string;
}> {
  try {
    return await geminiAnalyzer.generateTradingSignal(data);
  } catch (error) {
    console.error("[Gemini] Signal generation failed:", error);
    throw error;
  }
}
