/**
 * Unit Tests for GoPlus Security Service
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { goPlusSecurityService } from '../../server/services/goPlusSecurity';

// Mock fetch globally
global.fetch = vi.fn();

describe('GoPlus Security Service', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('chainNameToId', () => {
    it('should map ethereum to 1', () => {
      expect(goPlusSecurityService.chainNameToId('ethereum')).toBe('1');
      expect(goPlusSecurityService.chainNameToId('eth')).toBe('1');
    });

    it('should map bsc to 56', () => {
      expect(goPlusSecurityService.chainNameToId('bsc')).toBe('56');
      expect(goPlusSecurityService.chainNameToId('binance-smart-chain')).toBe('56');
    });

    it('should map polygon to 137', () => {
      expect(goPlusSecurityService.chainNameToId('polygon')).toBe('137');
      expect(goPlusSecurityService.chainNameToId('matic')).toBe('137');
    });

    it('should default to ethereum (1) for unknown chains', () => {
      expect(goPlusSecurityService.chainNameToId('unknown')).toBe('1');
    });
  });

  describe('getSupportedChains', () => {
    it('should return array of supported chain names', () => {
      const chains = goPlusSecurityService.getSupportedChains();
      expect(Array.isArray(chains)).toBe(true);
      expect(chains.length).toBeGreaterThan(0);
      expect(chains).toContain('ethereum');
      expect(chains).toContain('bsc');
      expect(chains).toContain('polygon');
    });
  });

  describe('getTokenSecurity', () => {
    const mockAddress = '0x1234567890abcdef1234567890abcdef12345678';

    it('should fetch token security data', async () => {
      const mockResponse = {
        [mockAddress.toLowerCase()]: {
          token_name: 'Test Token',
          token_symbol: 'TEST',
          token_type: 'ERC20',
          contract_address: mockAddress,
          holder_count: 1000,
          token_price: '1',
          lp_holder_count: 10,
          lp_total_supply: '1000',
          owner_address: '0xowner',
          creator_address: '0xcreator',
          creator_balance: '20',
          creator_percent: 2,
          transfer_tax: 0,
          buy_tax: 5,
          sell_tax: 5,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: false,
          is_anti_honeypot: true,
          is_in_blacklist: false,
          is_open_source: true,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: false,
          is_trustable: true,
          is_mintable: false,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '1',
          owner_proportion: 2,
          owner_balance: 2,
          confidence: 85,
          risk_level: 'low',
          risk_score: 85,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getTokenSecurity(mockAddress, '1');

      expect(result).toBeDefined();
      expect(result?.address).toBe(mockAddress);
      expect(result?.isHoneypot).toBe(false);
      expect(result?.riskScore).toBeGreaterThan(0);
    });

    it('should handle honeypot detection', async () => {
      const mockResponse = {
        [mockAddress.toLowerCase()]: {
          token_name: 'Bad Token',
          token_symbol: 'BAD',
          token_type: 'ERC20',
          contract_address: mockAddress,
          holder_count: 1000,
          token_price: '0',
          lp_holder_count: 10,
          lp_total_supply: '0',
          owner_address: '0xowner',
          creator_address: '0xcreator',
          creator_balance: '0',
          creator_percent: 50,
          transfer_tax: 99,
          buy_tax: 99,
          sell_tax: 99,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: true,
          is_anti_honeypot: false,
          is_in_blacklist: false,
          is_open_source: true,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: true,
          is_trustable: false,
          is_mintable: false,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '0',
          owner_proportion: 50,
          owner_balance: 50,
          confidence: 90,
          risk_level: 'critical',
          risk_score: 0,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getTokenSecurity(mockAddress, '1');

      expect(result?.isHoneypot).toBe(true);
      expect(result?.riskLevel).toBe('critical');
      expect(result?.riskScore).toBe(0);
    });

    it('should return null on fetch error', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const result = await goPlusSecurityService.getTokenSecurity(mockAddress, '1');

      expect(result).toBeNull();
    });

    it('should return null when contract not found', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const result = await goPlusSecurityService.getTokenSecurity(mockAddress, '1');

      expect(result).toBeNull();
    });
  });

  describe('getBatchTokenSecurity', () => {
    it('should fetch security for multiple tokens', async () => {
      const addresses = [
        '0x1234567890abcdef1234567890abcdef12345678',
        '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
      ];

      const mockResponse = {
        [addresses[0].toLowerCase()]: {
          token_name: 'Token 1',
          token_symbol: 'TOK1',
          token_type: 'ERC20',
          contract_address: addresses[0],
          holder_count: 1000,
          token_price: '1',
          lp_holder_count: 10,
          lp_total_supply: '1000',
          owner_address: '0xowner1',
          creator_address: '0xcreator1',
          creator_balance: '100',
          creator_percent: 5,
          transfer_tax: 0,
          buy_tax: 5,
          sell_tax: 5,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: false,
          is_anti_honeypot: true,
          is_in_blacklist: false,
          is_open_source: true,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: false,
          is_trustable: true,
          is_mintable: false,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '1',
          owner_proportion: 5,
          owner_balance: 5,
          confidence: 85,
          risk_level: 'low',
          risk_score: 85,
        },
        [addresses[1].toLowerCase()]: {
          token_name: 'Token 2',
          token_symbol: 'TOK2',
          token_type: 'ERC20',
          contract_address: addresses[1],
          holder_count: 500,
          token_price: '0',
          lp_holder_count: 5,
          lp_total_supply: '0',
          owner_address: '0xowner2',
          creator_address: '0xcreator2',
          creator_balance: '0',
          creator_percent: 80,
          transfer_tax: 99,
          buy_tax: 99,
          sell_tax: 99,
          buy_count: 10,
          sell_count: 5,
          transfer_count: 1,
          last_trade_time: Date.now(),
          is_honeypot: true,
          is_anti_honeypot: false,
          is_in_blacklist: false,
          is_open_source: false,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: true,
          hidden_owner: true,
          is_honeypot_confirmed: true,
          is_trustable: false,
          is_mintable: true,
          is_proxy_with_implementation: false,
          slippage_modifiable: true,
          transfer_tax_modifiable: true,
          buy_tax_modifiable: true,
          sell_tax_modifiable: true,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '0',
          owner_proportion: 80,
          owner_balance: 80,
          confidence: 10,
          risk_level: 'critical',
          risk_score: 0,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getBatchTokenSecurity(addresses, '1');

      expect(result.size).toBe(2);
      expect(result.get(addresses[0])?.isHoneypot).toBe(false);
      expect(result.get(addresses[1])?.isHoneypot).toBe(true);
    });

    it('should handle empty address array', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const result = await goPlusSecurityService.getBatchTokenSecurity([], '1');

      expect(result.size).toBe(0);
    });
  });

  describe('parseTokenSecurity (via getTokenSecurity)', () => {
    it('should generate warnings for high taxes', async () => {
      const mockResponse = {
        '0xtest': {
          token_name: 'High Tax Token',
          token_symbol: 'TAX',
          token_type: 'ERC20',
          contract_address: '0xtest',
          holder_count: 1000,
          token_price: '1',
          lp_holder_count: 10,
          lp_total_supply: '1000',
          owner_address: '0xowner',
          creator_address: '0xcreator',
          creator_balance: '50',
          creator_percent: 5,
          transfer_tax: 10,
          buy_tax: 15,
          sell_tax: 15,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: false,
          is_anti_honeypot: true,
          is_in_blacklist: false,
          is_open_source: true,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: false,
          is_trustable: true,
          is_mintable: false,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '1',
          owner_proportion: 5,
          owner_balance: 5,
          confidence: 80,
          risk_level: 'medium',
          risk_score: 70,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getTokenSecurity('0xtest', '1');

      expect(result?.warnings.some(w => w.includes('High tax'))).toBe(true);
    });

    it('should generate warnings for mintable tokens', async () => {
      const mockResponse = {
        '0xtest': {
          token_name: 'Mintable Token',
          token_symbol: 'MINT',
          token_type: 'ERC20',
          contract_address: '0xtest',
          holder_count: 1000,
          token_price: '1',
          lp_holder_count: 10,
          lp_total_supply: '1000',
          owner_address: '0xowner',
          creator_address: '0xcreator',
          creator_balance: '0',
          creator_percent: 0,
          transfer_tax: 0,
          buy_tax: 0,
          sell_tax: 0,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: false,
          is_anti_honeypot: true,
          is_in_blacklist: false,
          is_open_source: true,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: false,
          is_trustable: true,
          is_mintable: true,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '0',
          owner_proportion: 0,
          owner_balance: 0,
          confidence: 75,
          risk_level: 'low',
          risk_score: 85,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getTokenSecurity('0xtest', '1');

      expect(result?.warnings.some(w => w.includes('mintable'))).toBe(true);
    });

    it('should generate warnings for unverified contracts', async () => {
      const mockResponse = {
        '0xtest': {
          token_name: 'Unverified Token',
          token_symbol: 'UNV',
          token_type: 'ERC20',
          contract_address: '0xtest',
          holder_count: 1000,
          token_price: '1',
          lp_holder_count: 10,
          lp_total_supply: '1000',
          owner_address: '0xowner',
          creator_address: '0xcreator',
          creator_balance: '0',
          creator_percent: 0,
          transfer_tax: 0,
          buy_tax: 0,
          sell_tax: 0,
          buy_count: 100,
          sell_count: 50,
          transfer_count: 10,
          last_trade_time: Date.now(),
          is_honeypot: false,
          is_anti_honeypot: true,
          is_in_blacklist: false,
          is_open_source: false,
          is_proxy: false,
          is_whitelisted: false,
          can_take_back_ownership: false,
          hidden_owner: false,
          is_honeypot_confirmed: false,
          is_trustable: false,
          is_mintable: false,
          is_proxy_with_implementation: false,
          slippage_modifiable: false,
          transfer_tax_modifiable: false,
          buy_tax_modifiable: false,
          sell_tax_modifiable: false,
          is_token_deprecated: false,
          is_blacklisted_token: false,
          personal_slippage_recommend: '0',
          owner_proportion: 0,
          owner_balance: 0,
          confidence: 60,
          risk_level: 'medium',
          risk_score: 75,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getTokenSecurity('0xtest', '1');

      expect(result?.warnings.some(w => w.includes('not verified'))).toBe(true);
    });
  });

  describe('getApproveSecurity', () => {
    it('should fetch approve security data', async () => {
      const mockResponse = {
        '0xtest': {
          seal_status: true,
          allowance: 1000000,
          token_symbol: 'TEST',
          token_name: 'Test Token',
          contract_address: '0xtest',
          risk_description: 'Low risk',
          risk_details: ['Safe to approve'],
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await goPlusSecurityService.getApproveSecurity('0xtest', '1');

      expect(result).toBeDefined();
      expect(result?.['0xtest']).toBeDefined();
    });
  });
});
