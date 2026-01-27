/**
 * Analytics Dashboard Component
 * Displays user metrics, feature usage, revenue analytics, and trends
 */

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/trpc';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Users,
  Activity,
  DollarSign,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Calendar,
  Download,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down' | 'neutral';
}

function MetricCard({ title, value, change, icon: Icon, trend = 'neutral' }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {change !== undefined && (
              <div className="flex items-center gap-1 text-xs">
                {trend === 'up' ? (
                  <TrendingUp className="h-3 w-3 text-green-500" />
                ) : trend === 'down' ? (
                  <TrendingDown className="h-3 w-3 text-red-500" />
                ) : null}
                <span className={cn(
                  trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-muted-foreground'
                )}>
                  {change > 0 ? '+' : ''}{change}%
                </span>
              </div>
            )}
          </div>
          <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ChartProps {
  data: Array<{ label: string; value: number }>;
  color?: string;
}

function SimpleBarChart({ data, color = 'hsl(var(--primary))' }: ChartProps) {
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="space-y-2">
      {data.map((item, index) => (
        <div key={index} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{item.label}</span>
            <span className="font-medium">{item.value.toLocaleString()}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${(item.value / maxValue) * 100}%`,
                backgroundColor: color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function AnalyticsDashboard() {
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { data: analytics, isLoading, refetch } = api.analytics.getAll.useQuery({
    days: dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90,
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-20 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <BarChart3 className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
          <p className="text-muted-foreground">Unable to load analytics data</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h2>
          <p className="text-muted-foreground">
            Track user activity, feature usage, and business metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', isRefreshing && 'animate-spin')} />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="flex items-center gap-2">
        <Button
          variant={dateRange === '7d' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setDateRange('7d')}
        >
          Last 7 days
        </Button>
        <Button
          variant={dateRange === '30d' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setDateRange('30d')}
        >
          Last 30 days
        </Button>
        <Button
          variant={dateRange === '90d' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setDateRange('90d')}
        >
          Last 90 days
        </Button>
      </div>

      {/* User Metrics */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">User Metrics</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Users"
            value={analytics.users.totalUsers.toLocaleString()}
            change={12}
            trend="up"
            icon={Users}
          />
          <MetricCard
            title="Active Users"
            value={analytics.users.activeUsers.toLocaleString()}
            change={8}
            trend="up"
            icon={Activity}
          />
          <MetricCard
            title="New Users"
            value={analytics.users.newUsers.toLocaleString()}
            change={-3}
            trend="down"
            icon={TrendingUp}
          />
          <MetricCard
            title="Paid Users"
            value={analytics.users.paidUsers.toLocaleString()}
            change={15}
            trend="up"
            icon={DollarSign}
          />
        </div>
      </div>

      {/* Feature Usage */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Feature Usage</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Projects</p>
                <p className="text-2xl font-bold">{analytics.features.totalProjects}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Audits Run</p>
                <p className="text-2xl font-bold">{analytics.features.totalAudits}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Watchlist</p>
                <p className="text-2xl font-bold">{analytics.features.totalWatchlist}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Comparisons</p>
                <p className="text-2xl font-bold">{analytics.features.totalComparisons}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Alerts</p>
                <p className="text-2xl font-bold">{analytics.features.totalAlerts}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Revenue & Performance */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Revenue</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">MRR</p>
                <p className="text-2xl font-bold">${analytics.revenue.mrr.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">ARR</p>
                <p className="text-2xl font-bold">${analytics.revenue.arr.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">ARPU</p>
                <p className="text-xl font-bold">${analytics.revenue.arpu}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">LTV</p>
                <p className="text-xl font-bold">${analytics.revenue.ltv}</p>
              </div>
            </div>
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Trial Conversions</span>
                <Badge variant="secondary">{analytics.revenue.trialConversions}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Avg Response Time</span>
                <span className="font-medium">{analytics.performance.avgResponseTime}ms</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: '85%' }}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Uptime</span>
                <span className="font-medium">{analytics.performance.uptime}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${analytics.performance.uptime}%` }}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Error Rate</span>
                <span className="font-medium">{(analytics.performance.errorRate * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-500 rounded-full"
                  style={{ width: `${analytics.performance.errorRate * 100}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trends */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Active Users (Last 7 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <SimpleBarChart
            data={analytics.trends.dailyUsers.slice(-7).map(d => ({
              label: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
              value: d.count,
            }))}
          />
        </CardContent>
      </Card>
    </div>
  );
}

export default AnalyticsDashboard;
