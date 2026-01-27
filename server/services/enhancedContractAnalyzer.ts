/**
 * Enhanced Contract Analyzer
 * Integrates Etherscan, BscScan, and GoPlus Security APIs
 * for comprehensive contract risk analysis
 */

import { goPlusSecurityService, SecurityAnalysis } from './goPlusSecurity';
import { analyzeTokenomics as baseAnalyzeTokenomics, analyzeContractRisk as baseAnalyzeContractRisk } from './contractAnalyzer';

interface EnhancedTokenomicsResult {
  score: number;
  data: any;
  analysis: string;
  issues: string[];
  strengths: string[];
  goPlusSecurity?: SecurityAnalysis;
}

interface EnhancedContractRiskResult {
  score: number;
  data: any;
  analysis: string;
  risks: string[];
  safetyFeatures: string[];
  goPlusSecurity?: SecurityAnalysis;
  honeypotDetected: boolean;
  overallRiskLevel: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * Enhanced tokenomics analysis with GoPlus Security integration
 */
export async function analyzeTokenomicsEnhanced(
  contractAddress: string,
  chain: string = 'ethereum'
): Promise<EnhancedTokenomicsResult> {
  try {
    // Run base analysis and GoPlus security check in parallel
    const [baseResult, goPlusData] = await Promise.allSettled([
      baseAnalyzeTokenomics(contractAddress, chain),
      goPlusSecurityService.getTokenSecurity(
        contractAddress,
        goPlusSecurityService.chainNameToId(chain)
      ),
    ]);

    const result = baseResult.status === 'fulfilled' ? baseResult.value : null;
    const security = goPlusData.status === 'fulfilled' ? goPlusData.value : undefined;

    if (!result) {
      throw new Error('Failed to analyze tokenomics');
    }

    // Enhance with GoPlus data
    if (security) {
      // Add GoPlus warnings to issues
      if (security.warnings.length > 0) {
        result.issues.push(...security.warnings);
      }

      // Add GoPlus recommendations to strengths
      if (security.recommendations.length > 0) {
        result.strengths.push(...security.recommendations);
      }

      // Adjust score based on GoPlus risk score
      if (security.riskScore < 50) {
        result.score = Math.max(0, result.score - 20);
      }

      result.goPlusSecurity = security;
    }

    return result;
  } catch (error) {
    console.error('[EnhancedAnalyzer] Error in tokenomics analysis:', error);
    throw error;
  }
}

/**
 * Enhanced contract risk analysis with GoPlus Security integration
 */
export async function analyzeContractRiskEnhanced(
  contractAddress: string,
  chain: string = 'ethereum'
): Promise<EnhancedContractRiskResult> {
  try {
    // Run base analysis and GoPlus security check in parallel
    const [baseResult, goPlusData] = await Promise.allSettled([
      baseAnalyzeContractRisk(contractAddress, chain),
      goPlusSecurityService.getTokenSecurity(
        contractAddress,
        goPlusSecurityService.chainNameToId(chain)
      ),
    ]);

    const result = baseResult.status === 'fulfilled' ? baseResult.value : null;
    const security = goPlusData.status === 'fulfilled' ? goPlusData.value : undefined;

    if (!result) {
      throw new Error('Failed to analyze contract risk');
    }

    const honeypotDetected = security?.isHoneypot || false;

    // Enhance with GoPlus data
    if (security) {
      // Add GoPlus warnings to risks
      if (security.warnings.length > 0) {
        result.risks.push(...security.warnings);
      }

      // Add GoPlus safety features
      if (security.recommendations.length > 0) {
        result.safetyFeatures.push(...security.recommendations);
      }

      // Adjust score based on GoPlus risk score and honeypot detection
      if (honeypotDetected) {
        result.score = 0; // Honeypot = zero safety
      } else {
        // Blend the scores - GoPlus is more weight for security
        result.score = Math.round((result.score * 0.6) + (security.riskScore * 0.4));
      }
    }

    // Determine overall risk level
    let overallRiskLevel: 'low' | 'medium' | 'high' | 'critical';

    if (honeypotDetected || result.score < 25) {
      overallRiskLevel = 'critical';
    } else if (security?.riskLevel === 'critical') {
      overallRiskLevel = 'critical';
    } else if (result.score >= 75 && security?.riskLevel !== 'high') {
      overallRiskLevel = 'low';
    } else if (result.score >= 50) {
      overallRiskLevel = 'medium';
    } else {
      overallRiskLevel = 'high';
    }

    return {
      ...result,
      goPlusSecurity: security,
      honeypotDetected,
      overallRiskLevel,
    };
  } catch (error) {
    console.error('[EnhancedAnalyzer] Error in contract risk analysis:', error);
    throw error;
  }
}

/**
 * Batch analyze multiple contracts
 * More efficient for analyzing multiple tokens
 */
export async function batchAnalyzeContracts(
  contracts: Array<{ address: string; chain: string }>
): Promise<Map<string, EnhancedContractRiskResult>> {
  const results = new Map<string, string>();

  // Group by chain
  const byChain = new Map<string, string[]>();
  for (const contract of contracts) {
    const chainId = goPlusSecurityService.chainNameToId(contract.chain);
    if (!byChain.has(chainId)) {
      byChain.set(chainId, []);
    }
    byChain.get(chainId)!.push(contract.address);
  }

  // Get GoPlus batch security data for each chain
  const securityData = new Map<string, SecurityAnalysis>();

  for (const [chainId, addresses] of byChain) {
    const batchResults = await goPlusSecurityService.getBatchTokenSecurity(
      addresses,
      chainId
    );

    for (const [address, security] of batchResults) {
      securityData.set(address.toLowerCase(), security);
    }
  }

  // Now analyze each contract individually (could be optimized further)
  for (const contract of contracts) {
    const security = securityData.get(contract.address.toLowerCase());

    if (security) {
      try {
        const result = await analyzeContractRiskEnhanced(
          contract.address,
          contract.chain
        );
        results.set(contract.address, JSON.stringify(result));
      } catch (error) {
        console.error(`[EnhancedAnalyzer] Error analyzing ${contract.address}:`, error);
      }
    }
  }

  // Parse back to results
  const finalResults = new Map<string, EnhancedContractRiskResult>();
  for (const [address, data] of results) {
    finalResults.set(address, JSON.parse(data));
  }

  return finalResults;
}

/**
 * Quick honeypot check for a contract
 * Returns immediately if honeypot is detected
 */
export async function quickHoneypotCheck(
  contractAddress: string,
  chain: string = 'ethereum'
): Promise<{
  isHoneypot: boolean;
  confidence: number;
  riskScore: number;
  details?: SecurityAnalysis;
}> {
  try {
    const security = await goPlusSecurityService.getTokenSecurity(
      contractAddress,
      goPlusSecurityService.chainNameToId(chain)
    );

    if (!security) {
      return {
        isHoneypot: false,
        confidence: 0,
        riskScore: 50,
      };
    }

    return {
      isHoneypot: security.isHoneypot,
      confidence: security.confidence,
      riskScore: security.riskScore,
      details: security,
    };
  } catch (error) {
    console.error('[EnhancedAnalyzer] Error in honeypot check:', error);
    return {
      isHoneypot: false,
      confidence: 0,
      riskScore: 50,
    };
  }
}

/**
 * Get security report for a token
 * Combines all security APIs for comprehensive report
 */
export async function getSecurityReport(
  contractAddress: string,
  chain: string = 'ethereum'
): Promise<{
  overall: {
    riskLevel: 'low' | 'medium' | 'high' | 'critical';
    riskScore: number;
    honeypotDetected: boolean;
    recommendation: string;
  };
  goPlusSecurity?: SecurityAnalysis;
  contractRisk?: EnhancedContractRiskResult;
  tokenomics?: EnhancedTokenomicsResult;
}> {
  const [goPlusData, contractRisk, tokenomics] = await Promise.allSettled([
    goPlusSecurityService.getTokenSecurity(
      contractAddress,
      goPlusSecurityService.chainNameToId(chain)
    ),
    analyzeContractRiskEnhanced(contractAddress, chain),
    analyzeTokenomicsEnhanced(contractAddress, chain),
  ]);

  const security = goPlusData.status === 'fulfilled' ? goPlusData.value : undefined;
  const risk = contractRisk.status === 'fulfilled' ? contractRisk.value : undefined;
  const tok = tokenomics.status === 'fulfilled' ? tokenomics.value : undefined;

  // Calculate overall risk
  let riskLevel: 'low' | 'medium' | 'high' | 'critical';
  let recommendation = '';

  if (security?.isHoneypot || risk?.honeypotDetected) {
    riskLevel = 'critical';
    recommendation = 'CRITICAL: Honeypot detected! Do not trade this token.';
  } else if (security?.riskLevel === 'critical' || risk?.overallRiskLevel === 'critical') {
    riskLevel = 'critical';
    recommendation = 'CRITICAL: Severe security risks detected. Exercise extreme caution.';
  } else if (security?.riskLevel === 'high' || risk?.overallRiskLevel === 'high') {
    riskLevel = 'high';
    recommendation = 'HIGH RISK: Multiple security concerns detected. Not recommended for trading.';
  } else if (security?.riskLevel === 'medium' || risk?.overallRiskLevel === 'medium') {
    riskLevel = 'medium';
    recommendation = 'MEDIUM RISK: Some security concerns. Proceed with caution and DYOR.';
  } else {
    riskLevel = 'low';
    recommendation = 'LOW RISK: Token passes security checks. Still DYOR before trading.';
  }

  // Calculate combined risk score
  const scores = [
    security?.riskScore,
    risk?.score,
    tok?.score,
  ].filter((s): s is number => s !== undefined);

  const riskScore = scores.length > 0
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : 50;

  return {
    overall: {
      riskLevel,
      riskScore,
      honeypotDetected: security?.isHoneypot || risk?.honeypotDetected || false,
      recommendation,
    },
    goPlusSecurity: security,
    contractRisk: risk,
    tokenomics: tok,
  };
}
