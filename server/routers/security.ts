/**
 * Security API Router
 * Exposes enhanced contract analysis endpoints
 * Integrates Etherscan, BscScan, and GoPlus Security APIs
 */

import { z } from 'zod';
import { publicProcedure, router, protectedProcedure } from '../_core/trpc';
import {
  analyzeTokenomicsEnhanced,
  analyzeContractRiskEnhanced,
  quickHoneypotCheck,
  getSecurityReport,
  batchAnalyzeContracts,
} from '../services/enhancedContractAnalyzer';
import { goPlusSecurityService } from '../services/goPlusSecurity';

export const securityRouter = router({
  // Quick honeypot check - fastest security check
  honeypotCheck: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      return quickHoneypotCheck(input.contractAddress, input.chain);
    }),

  // Enhanced tokenomics analysis with GoPlus integration
  tokenomicsEnhanced: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      return analyzeTokenomicsEnhanced(input.contractAddress, input.chain);
    }),

  // Enhanced contract risk analysis with GoPlus integration
  contractRiskEnhanced: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      return analyzeContractRiskEnhanced(input.contractAddress, input.chain);
    }),

  // Comprehensive security report combining all APIs
  securityReport: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      return getSecurityReport(input.contractAddress, input.chain);
    }),

  // Batch analyze multiple contracts
  batchAnalyze: publicProcedure
    .input(z.object({
      contracts: z.array(z.object({
        address: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
        chain: z.string().optional().default('ethereum'),
      })).min(1).max(20), // Limit to 20 contracts per request
    }))
    .query(async ({ input }) => {
      const results = await batchAnalyzeContracts(input.contracts);

      // Convert Map to array for JSON serialization
      return {
        results: Array.from(results.entries()).map(([address, data]) => ({
          address,
          ...data,
        })),
      };
    }),

  // Get supported chains
  supportedChains: publicProcedure.query(() => {
    return {
      chains: goPlusSecurityService.getSupportedChains(),
    };
  }),

  // Raw GoPlus Security API data
  goPlusSecurity: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      const chainId = goPlusSecurityService.chainNameToId(input.chain);
      return goPlusSecurityService.getTokenSecurity(input.contractAddress, chainId);
    }),

  // Approve security check - check if it's safe to approve a token
  approveCheck: publicProcedure
    .input(z.object({
      contractAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      const chainId = goPlusSecurityService.chainNameToId(input.chain);
      return goPlusSecurityService.getApproveSecurity(input.contractAddress, chainId);
    }),

  // Batch honeypot check for watchlist
  batchHoneypotCheck: protectedProcedure
    .input(z.object({
      addresses: z.array(z.string().regex(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address'))
        .min(1).max(50),
      chain: z.string().optional().default('ethereum'),
    }))
    .query(async ({ input }) => {
      const chainId = goPlusSecurityService.chainNameToId(input.chain);

      // Get batch security data
      const results = await goPlusSecurityService.getBatchTokenSecurity(
        input.addresses,
        chainId
      );

      // Return simplified results
      return Array.from(results.entries()).map(([address, data]) => ({
        address,
        isHoneypot: data.isHoneypot,
        riskScore: data.riskScore,
        riskLevel: data.riskLevel,
        warnings: data.warnings,
      }));
    }),
});
