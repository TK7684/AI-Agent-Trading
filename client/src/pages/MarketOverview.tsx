/**
 * Market Overview Page
 * Comprehensive market data from FREE APIs (CoinGecko, Binance)
 */

import { TopCoins } from "../components/Market/TopCoins";
import { TrendingCoins } from "../components/Market/TrendingCoins";
import { PriceDisplay } from "../components/Market/PriceDisplay";

export function MarketOverview() {
  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Crypto Market Overview</h1>
        <p className="text-muted-foreground">
          Live market data powered by free APIs (CoinGecko, Binance)
        </p>
      </div>

      {/* Featured Coins */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Featured Assets</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <PriceDisplay symbol="BTC" />
          <PriceDisplay symbol="ETH" />
          <PriceDisplay symbol="SOL" />
          <PriceDisplay symbol="BNB" />
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Coins List */}
        <div className="lg:col-span-2">
          <TopCoins />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Trending */}
          <TrendingCoins />

          {/* Market Stats */}
          <div className="bg-muted rounded-lg p-4">
            <h3 className="font-semibold mb-2">About this data</h3>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Powered by CoinGecko Free API</li>
              <li>• Binance Public API for OHLCV data</li>
              <li>• No paid services required</li>
              <li>• Data refreshes every 30-60 seconds</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
