/**
 * Top Coins by Market Cap
 * Displays the top cryptocurrencies from CoinGecko (FREE API)
 */

import { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { TrendingUp, TrendingDown, Search, Loader2 } from "lucide-react";
import { Link } from "wouter";

export function TopCoins() {
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(20);

  const { data: coins, isLoading, error } = trpc.marketData.getTopCoins.useQuery(
    { limit, currency: 'usd' },
    {
      refetchInterval: 60000, // Refresh every minute
    }
  );

  const { data: searchResults } = trpc.marketData.searchCoins.useQuery(
    { query: search },
    {
      enabled: search.length >= 2,
    }
  );

  const displayCoins = search.length >= 2 ? searchResults || [] : coins || [];

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Top Cryptocurrencies</CardTitle>
          <div className="flex gap-2">
            <Button
              variant={limit === 20 ? "default" : "outline"}
              size="sm"
              onClick={() => setLimit(20)}
            >
              Top 20
            </Button>
            <Button
              variant={limit === 50 ? "default" : "outline"}
              size="sm"
              onClick={() => setLimit(50)}
            >
              Top 50
            </Button>
            <Button
              variant={limit === 100 ? "default" : "outline"}
              size="sm"
              onClick={() => setLimit(100)}
            >
              Top 100
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search coins..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="text-center py-8 text-destructive">
            Failed to load market data
          </div>
        )}

        {/* Coins List */}
        {!isLoading && !error && (
          <div className="space-y-2">
            {/* Header */}
            <div className="grid grid-cols-6 gap-2 px-4 py-2 text-sm font-medium text-muted-foreground border-b">
              <div className="col-span-1">#</div>
              <div className="col-span-2">Coin</div>
              <div className="col-span-1 text-right">Price</div>
              <div className="col-span-1 text-right">24h %</div>
              <div className="col-span-1 text-right">Market Cap</div>
            </div>

            {/* Rows */}
            {displayCoins.map((coin, index) => {
              const isPositive = coin.change24h >= 0;

              return (
                <Link
                  key={coin.id || coin.symbol}
                  href={`/coin/${coin.symbol}`}
                  className="block"
                >
                  <div className="grid grid-cols-6 gap-2 px-4 py-3 hover:bg-muted/50 rounded-lg transition-colors cursor-pointer">
                    <div className="col-span-1 text-muted-foreground">
                      {coin.marketCapRank || (index + 1)}
                    </div>
                    <div className="col-span-2 flex items-center gap-2">
                      {coin.image && (
                        <img src={coin.image} alt={coin.name} className="w-6 h-6 rounded-full" />
                      )}
                      <div>
                        <p className="font-medium">{coin.symbol}</p>
                        <p className="text-xs text-muted-foreground">{coin.name}</p>
                      </div>
                    </div>
                    <div className="col-span-1 text-right font-medium">
                      ${coin.price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'N/A'}
                    </div>
                    <div className={`col-span-1 text-right font-medium flex items-center justify-end gap-1 ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                      {isPositive ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {isPositive ? '+' : ''}{(coin.change24h || 0).toFixed(2)}%
                    </div>
                    <div className="col-span-1 text-right text-muted-foreground">
                      ${(coin.marketCap / 1e9).toFixed(1)}B
                    </div>
                  </div>
                </Link>
              );
            })}

            {/* No results */}
            {displayCoins.length === 0 && !isLoading && (
              <div className="text-center py-8 text-muted-foreground">
                {search.length >= 2 ? 'No coins found' : 'No coins available'}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
