/**
 * Trading Dashboard Page
 * Combines TradingView charts with live signals and market data
 */

import { useState } from "react";
import { TradingViewChart, SymbolOverview, TickerTape } from "../components/Trading/TradingViewChart";
import { TradingSignals } from "../components/Trading/TradingSignals";
import { PriceDisplay } from "../components/Market/PriceDisplay";
import { trpc } from "../lib/trpc";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Copy, Check, AlertCircle } from "lucide-react";

export function TradingDashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");
  const [copiedWebhook, setCopiedWebhook] = useState(false);

  const { data: webhookInfo } = trpc.tradingView.getWebhookUrl.useQuery();
  const { data: alertTemplate } = trpc.tradingView.getAlertTemplate.useQuery();

  const copyWebhookUrl = () => {
    if (webhookInfo?.webhookUrl) {
      navigator.clipboard.writeText(webhookInfo.webhookUrl);
      setCopiedWebhook(true);
      setTimeout(() => setCopiedWebhook(false), 2000);
    }
  };

  const featuredSymbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Trading Dashboard</h1>
        <p className="text-muted-foreground">
          Live charts from TradingView + AI-powered trading signals
        </p>
      </div>

      {/* Ticker Tape */}
      <div className="mb-6">
        <TickerTape symbols={featuredSymbols} height={60} />
      </div>

      {/* Main Content */}
      <Tabs defaultValue="chart" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="chart">Chart</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
          <TabsTrigger value="overview">Market Overview</TabsTrigger>
          <TabsTrigger value="setup">Webhook Setup</TabsTrigger>
        </TabsList>

        {/* Chart Tab */}
        <TabsContent value="chart" className="space-y-6">
          {/* Symbol Selector */}
          <div className="flex flex-wrap gap-2">
            {featuredSymbols.map((symbol) => (
              <Button
                key={symbol}
                variant={selectedSymbol === symbol ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedSymbol(symbol)}
              >
                {symbol.replace("USDT", "")}
              </Button>
            ))}
          </div>

          {/* TradingView Chart */}
          <TradingViewChart
            symbol={selectedSymbol}
            theme="dark"
            interval="15"
            height={600}
            showToolbar={true}
          />

          {/* Price Display */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {featuredSymbols.map((symbol) => (
              <PriceDisplay
                key={symbol}
                symbol={symbol.replace("USDT", "")}
                showDetails={false}
              />
            ))}
          </div>
        </TabsContent>

        {/* Signals Tab */}
        <TabsContent value="signals">
          <TradingSignals />
        </TabsContent>

        {/* Market Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Symbol Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <SymbolOverview symbols={featuredSymbols} height={600} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Webhook Setup Tab */}
        <TabsContent value="setup">
          <div className="space-y-6">
            {/* Webhook URL */}
            <Card>
              <CardHeader>
                <CardTitle>Your Webhook URL</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    readOnly
                    value={webhookInfo?.webhookUrl || ""}
                    className="flex-1 px-3 py-2 bg-muted rounded-lg text-sm font-mono"
                  />
                  <Button onClick={copyWebhookUrl} variant="outline">
                    {copiedWebhook ? (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>

                {webhookInfo?.instructions && (
                  <div className="space-y-2">
                    <h4 className="font-semibold">Setup Instructions:</h4>
                    <ol className="list-decimal list-inside space-y-2 text-sm">
                      <li>{webhookInfo.instructions.step1}</li>
                      <li>{webhookInfo.instructions.step2}</li>
                      <li>{webhookInfo.instructions.step3}</li>
                      <li>{webhookInfo.instructions.step4}</li>
                      <li>{webhookInfo.instructions.step5}</li>
                    </ol>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Alert Template */}
            <Card>
              <CardHeader>
                <CardTitle>Alert Message Template</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-muted p-4 rounded-lg">
                  <pre className="text-sm font-mono overflow-x-auto">
                    {alertTemplate?.template}
                  </pre>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Example:</h4>
                  <div className="bg-muted p-4 rounded-lg">
                    <pre className="text-sm font-mono">
                      {JSON.stringify(alertTemplate?.example, null, 2)}
                    </pre>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Info Card */}
            <Card className="border-blue-500/50 bg-blue-500/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-blue-500" />
                  How It Works
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  1. Set up alerts in TradingView with your custom conditions
                </p>
                <p>
                  2. Configure the webhook to send alerts to this platform
                </p>
                <p>
                  3. Alerts are combined with audit scores to generate trading signals
                </p>
                <p>
                  4. View signals in the Signals tab with entry/exit points
                </p>
                <p className="text-muted-foreground pt-2">
                  <strong>Tip:</strong> Use RSI oversold/overbought, MACD crossovers, or
                  price breakouts for the best signals.
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
