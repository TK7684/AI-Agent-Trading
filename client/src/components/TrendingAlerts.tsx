import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bell, Loader2, Shield, X, TrendingUp, AlertTriangle, Sparkles } from "lucide-react";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { Link } from "wouter";
import { useEffect, useState } from "react";

interface TrendingAlert {
  id: string;
  title: string;
  message: string;
  type: "info" | "warning" | "critical";
  projectId: string;
  projectName: string;
  projectSymbol: string;
  timestamp: Date;
  data: any;
}

interface TrendingAlertsProps {
  onClose?: () => void;
}

export function TrendingAlerts({ onClose }: TrendingAlertsProps) {
  const [alerts, setAlerts] = useState<TrendingAlert[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const { data: trendingAlerts, isLoading } = trpc.alerts.checkTrending.useQuery(undefined, {
    refetchInterval: 5 * 60 * 1000, // Check every 5 minutes
  });

  useEffect(() => {
    if (trendingAlerts) {
      setAlerts(trendingAlerts);
    }
  }, [trendingAlerts]);

  const visibleAlerts = alerts.filter((alert) => !Array.from(dismissed).includes(alert.id));

  const handleDismiss = (alertId: string) => {
    setDismissed(new Set(Array.from(dismissed).concat([alertId])));
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "critical":
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case "warning":
        return <TrendingUp className="h-5 w-5 text-orange-500" />;
      default:
        return <Sparkles className="h-5 w-5 text-blue-500" />;
    }
  };

  const getAlertStyles = (type: string) => {
    switch (type) {
      case "critical":
        return "border-red-500/50 bg-red-500/5";
      case "warning":
        return "border-orange-500/50 bg-orange-500/5";
      default:
        return "border-blue-500/50 bg-blue-500/5";
    }
  };

  if (isLoading) {
    return null;
  }

  if (visibleAlerts.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 max-w-md w-full space-y-3">
      {onClose && (
        <div className="flex justify-end mb-2">
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4 mr-2" />
            Close
          </Button>
        </div>
      )}
      {visibleAlerts.map((alert) => (
        <Card key={alert.id} className={`${getAlertStyles(alert.type)} shadow-lg`}>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">{getAlertIcon(alert.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-sm">{alert.title}</h4>
                    <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 flex-shrink-0"
                    onClick={() => handleDismiss(alert.id)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Badge variant="outline" className="text-xs">
                    {alert.projectSymbol}
                  </Badge>
                  <Link href={`/discover`}>
                    <Button size="sm" variant="outline" className="h-7 text-xs">
                      <Shield className="h-3 w-3 mr-1" />
                      View Project
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * Trending Alerts Bell - A bell icon that shows the number of new alerts
 */
export function TrendingAlertsBell() {
  const [isOpen, setIsOpen] = useState(false);
  const { data: trendingAlerts } = trpc.alerts.checkTrending.useQuery(undefined, {
    refetchInterval: 5 * 60 * 1000, // Check every 5 minutes
  });

  const alertCount = trendingAlerts?.length || 0;

  if (alertCount === 0) {
    return null;
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        className="relative"
      >
        <Bell className="h-5 w-5" />
        {alertCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
            {alertCount > 9 ? "9+" : alertCount}
          </span>
        )}
      </Button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-12 z-50 w-80 max-h-96 overflow-y-auto">
            <Card>
              <TrendingAlerts onClose={() => setIsOpen(false)} />
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
