/**
 * GoPlus Security API Service
 * Provides real-time security analysis for crypto tokens
 * including honeypot detection, contract risks, and more
 * FREE API with generous rate limits
 */

interface TokenSecurityResponse {
  [address: string]: {
    token_name: string;
    token_symbol: string;
    token_type: string;
    contract_address: string;
    holder_count: number;
    token_price: string;
    lp_holder_count: number;
    lp_total_supply: string;
    owner_address: string;
    creator_address: string;
    creator_balance: string;
    creator_percent: number;
    transfer_tax: number;
    buy_tax: number;
    sell_tax: number;
    buy_count: number;
    sell_count: number;
    transfer_count: number;
    last_trade_time: number;
    is_honeypot: boolean;
    is_anti_honeypot: boolean;
    is_in_blacklist: boolean;
    is_open_source: boolean;
    is_proxy: boolean;
    is_whitelisted: boolean;
    can_take_back_ownership: boolean;
    hidden_owner: boolean;
    is_honeypot_confirmed: boolean;
    is_trustable: boolean;
    is_mintable: boolean;
    is_proxy_with_implementation: boolean;
    slippage_modifiable: boolean;
    transfer_tax_modifiable: boolean;
    buy_tax_modifiable: boolean;
    sell_tax_modifiable: boolean;
    is_token_deprecated: boolean;
    is_blacklisted_token: boolean;
    personal_slippage_recommend: string;
    owner_proportion: number;
    owner_balance: number;
    confidence: number;
    risk_level: string;
    risk_score: number;
  };
}

interface ApproveSecurityResponse {
  [address: string]: {
    seal_status: boolean;
    allowance: number;
    token_symbol: string;
    token_name: string;
    contract_address: string;
    risk_description: string;
    risk_details: string[];
  };
}

interface SecurityAnalysis {
  address: string;
  chain: string;
  isHoneypot: boolean;
  riskScore: number; // 0-100
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  details: {
    tokenName?: string;
    tokenSymbol?: string;
    buyTax: number;
    sellTax: number;
    transferTax: number;
    holderCount: number;
    ownerAddress?: string;
    ownerPercent: number;
    isOpenSource: boolean;
    isMintable: boolean;
    canTakeBackOwnership: boolean;
    isBlacklisted: boolean;
    slippageModifiable: boolean;
    taxModifiable: boolean;
    isDeprecated: boolean;
  };
  warnings: string[];
  recommendations: string[];
}

class GoPlusSecurityService {
  private baseUrl = 'https://api.gopluslabs.io/api/v1';

  /**
   * Get token security information
   * FREE endpoint - no API key required
   */
  async getTokenSecurity(
    address: string,
    chainId: string = '1' // 1 = ETH, 56 = BSC, etc.
  ): Promise<SecurityAnalysis | null> {
    try {
      const url = `${this.baseUrl}/token_security/${chainId}?contract_addresses=${address}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });

      if (!response.ok) {
        console.error(`[GoPlus] API error: ${response.status}`);
        return null;
      }

      const data: TokenSecurityResponse = await response.json();
      const tokenData = data[address.toLowerCase()];

      if (!tokenData) {
        console.warn(`[GoPlus] No data found for ${address}`);
        return null;
      }

      return this.parseTokenSecurity(address, chainId, tokenData);
    } catch (error) {
      console.error('[GoPlus] Error fetching token security:', error);
      return null;
    }
  }

  /**
   * Get approve security information
   * Checks if approval is safe for a token
   */
  async getApproveSecurity(
    address: string,
    chainId: string = '1'
  ): Promise<ApproveSecurityResponse | null> {
    try {
      const url = `${this.baseUrl}/approve_security/${chainId}?contract_addresses=${address}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        signal: AbortSignal.timeout(10000),
      });

      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error('[GoPlus] Error fetching approve security:', error);
      return null;
    }
  }

  /**
   * Get security info for multiple tokens at once
   * More efficient than individual calls
   */
  async getBatchTokenSecurity(
    addresses: string[],
    chainId: string = '1'
  ): Promise<Map<string, SecurityAnalysis>> {
    const results = new Map<string, SecurityAnalysis>();

    // GoPlus supports up to 20 addresses per request
    const batchSize = 20;
    for (let i = 0; i < addresses.length; i += batchSize) {
      const batch = addresses.slice(i, i + batchSize);
      const addressStr = batch.join(',');

      try {
        const url = `${this.baseUrl}/token_security/${chainId}?contract_addresses=${addressStr}`;

        const response = await fetch(url, {
          method: 'GET',
          signal: AbortSignal.timeout(15000),
        });

        if (response.ok) {
          const data: TokenSecurityResponse = await response.json();

          for (const [addr, tokenData] of Object.entries(data)) {
            results.set(
              addr.toLowerCase(),
              this.parseTokenSecurity(addr, chainId, tokenData)
            );
          }
        }
      } catch (error) {
        console.error('[GoPlus] Batch request error:', error);
      }

      // Small delay between batches to avoid rate limiting
      if (i + batchSize < addresses.length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    return results;
  }

  /**
   * Parse token security data into our format
   */
  private parseTokenSecurity(
    address: string,
    chainId: string,
    data: TokenSecurityResponse[string]
  ): SecurityAnalysis {
    const warnings: string[] = [];
    const recommendations: string[] = [];

    // Honeypot detection
    if (data.is_honeypot || data.is_honeypot_confirmed) {
      warnings.push('HONEYPOT DETECTED - Do not trade this token!');
      recommendations.push('Immediately avoid trading this token');
    }

    // Tax analysis
    if (data.buy_tax > 10 || data.sell_tax > 10) {
      warnings.push(`High tax detected: Buy ${data.buy_tax}% / Sell ${data.sell_tax}%`);
      recommendations.push('Be cautious of high transaction fees');
    }

    if (data.transfer_tax > 5) {
      warnings.push(`High transfer tax: ${data.transfer_tax}%`);
    }

    // Ownership risks
    if (data.owner_percent > 10) {
      warnings.push(`High owner concentration: ${data.owner_percent.toFixed(2)}%`);
      recommendations.push('Owner holds significant supply - potential dump risk');
    }

    if (data.can_take_back_ownership) {
      warnings.push('Owner can take back ownership after renouncing');
    }

    if (data.hidden_owner) {
      warnings.push('Hidden owner detected');
    }

    // Mintable tokens
    if (data.is_mintable) {
      warnings.push('Token is mintable - unlimited supply possible');
      recommendations.push('Risk of inflation through unlimited minting');
    }

    // Modifiable taxes
    if (data.slippage_modifiable || data.taxModifiable) {
      warnings.push('Taxes can be modified by owner');
    }

    // Blacklist
    if (data.is_blacklisted || data.is_in_blacklist || data.is_blacklisted_token) {
      warnings.push('Token is blacklisted');
    }

    // Deprecated
    if (data.is_token_deprecated) {
      warnings.push('Token is deprecated');
    }

    // Source code
    if (!data.is_open_source) {
      warnings.push('Source code is not verified');
      recommendations.push('Unverified contracts pose higher security risks');
    }

    // Positive indicators
    if (data.is_trustable) {
      recommendations.push('Token passes trust checks');
    }

    if (data.is_anti_honeypot) {
      recommendations.push('Anti-honeypot mechanisms detected');
    }

    if (data.is_whitelisted) {
      recommendations.push('Token is whitelisted on platform');
    }

    // Calculate risk score
    let riskScore = 100;

    if (data.is_honeypot || data.is_honeypot_confirmed) riskScore = 0;
    else if (data.is_blacklisted || data.is_in_blacklist) riskScore -= 40;
    else if (data.is_token_deprecated) riskScore -= 30;

    if (data.buy_tax > 15 || data.sell_tax > 15) riskScore -= 20;
    else if (data.buy_tax > 10 || data.sell_tax > 10) riskScore -= 10;

    if (data.is_mintable) riskScore -= 15;
    if (!data.is_open_source) riskScore -= 10;
    if (data.can_take_back_ownership) riskScore -= 10;
    if (data.hidden_owner) riskScore -= 10;
    if (data.owner_percent > 20) riskScore -= 10;
    else if (data.owner_percent > 10) riskScore -= 5;

    if (data.slippage_modifiable || data.taxModifiable) riskScore -= 5;

    riskScore = Math.max(0, Math.min(100, riskScore));

    // Determine risk level
    let riskLevel: 'low' | 'medium' | 'high' | 'critical';
    if (data.is_honeypot || data.is_honeypot_confirmed) {
      riskLevel = 'critical';
    } else if (riskScore >= 75) {
      riskLevel = 'low';
    } else if (riskScore >= 50) {
      riskLevel = 'medium';
    } else if (riskScore >= 25) {
      riskLevel = 'high';
    } else {
      riskLevel = 'critical';
    }

    return {
      address,
      chain: chainId,
      isHoneypot: data.is_honeypot || data.is_honeypot_confirmed,
      riskScore,
      riskLevel,
      confidence: data.confidence || 0,
      details: {
        tokenName: data.token_name,
        tokenSymbol: data.token_symbol,
        buyTax: data.buy_tax,
        sellTax: data.sell_tax,
        transferTax: data.transfer_tax,
        holderCount: data.holder_count,
        ownerAddress: data.owner_address,
        ownerPercent: data.owner_percent,
        isOpenSource: data.is_open_source,
        isMintable: data.is_mintable,
        canTakeBackOwnership: data.can_take_back_ownership,
        isBlacklisted: data.is_blacklisted || data.is_in_blacklist || data.is_blacklisted_token,
        slippageModifiable: data.slippage_modifiable,
        taxModifiable: data.transfer_tax_modifiable || data.buy_tax_modifiable || data.sell_tax_modifiable,
        isDeprecated: data.is_token_deprecated,
      },
      warnings,
      recommendations,
    };
  }

  /**
   * Convert chain name to GoPlus chain ID
   */
  chainNameToId(chain: string): string {
    const chainMap: Record<string, string> = {
      'ethereum': '1',
      'eth': '1',
      'bsc': '56',
      'binance-smart-chain': '56',
      'polygon': '137',
      'matic': '137',
      'arbitrum': '42161',
      'arb': '42161',
      'optimism': '10',
      'op': '10',
      'fantom': '250',
      'ftm': '250',
      'avalanche': '43114',
      'avax': '43114',
      'moonbeam': '1284',
      'glmr': '1284',
      'cronos': '25',
      'cro': '25',
    };

    return chainMap[chain.toLowerCase()] || '1';
  }

  /**
   * Get supported chains
   */
  getSupportedChains(): string[] {
    return [
      'ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism',
      'fantom', 'avalanche', 'moonbeam', 'cronos',
    ];
  }
}

// Export singleton instance
export const goPlusSecurityService = new GoPlusSecurityService();
export type { SecurityAnalysis, TokenSecurityResponse, ApproveSecurityResponse };
