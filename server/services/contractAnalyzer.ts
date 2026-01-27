import { invokeLLM } from "../_core/llm";
import { getCachedContractAnalysis, setCachedContractAnalysis } from "./analysisCache";

interface TokenomicsApiResponse {
  name: string;
  symbol: string;
  totalSupply: string;
  circulatingSupply: string;
  holders: number;
  transferCount: number;
  lastUpdated: string;
}

interface TokenomicsData {
  name?: string;
  symbol?: string;
  totalSupply?: string;
  circulatingSupply?: string;
  holders?: number;
  transferCount?: number;
  lastUpdated?: string;
}

interface ContractApiResponse {
  name: string;
  address: string;
  owner?: string;
  verified: boolean;
  sourceCode?: string;
  compilerVersion?: string;
  optimization?: boolean;
  runs?: number;
  constructorArguments?: string;
  libraries?: Record<string, string>;
  license?: string;
  issues: string[];
}

interface ContractRiskData {
  name?: string;
  address?: string;
  owner?: string;
  verified?: boolean;
  sourceCode?: string;
  compilerVersion?: string;
  optimization?: boolean;
  runs?: number;
  constructorArguments?: string;
  libraries?: Record<string, string>;
  license?: string;
  issues?: string[];
}

interface TokenomicsAnalysisResult {
  score: number;
  data: TokenomicsData;
  analysis: string;
  issues: string[];
  strengths: string[];
}

interface ContractRiskAnalysisResult {
  score: number;
  data: ContractRiskData;
  analysis: string;
  risks: string[];
  safetyFeatures: string[];
}

/**
 * Helper function to calculate circulating supply ratio
 */
function calculateCirculatingRatio(totalSupply: string, circulatingSupply: string): number {
  const total = BigInt(totalSupply);
  const circulating = BigInt(circulatingSupply);
  if (total === 0n) return 0;
  return Number((circulating * 100n) / total) / 100;
}

/**
 * Analyze Tokenomics by fetching data from blockchain explorers
 */
export async function analyzeTokenomics(
  contractAddress: string,
  chain: string = "ethereum"
): Promise<TokenomicsAnalysisResult> {
  // Check cache first
  const cached = await getCachedContractAnalysis(contractAddress, chain, 'tokenomics');
  if (cached) {
    return cached;
  }

  try {
    // Validate contract address
    if (!contractAddress || !/^0x[a-fA-F0-9]{40}$/.test(contractAddress)) {
      throw new Error("Invalid contract address");
    }

    // Determine API endpoint based on chain
    const apiBaseUrl = chain === "bsc"
      ? "https://api.bscscan.com/api"
      : "https://api.etherscan.io/api";

    // Fetch tokenomics data
    const response = await fetch(`${apiBaseUrl}?module=token&action=tokeninfo&contractaddress=${contractAddress}`);

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("Contract not found");
      }
      throw new Error(`API error: ${response.status}`);
    }

    const apiData = await response.json();

    if (apiData.status === "0" || !apiData.result || apiData.result.length === 0) {
      throw new Error("Contract not found");
    }

    const tokenInfo: any = Array.isArray(apiData.result) ? apiData.result[0] : apiData.result;

    const data: TokenomicsData = {
      name: tokenInfo.tokenName || tokenInfo.name,
      symbol: tokenInfo.symbol,
      totalSupply: tokenInfo.totalSupply,
      circulatingSupply: tokenInfo.totalSupply, // Etherscan doesn't provide circulating, using total as fallback
      holders: 0, // Would need additional API call
      transferCount: 0, // Would need additional API call
      lastUpdated: new Date().toISOString(),
    };

    // Calculate score
    let score = 50;

    // Holder distribution - would need holder count from additional API
    // For now, use reasonable defaults
    score += 15;

    // Circulation ratio
    const ratio = calculateCirculatingRatio(data.totalSupply || "0", data.circulatingSupply || "0");
    if (ratio >= 0.8) score += 15;
    else if (ratio >= 0.6) score += 10;
    else if (ratio >= 0.4) score += 5;
    else if (ratio < 0.2) score -= 15;

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

Name: ${data.name}
Symbol: ${data.symbol}
Total Supply: ${data.totalSupply}
Circulating Supply: ${data.circulatingSupply}
Circulation Ratio: ${(ratio * 100).toFixed(1)}%

Provide brief analysis covering:
1. Distribution health
2. Economic sustainability
3. Red flags or concerns`
        }
      ]
    });

    const aiAnalysis = typeof aiResponse.choices[0]?.message?.content === "string"
      ? aiResponse.choices[0].message.content
      : "AI analysis unavailable";

    // Extract issues and strengths
    const issues: string[] = [];
    const strengths: string[] = [];

    if (ratio < 0.5) {
      issues.push("Low circulation ratio - tokens may be locked");
    }
    if (ratio >= 0.7) {
      strengths.push("Good circulation ratio");
    }
    if (data.totalSupply && BigInt(data.totalSupply) > 0n) {
      strengths.push("Token has defined supply");
    }

    const result = {
      score,
      data,
      analysis: aiAnalysis,
      issues,
      strengths,
    };

    // Cache the result
    await setCachedContractAnalysis(contractAddress, chain, 'tokenomics', result);

    return result;
  } catch (error) {
    console.error("Error analyzing tokenomics:", error);
    throw error; // Re-throw to allow tests to catch specific errors
  }
}

/**
 * Analyze Contract Risk by fetching contract data from blockchain explorers
 */
export async function analyzeContractRisk(
  contractAddress: string,
  chain: string = "ethereum"
): Promise<ContractRiskAnalysisResult> {
  // Check cache first
  const cached = await getCachedContractAnalysis(contractAddress, chain, 'risk');
  if (cached) {
    return cached;
  }

  try {
    // Validate contract address
    if (!contractAddress || !/^0x[a-fA-F0-9]{40}$/.test(contractAddress)) {
      throw new Error("Invalid contract address");
    }

    // Determine API endpoint based on chain
    const scanUrl = chain === "bsc"
      ? "https://api.bscscan.com/api"
      : "https://api.etherscan.io/api";

    // Fetch contract source code
    const response = await fetch(
      `${scanUrl}?module=contract&action=getsourcecode&address=${contractAddress}`
    );

    if (!response.ok) {
      throw new Error(`Network error: ${response.status}`);
    }

    const apiData = await response.json();

    if (!apiData.result || apiData.result.length === 0) {
      throw new Error("Contract not found");
    }

    const contractData: any = Array.isArray(apiData.result) ? apiData.result[0] : apiData.result;

    const data: ContractRiskData = {
      name: contractData.ContractName || contractData.name || "",
      address: contractAddress,
      owner: contractData.owner,
      verified: (contractData.verified || contractData.SourceCode !== "") && !!contractData.SourceCode,
      sourceCode: contractData.SourceCode || contractData.sourceCode,
      compilerVersion: contractData.CompilerVersion || contractData.compilerVersion,
      optimization: contractData.OptimizationUsed === "1" || contractData.optimization,
      runs: parseInt(contractData.Runs) || contractData.runs,
      constructorArguments: contractData.ConstructorArguments || contractData.constructorArguments,
      libraries: contractData.Libraries || contractData.libraries,
      license: contractData.License || contractData.license,
      issues: contractData.issues || [],
    };

    // Calculate score
    let score = 100;

    if (!data.verified) {
      score -= 30;
    }

    // Check for old compiler version
    if (data.compilerVersion) {
      const versionMatch = data.compilerVersion.match(/0\.\d+\.\d+/);
      if (versionMatch) {
        const [major, minor] = versionMatch[0].split('.').map(Number);
        if (major < 0 || (major === 0 && minor < 8)) {
          score -= 20;
          (data.issues = data.issues || []).push("Old compiler version");
        }
      }
    }

    // Check for optimization
    if (data.optimization) {
      score += 5;
    }

    score = Math.max(0, Math.min(100, score));

    // Safety features
    const safetyFeatures: string[] = [];
    const risks: string[] = [];

    if (data.verified) {
      safetyFeatures.push("Verified source code");
    } else {
      risks.push("Unverified contract");
    }

    if (data.compilerVersion) {
      const versionMatch = data.compilerVersion.match(/0\.\d+\.\d+/);
      if (versionMatch) {
        const [major, minor] = versionMatch[0].split('.').map(Number);
        if (major > 0 || (major === 0 && minor >= 8)) {
          safetyFeatures.push("Modern compiler version");
        } else {
          risks.push("Old compiler version");
        }
      }
    }

    if (data.optimization) {
      safetyFeatures.push("Compiler optimization enabled");
    }

    if (data.issues && data.issues.length > 0) {
      data.issues.forEach(issue => {
        if (!risks.includes(issue)) risks.push(issue);
      });
    }

    // Check for potential vulnerabilities in source code
    if (data.sourceCode) {
      const code = data.sourceCode.toLowerCase();
      if (code.includes('tx.origin')) {
        risks.push("Potential tx.origin vulnerability");
        score -= 10;
      }
      if (code.includes('delegatecall') && !code.includes('protected')) {
        risks.push("Uses delegatecall - potential risk");
        score -= 5;
      }
      if (code.includes('suicide') || code.includes('selfdestruct')) {
        risks.push("Contains self-destruct function");
        score -= 15;
      }
    }

    score = Math.max(0, Math.min(100, score));

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

Name: ${data.name}
Address: ${data.address}
Verified: ${data.verified}
Compiler Version: ${data.compilerVersion}
Optimization: ${data.optimization}
License: ${data.license}

Detected Risks: ${risks.join(", ") || "None"}
Safety Features: ${safetyFeatures.join(", ") || "None"}

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

    const result = {
      score,
      data,
      analysis: aiAnalysis,
      risks,
      safetyFeatures,
    };

    // Cache the result
    await setCachedContractAnalysis(contractAddress, chain, 'risk', result);

    return result;
  } catch (error) {
    console.error("Error analyzing contract risk:", error);
    throw error; // Re-throw to allow tests to catch specific errors
  }
}
