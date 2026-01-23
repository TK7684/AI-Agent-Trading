import { invokeLLM } from "../_core/llm";

interface TokenomicsData {
  totalSupply?: string;
  circulatingSupply?: string;
  holders?: number;
  topHoldersPercentage?: number;
  liquidityLocked?: boolean;
  mintable?: boolean;
  burnable?: boolean;
  pausable?: boolean;
  hasProxy?: boolean;
  hasOwner?: boolean;
  renounced?: boolean;
}

interface ContractRiskData {
  isVerified: boolean;
  hasHoneypot: boolean;
  hasMaliciousFunctions: boolean;
  hasHiddenOwner: boolean;
  hasBlacklist: boolean;
  hasWhitelist: boolean;
  hasTradingCooldown: boolean;
  hasHighFees: boolean;
  cannotSellAll: boolean;
  risks: string[];
  warnings: string[];
}

interface TokenomicsAnalysisResult {
  score: number; // 0-100
  data: TokenomicsData;
  analysis: string;
  issues: string[];
  strengths: string[];
}

interface ContractRiskAnalysisResult {
  score: number; // 0-100
  data: ContractRiskData;
  analysis: string;
  risks: string[];
  safetyFeatures: string[];
}

/**
 * วิเคราะห์ Tokenomics โดยใช้ข้อมูลจาก blockchain explorers
 * (ในระบบจริงควรใช้ API เช่น Etherscan, BscScan, หรือ Moralis)
 */
export async function analyzeTokenomics(
  contractAddress: string,
  chain: string = "ethereum"
): Promise<TokenomicsAnalysisResult> {
  try {
    // Mock data - ในระบบจริงควรเรียก API จริง
    const mockData: TokenomicsData = {
      totalSupply: "1000000000",
      circulatingSupply: "750000000",
      holders: 5420,
      topHoldersPercentage: 35,
      liquidityLocked: true,
      mintable: false,
      burnable: true,
      pausable: false,
      hasProxy: false,
      hasOwner: true,
      renounced: false,
    };

    // คำนวณคะแนน
    let score = 50; // เริ่มต้นที่ 50

    // Holder distribution (max 25 points)
    if (mockData.holders && mockData.holders >= 10000) score += 25;
    else if (mockData.holders && mockData.holders >= 5000) score += 20;
    else if (mockData.holders && mockData.holders >= 1000) score += 15;
    else if (mockData.holders && mockData.holders >= 500) score += 10;
    else score -= 10; // Too few holders

    // Top holders concentration (max 20 points)
    if (mockData.topHoldersPercentage) {
      if (mockData.topHoldersPercentage <= 20) score += 20;
      else if (mockData.topHoldersPercentage <= 30) score += 15;
      else if (mockData.topHoldersPercentage <= 40) score += 10;
      else if (mockData.topHoldersPercentage <= 50) score += 5;
      else score -= 15; // Too concentrated
    }

    // Liquidity locked (15 points)
    if (mockData.liquidityLocked) score += 15;
    else score -= 20;

    // Mintable (negative if true)
    if (mockData.mintable) score -= 10;
    else score += 5;

    // Pausable (negative if true)
    if (mockData.pausable) score -= 10;

    // Owner renounced (positive)
    if (mockData.renounced) score += 10;
    else if (mockData.hasOwner) score -= 5;

    score = Math.max(0, Math.min(100, score));

    // AI Analysis
    const aiResponse = await invokeLLM({
      messages: [
        {
          role: "system",
          content: "You are a crypto tokenomics analyst. Analyze token distribution and economics for potential risks and opportunities."
        },
        {
          role: "user",
          content: `Analyze this token's economics:

Total Supply: ${mockData.totalSupply}
Circulating Supply: ${mockData.circulatingSupply}
Holders: ${mockData.holders}
Top Holders Own: ${mockData.topHoldersPercentage}%
Liquidity Locked: ${mockData.liquidityLocked}
Mintable: ${mockData.mintable}
Burnable: ${mockData.burnable}
Pausable: ${mockData.pausable}
Has Owner: ${mockData.hasOwner}
Owner Renounced: ${mockData.renounced}

Provide brief analysis covering:
1. Distribution health
2. Centralization risks
3. Economic sustainability
4. Red flags or concerns`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    // Extract issues and strengths
    const issues: string[] = [];
    const strengths: string[] = [];

    if (!mockData.liquidityLocked) issues.push("Liquidity not locked - rug pull risk");
    if (mockData.mintable) issues.push("Token is mintable - inflation risk");
    if (mockData.pausable) issues.push("Contract is pausable - trading can be halted");
    if (mockData.topHoldersPercentage && mockData.topHoldersPercentage > 50) {
      issues.push("High concentration - top holders control majority");
    }
    if (mockData.hasOwner && !mockData.renounced) {
      issues.push("Owner has not renounced - centralization risk");
    }
    if (mockData.holders && mockData.holders < 100) {
      issues.push("Very few holders - low adoption");
    }

    if (mockData.liquidityLocked) strengths.push("Liquidity is locked");
    if (!mockData.mintable) strengths.push("Cannot mint new tokens");
    if (mockData.burnable) strengths.push("Deflationary mechanism (burnable)");
    if (mockData.renounced) strengths.push("Ownership renounced - decentralized");
    if (mockData.holders && mockData.holders >= 1000) strengths.push("Good holder distribution");

    return {
      score,
      data: mockData,
      analysis: aiAnalysis,
      issues,
      strengths,
    };
  } catch (error) {
    console.error("Error analyzing tokenomics:", error);
    return {
      score: 0,
      data: {},
      analysis: "Unable to analyze tokenomics. Please check contract address and chain.",
      issues: ["Analysis failed"],
      strengths: [],
    };
  }
}

/**
 * วิเคราะห์ Contract Risk โดยตรวจสอบ smart contract code
 * (ในระบบจริงควรใช้ API เช่น GoPlus Security API, Honeypot.is)
 */
export async function analyzeContractRisk(
  contractAddress: string,
  chain: string = "ethereum"
): Promise<ContractRiskAnalysisResult> {
  try {
    // Mock data - ในระบบจริงควรเรียก Security API
    const mockData: ContractRiskData = {
      isVerified: true,
      hasHoneypot: false,
      hasMaliciousFunctions: false,
      hasHiddenOwner: false,
      hasBlacklist: false,
      hasWhitelist: false,
      hasTradingCooldown: false,
      hasHighFees: false,
      cannotSellAll: false,
      risks: [],
      warnings: [],
    };

    // คำนวณคะแนน
    let score = 100; // เริ่มต้นที่ 100 แล้วลบตาม risk

    if (!mockData.isVerified) {
      score -= 30;
      mockData.risks.push("Contract not verified");
    }

    if (mockData.hasHoneypot) {
      score -= 50;
      mockData.risks.push("HONEYPOT DETECTED - Cannot sell tokens!");
    }

    if (mockData.hasMaliciousFunctions) {
      score -= 40;
      mockData.risks.push("Malicious functions detected");
    }

    if (mockData.hasHiddenOwner) {
      score -= 25;
      mockData.risks.push("Hidden owner functions");
    }

    if (mockData.hasBlacklist) {
      score -= 20;
      mockData.warnings.push("Has blacklist function");
    }

    if (mockData.hasWhitelist) {
      score -= 15;
      mockData.warnings.push("Has whitelist function");
    }

    if (mockData.hasTradingCooldown) {
      score -= 10;
      mockData.warnings.push("Trading cooldown enabled");
    }

    if (mockData.hasHighFees) {
      score -= 15;
      mockData.risks.push("High transaction fees (>10%)");
    }

    if (mockData.cannotSellAll) {
      score -= 30;
      mockData.risks.push("Cannot sell all tokens at once");
    }

    score = Math.max(0, Math.min(100, score));

    // Safety features
    const safetyFeatures: string[] = [];
    if (mockData.isVerified) safetyFeatures.push("Contract is verified");
    if (!mockData.hasHoneypot) safetyFeatures.push("No honeypot detected");
    if (!mockData.hasMaliciousFunctions) safetyFeatures.push("No malicious functions");
    if (!mockData.hasHighFees) safetyFeatures.push("Reasonable transaction fees");

    // AI Analysis
    const aiResponse = await invokeLLM({
      messages: [
        {
          role: "system",
          content: "You are a smart contract security expert. Analyze contract risks and provide security assessment."
        },
        {
          role: "user",
          content: `Analyze this smart contract security:

Verified: ${mockData.isVerified}
Honeypot: ${mockData.hasHoneypot}
Malicious Functions: ${mockData.hasMaliciousFunctions}
Hidden Owner: ${mockData.hasHiddenOwner}
Has Blacklist: ${mockData.hasBlacklist}
Has Whitelist: ${mockData.hasWhitelist}
Trading Cooldown: ${mockData.hasTradingCooldown}
High Fees: ${mockData.hasHighFees}
Cannot Sell All: ${mockData.cannotSellAll}

Detected Risks: ${mockData.risks.join(", ") || "None"}
Warnings: ${mockData.warnings.join(", ") || "None"}

Provide brief security assessment covering:
1. Critical vulnerabilities
2. Trust assumptions
3. Trading risks
4. Overall safety rating`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    return {
      score,
      data: mockData,
      analysis: aiAnalysis,
      risks: mockData.risks,
      safetyFeatures,
    };
  } catch (error) {
    console.error("Error analyzing contract risk:", error);
    return {
      score: 0,
      data: {
        isVerified: false,
        hasHoneypot: false,
        hasMaliciousFunctions: false,
        hasHiddenOwner: false,
        hasBlacklist: false,
        hasWhitelist: false,
        hasTradingCooldown: false,
        hasHighFees: false,
        cannotSellAll: false,
        risks: ["Analysis failed"],
        warnings: [],
      },
      analysis: "Unable to analyze contract risk. Please check contract address and chain.",
      risks: ["Analysis failed"],
      safetyFeatures: [],
    };
  }
}
