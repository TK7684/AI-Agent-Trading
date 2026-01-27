/**
 * Price Display Component
 * Shows live price data from FREE APIs (CoinGecko, Binance)
 */

import { useEffect, useState } from "react";
import { trpc } from "../../lib/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { TrendingUp, TrendingDown, Loader2 } from "lucide-react";

interface PriceDisplayProps {
  symbol: string;
  showDetails?: boolean;
  refreshInterval?: number; // seconds
}

export function PriceDisplay({ symbol, showDetails = false, refreshInterval = 30 }: PriceDisplayProps) {
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const { data: priceData, isLoading, error, refetch } = trpc.marketData.getPrice.useQuery(
    { symbol, useCache: true },
    {
      refetchInterval: refreshInterval * 1000,
    }
  );

  // Update lastUpdate when data is fetched
  useEffect(() => {
    if (priceData) {
      setLastUpdate(new Date());
    }
  }, [priceData]);

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-6">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error || !priceData) {
    return (
      <Card className="w-full border-destructive">
        <CardContent className="flex items-center justify-center py-6">
          <p className="text-sm text-destructive">Failed to load price data</p>
        </CardContent>
      </Card>
    );
  }

  const isPositive = priceData.change24h >= 0;

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold">{symbol}</CardTitle>
          <button
            onClick={() => refetch()}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Refresh
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Price */}
        <div>
          <p className="text-3xl font-bold">
            ${priceData.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>

        {/* 24h Change */}
        <div className={`flex items-center gap-1 ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
          {isPositive ? (
            <TrendingUp className="h-4 w-4" />
          ) : (
            <TrendingDown className="h-4 w-4" />
          )}
          <span className="font-semibold">
            {isPositive ? '+' : ''}{priceData.change24h.toFixed(2)}%
          </span>
          <span className="text-muted-foreground text-sm">24h</span>
        </div>

        {/* Additional Details */}
        {showDetails && (
          <div className="grid grid-cols-2 gap-2 pt-3 border-t">
            <div>
              <p className="text-xs text-muted-foreground">Market Cap</p>
              <p className="text-sm font-medium">
                ${priceData.marketCap.toLocaleString('en-US', { notation: 'compact' })}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">24h Volume</p>
              <p className="text-sm font-medium">
                ${priceData.volume24h.toLocaleString('en-US', { notation: 'compact' })}
              </p>
            </div>
            {priceData.high24h > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">24h High</p>
                <p className="text-sm font-medium">${priceData.high24h.toLocaleString()}</p>
              </div>
            )}
            {priceData.low24h > 0 && (
              <div>
                <p className="text-xs text-muted-foreground">24h Low</p>
                <p className="text-sm font-medium">${priceData.low24h.toLocaleString()}</p>
              </div>
            )}
            {priceData.ath > 0 && (
              <>
                <div>
                  <p className="text-xs text-muted-foreground">ATH</p>
                  <p className="text-sm font-medium">${priceData.ath.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">From ATH</p>
                  <p className={`text-sm font-medium ${priceData.athChange < 0 ? 'text-red-500' : 'text-green-500'}`}>
                    {priceData.athChange.toFixed(1)}%
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {/* Last Update */}
        <p className="text-xs text-muted-foreground">
          Updated {lastUpdate.toLocaleTimeString()}
        </p>
      </CardContent>
    </Card>
  );
}
