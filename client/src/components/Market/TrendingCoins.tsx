/**
 * Trending Coins Component
 * Shows the most searched cryptocurrencies from CoinGecko (FREE API)
 */

import { trpc } from "../../lib/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { TrendingUp, Loader2 } from "lucide-react";
import { Link } from "wouter";

export function TrendingCoins() {
  const { data: trending, isLoading } = trpc.marketData.getTrending.useQuery(
    undefined,
    {
      refetchInterval: 120000, // Refresh every 2 minutes
    }
  );

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          Trending Now
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {trending?.map((coin, index) => (
              <Link key={coin.symbol} href={`/coin/${coin.symbol}`}>
                <div className="flex items-center gap-3 p-3 hover:bg-muted/50 rounded-lg transition-colors cursor-pointer">
                  <div className="text-lg font-bold text-muted-foreground w-6">
                    {index + 1}
                  </div>
                  {coin.thumb && (
                    <img src={coin.thumb} alt={coin.name} className="w-8 h-8 rounded-full" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium">{coin.name}</p>
                    <p className="text-sm text-muted-foreground">{coin.symbol}</p>
                  </div>
                  {coin.marketCapRank && (
                    <div className="text-xs text-muted-foreground">
                      #{coin.marketCapRank}
                    </div>
                  )}
                </div>
              </Link>
            ))}

            {!trending || trending.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No trending data available
              </div>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
