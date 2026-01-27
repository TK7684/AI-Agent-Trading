/**
 * Trading Signals Display Component
 * Shows combined signals from TradingView + Audit + Gemini
 */

import { useState } from "react";
import { trpc } from "../../lib/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { TrendingUp, TrendingDown, Minus, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

interface SignalCardProps {
  signal: {
    id: number;
    symbol: string;
    signalType: "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
    confidence: number;
    entryPrice: string;
    stopLoss: string;
    takeProfit: string;
    reasoning: string;
    riskLevel: string;
    status: "active" | "executed" | "expired";
    createdAt: Date;
    expiresAt: Date | null;
  };
  onExecute?: (id: number) => void;
  onExpire?: (id: number) => void;
}

function SignalCard({ signal, onExecute, onExpire }: SignalCardProps) {
  const getActionColor = (action: string) => {
    switch (action) {
      case "STRONG_BUY":
      case "BUY":
        return "text-green-500 bg-green-500/10";
      case "STRONG_SELL":
      case "SELL":
        return "text-red-500 bg-red-500/10";
      default:
        return "text-yellow-500 bg-yellow-500/10";
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case "STRONG_BUY":
      case "BUY":
        return <TrendingUp className="h-4 w-4" />;
      case "STRONG_SELL":
      case "SELL":
        return <TrendingDown className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge variant="outline" className="gap-1"><Clock className="h-3 w-3" /> Active</Badge>;
      case "executed":
        return <Badge variant="default" className="gap-1 bg-green-500"><CheckCircle2 className="h-3 w-3" /> Executed</Badge>;
      case "expired":
        return <Badge variant="secondary" className="gap-1"><XCircle className="h-3 w-3" /> Expired</Badge>;
    }
  };

  const getRiskBadge = (risk: string) => {
    const colors: Record<string, string> = {
      low: "bg-green-500/20 text-green-500",
      medium: "bg-yellow-500/20 text-yellow-500",
      high: "bg-orange-500/20 text-orange-500",
      critical: "bg-red-500/20 text-red-500",
    };
    return <Badge className={colors[risk] || colors.medium}>{risk.toUpperCase()}</Badge>;
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">{signal.symbol}</CardTitle>
            <Badge className={getActionColor(signal.signalType)}>
              {getActionIcon(signal.signalType)}
              {signal.signalType}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(signal.status)}
            {getRiskBadge(signal.riskLevel)}
          </div>
        </div>
        <div className="text-sm text-muted-foreground">
          Confidence: {signal.confidence.toFixed(0)}%
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Trading Levels */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-muted/50 rounded-lg p-2">
            <p className="text-xs text-muted-foreground">Entry</p>
            <p className="font-semibold">${signal.entryPrice}</p>
          </div>
          <div className="bg-red-500/10 rounded-lg p-2">
            <p className="text-xs text-muted-foreground">Stop Loss</p>
            <p className="font-semibold text-red-500">${signal.stopLoss}</p>
          </div>
          <div className="bg-green-500/10 rounded-lg p-2">
            <p className="text-xs text-muted-foreground">Take Profit</p>
            <p className="font-semibold text-green-500">${signal.takeProfit}</p>
          </div>
        </div>

        {/* Reasoning */}
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-sm">{signal.reasoning}</p>
        </div>

        {/* Actions */}
        {signal.status === "active" && (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="default"
              className="flex-1"
              onClick={() => onExecute?.(signal.id)}
            >
              Mark Executed
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={() => onExpire?.(signal.id)}
            >
              Mark Expired
            </Button>
          </div>
        )}

        {/* Timestamps */}
        <div className="text-xs text-muted-foreground">
          Created: {new Date(signal.createdAt).toLocaleString()}
          {signal.expiresAt && ` • Expires: ${new Date(signal.expiresAt).toLocaleString()}`}
        </div>
      </CardContent>
    </Card>
  );
}

export function TradingSignals() {
  const [statusFilter, setStatusFilter] = useState<"active" | "executed" | "expired" | "all">("all");

  const { data: signals, isLoading, refetch } = trpc.tradingView.getSignals.useQuery(
    { limit: 50, status: statusFilter === "all" ? undefined : statusFilter },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  );

  const updateSignalStatus = trpc.tradingView.updateSignalStatus.useMutation({
    onSuccess: () => refetch(),
  });

  const handleExecute = (id: number) => {
    updateSignalStatus.mutate({ id, status: "executed" });
  };

  const handleExpire = (id: number) => {
    updateSignalStatus.mutate({ id, status: "expired" });
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Trading Signals</CardTitle>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={statusFilter === "all" ? "default" : "outline"}
              onClick={() => setStatusFilter("all")}
            >
              All
            </Button>
            <Button
              size="sm"
              variant={statusFilter === "active" ? "default" : "outline"}
              onClick={() => setStatusFilter("active")}
            >
              Active
            </Button>
            <Button
              size="sm"
              variant={statusFilter === "executed" ? "default" : "outline"}
              onClick={() => setStatusFilter("executed")}
            >
              Executed
            </Button>
            <Button
              size="sm"
              variant={statusFilter === "expired" ? "default" : "outline"}
              onClick={() => setStatusFilter("expired")}
            >
              Expired
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : signals && signals.length > 0 ? (
          <div className="space-y-4">
            {signals.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={{
                  ...signal,
                  createdAt: new Date(signal.createdAt),
                  expiresAt: signal.expiresAt ? new Date(signal.expiresAt) : null,
                  signalType: signal.signalType as "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL",
                  status: signal.status as "active" | "executed" | "expired",
                  confidence: signal.confidence ?? 0,
                  riskLevel: signal.riskLevel ?? "medium",
                  entryPrice: signal.entryPrice ?? "N/A",
                  stopLoss: signal.stopLoss ?? "N/A",
                  takeProfit: signal.takeProfit ?? "N/A",
                  reasoning: signal.reasoning ?? "No reasoning provided",
                }}
                onExecute={handleExecute}
                onExpire={handleExpire}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            {statusFilter === "active"
              ? "No active signals. Set up TradingView alerts to generate signals."
              : "No signals found."}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
