/**
 * TradingView Chart Component
 * Uses your TradingView subscription to display professional charts
 * Works with your existing TradingView account
 */

import { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

interface TradingViewChartProps {
  symbol: string;
  theme?: "light" | "dark";
  interval?: string;
  height?: number;
  showToolbar?: boolean;
  studies?: string[];
}

export function TradingViewChart({
  symbol,
  theme = "dark",
  interval = "15",
  height = 600,
  showToolbar = true,
  studies = ["RSI@tv-basicstudies", "MACD@tv-basicstudies"],
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clean up previous script
    if (scriptRef.current && scriptRef.current.parentNode) {
      scriptRef.current.parentNode.removeChild(scriptRef.current);
    }

    // Load TradingView Widget
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    scriptRef.current = script;

    script.onload = () => {
      // @ts-ignore - TradingView global
      if (typeof TradingView !== "undefined") {
        // @ts-ignore
        new TradingView.widget({
          autosize: true,
          symbol: `BINANCE:${symbol}`,
          interval,
          timezone: "Etc/UTC",
          theme,
          style: "1",
          locale: "en",
          toolbar_bg: theme === "dark" ? "#1e1e1e" : "#f1f3f6",
          enable_publishing: false,
          allow_symbol_change: true,
          container_id: containerRef.current?.id,
          hide_side_toolbar: !showToolbar,
          studies,
          // Your subscription features (if applicable)
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: false,
          details: true,
          hotlist: true,
          calendar: true,
        });
      }
    };

    containerRef.current.appendChild(script);

    return () => {
      if (scriptRef.current && scriptRef.current.parentNode) {
        scriptRef.current.parentNode.removeChild(scriptRef.current);
      }
    };
  }, [symbol, theme, interval, showToolbar, studies]);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>{symbol} Chart</span>
          <span className="text-xs text-muted-foreground font-normal">
            Powered by TradingView
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div
          ref={containerRef}
          id={`tradingview_${symbol}`}
          className="w-full"
          style={{ height: `${height}px` }}
        />
      </CardContent>
    </Card>
  );
}

/**
 * TradingView Symbol Overview Widget
 * Shows a mini chart with ticker info
 */
interface SymbolOverviewProps {
  symbols: string[];
  chartOnly?: boolean;
  height?: number;
}

export function SymbolOverview({
  symbols,
  chartOnly = false,
  height = 500,
}: SymbolOverviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clean up previous script
    if (scriptRef.current && scriptRef.current.parentNode) {
      scriptRef.current.parentNode.removeChild(scriptRef.current);
    }

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js";
    script.async = true;
    script.type = "text/javascript";
    scriptRef.current = script;

    // Create config object
    const config = {
      symbols: symbols.map((s) => [`BINANCE:${s}`, ""]).flat(),
      chartOnly: chartOnly,
      width: "100%",
      height: height,
      locale: "en",
      colorTheme: "dark",
      autosize: true,
      showVolume: true,
      showMA: false,
      hideDateRanges: false,
      hideMarketStatus: false,
      hideSymbolLogo: false,
      scalePosition: "right",
      scaleMode: "Normal",
      fontFamily: "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
      fontSize: "10",
      noTimeScale: false,
      valuesTracking: "1",
      changeMode: "price-and-percent",
      dateFormat: "dd MMM 'yy",
    };

    script.innerHTML = JSON.stringify(config);

    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(
      <div className="tradingview-widget-container" style={{ height: "100%", width: "100%" }}>
        <div className="tradingview-widget-container__widget" style={{ height, width: "100%" }}></div>
      </div>
    );
    containerRef.current.appendChild(script);

    return () => {
      if (scriptRef.current && scriptRef.current.parentNode) {
        scriptRef.current.parentNode.removeChild(scriptRef.current);
      }
    };
  }, [symbols, chartOnly, height]);

  return (
    <div ref={containerRef} className="w-full" style={{ height: `${height}px` }} />
  );
}

/**
 * TradingView Ticker Tape Widget
 * Shows scrolling ticker for multiple symbols
 */
interface TickerTapeProps {
  symbols: string[];
  height?: number;
}

export function TickerTape({ symbols, height = 60 }: TickerTapeProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
    script.async = true;
    script.type = "text/javascript";

    const config = {
      symbols: symbols.map((s) => ({
        proName: `BINANCE:${s}`,
        title: s,
      })),
      showSymbolLogo: true,
      isTransparent: false,
      displayMode: "adaptive",
      colorTheme: "dark",
      width: "100%",
      height: height,
      locale: "en",
    };

    script.innerHTML = JSON.stringify(config);

    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container";
    widgetDiv.style.height = `${height}px`;

    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(widgetDiv);
    widgetDiv.appendChild(script);

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [symbols, height]);

  return <div ref={containerRef} className="w-full" />;
}
