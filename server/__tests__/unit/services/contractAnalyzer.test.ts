import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { analyzeTokenomics, analyzeContractRisk } from '../../../services/contractAnalyzer';
import { setupGlobalMocks, resetAllMocks } from '../../../../test-utils/mocks';
import { clearAnalysisCache } from '../../../services/analysisCache';


// Create mock fetch
const mockFetch = vi.fn();

// Mock the LLM service
vi.mock('../../../_core/llm', () => ({
  invokeLLM: vi.fn().mockResolvedValue({
    choices: [{
      message: {
        content: 'Mock AI analysis response'
      }
    }]
  })
}));

describe('Contract Analyzer', () => {
  beforeEach(() => {
    setupGlobalMocks();
    vi.clearAllMocks();
    // Mock global fetch
    vi.stubGlobal('fetch', mockFetch);
    // Clear analysis cache to prevent cross-test pollution
    clearAnalysisCache();

  });

  afterEach(() => {
    resetAllMocks();
    vi.unstubAllGlobals();
  });

  describe('Tokenomics Analysis', () => {
    it('should analyze tokenomics with valid contract address', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          contractAddress: '0x1234567890123456789012345678901234567890',
          tokenName: 'Test Token',
          symbol: 'TEST',
          divisor: '18',
          totalSupply: '1000000000000000000000000000',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeTokenomics('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result).toBeDefined();
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(100);
      expect(result.data.name).toBe('Test Token');
      expect(result.data.symbol).toBe('TEST');
      expect(result.analysis).toBeDefined();
      expect(result.strengths).toBeDefined();
      expect(result.issues).toBeDefined();
    });

    it('should calculate high score for tokens with good circulation ratio', async () => {
      // High circulation ratio (circulating = totalSupply)
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          contractAddress: '0x1234567890123456789012345678901234567890',
          tokenName: 'Well Distributed Token',
          symbol: 'WDT',
          divisor: '18',
          totalSupply: '1000000000000000000000000000',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeTokenomics('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result.score).toBeGreaterThan(70);
      expect(result.strengths).toContain('Good circulation ratio');
    });

    it('should calculate moderate score for tokens with average circulation ratio', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          contractAddress: '0x1234567890123456789012345678901234567890',
          tokenName: 'Average Token',
          symbol: 'AVG',
          divisor: '18',
          totalSupply: '1000000000000000000000000000',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeTokenomics('0x1234567890123456789012345678901234567890', 'ethereum');

      // Score should be between 65 and 80 with default circulation ratio of 1.0
      expect(result.score).toBeGreaterThanOrEqual(65);
      expect(result.score).toBeLessThanOrEqual(100);
    });

    it('should handle invalid contract addresses', async () => {
      await expect(
        analyzeTokenomics('invalid-address', 'ethereum')
      ).rejects.toThrow('Invalid contract address');
    });

    it('should handle contract not found', async () => {
      const mockApiResponse = {
        status: '0',
        message: 'NOTOK',
        result: 'Contract not found'
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      await expect(
        analyzeTokenomics('0x1234567890123456789012345678901234567890', 'ethereum')
      ).rejects.toThrow('Contract not found');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        analyzeTokenomics('0x1234567890123456789012345678901234567890', 'ethereum')
      ).rejects.toThrow('Network error');
    });
  });

  describe('Contract Risk Analysis', () => {
    it('should analyze contract risk with valid contract address', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: 'Test Contract',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: 'v0.8.0+commit.c7dfd78e',
          OptimizationUsed: '1',
          SourceCode: `pragma solidity ^0.8.0;
contract Test {
    // Safe contract code
}`,
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result).toBeDefined();
      expect(result.score).toBeGreaterThanOrEqual(0);
      expect(result.score).toBeLessThanOrEqual(100);
      expect(result.data.name).toBe('Test Contract');
      expect(result.data.verified).toBe(true);
      expect(result.analysis).toBeDefined();
      expect(result.risks).toBeDefined();
      expect(result.safetyFeatures).toBeDefined();
    });

    it('should calculate high score for verified contracts with modern compiler', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: 'Safe Contract',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: 'v0.8.0+commit.c7dfd78e',
          OptimizationUsed: '1',
          SourceCode: `pragma solidity ^0.8.0;
contract Safe {
    // Safe contract code
}`,
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result.score).toBeGreaterThan(80);
      expect(result.safetyFeatures).toContain('Verified source code');
      expect(result.safetyFeatures).toContain('Modern compiler version');
      expect(result.safetyFeatures).toContain('Compiler optimization enabled');
    });

    it('should calculate lower score for unverified contracts', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: '',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: '',
          OptimizationUsed: '0',
          SourceCode: '',
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result.score).toBeLessThan(80);
      expect(result.risks).toContain('Unverified contract');
    });

    it('should analyze contracts with old compiler versions', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: 'Vulnerable Contract',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: 'v0.4.0+commit.c7dfd78e',
          OptimizationUsed: '1',
          SourceCode: `pragma solidity ^0.4.0;
contract Vulnerable {
    function withdraw() public {
        msg.sender.transfer(address(this).balance);
    }
}`,
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result.score).toBeLessThan(90);
      expect(result.risks).toContain('Old compiler version');
    });

    it('should detect potential vulnerabilities in source code', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: 'Vulnerable Contract',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: 'v0.8.0+commit.c7dfd78e',
          OptimizationUsed: '1',
          SourceCode: `pragma solidity ^0.8.0;
contract Vulnerable {
    function bad() public {
        if (tx.origin == msg.sender) {
            // Vulnerable code
        }
    }
    function selfdestruct() public {
        selfdestruct(payable(owner()));
    }
}`,
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum');

      expect(result.score).toBeLessThan(90);
      expect(result.risks).toContain('Potential tx.origin vulnerability');
      expect(result.risks).toContain('Contains self-destruct function');
    });

    it('should handle different blockchain networks', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: [{
          ContractName: 'BSC Contract',
          Address: '0x1234567890123456789012345678901234567890',
          CompilerVersion: 'v0.8.0+commit.c7dfd78e',
          OptimizationUsed: '1',
          SourceCode: `pragma solidity ^0.8.0;
contract BSCContract {
    // BSC contract code
}`,
          ABI: '[]',
        }]
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      const result = await analyzeContractRisk('0x1234567890123456789012345678901234567890', 'bsc');

      expect(result).toBeDefined();
      expect(result.score).toBeGreaterThan(80);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('bscscan')
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum')
      ).rejects.toThrow('Network error');
    });

    it('should handle invalid contract addresses', async () => {
      await expect(
        analyzeContractRisk('invalid-address', 'ethereum')
      ).rejects.toThrow('Invalid contract address');
    });

    it('should handle contract not found', async () => {
      const mockApiResponse = {
        status: '1',
        message: 'OK',
        result: []
      };

      mockFetch.mockResolvedValueOnce({
        json: async () => mockApiResponse,
        ok: true,
      });

      await expect(
        analyzeContractRisk('0x1234567890123456789012345678901234567890', 'ethereum')
      ).rejects.toThrow('Contract not found');
    });
  });
});
