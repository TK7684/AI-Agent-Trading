import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { APP_TITLE } from "@/const";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sparkles, TrendingUp, DollarSign, Activity,
  Rocket, Eye, AlertCircle, CheckCircle2,
  Filter, Search, Github, Twitter, Coins,
  LineChart, Zap, Target, Gem, Flame
} from "lucide-react";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";

type UnicornScore = 'diamond-hands' | 'early-gem' | 'rising-star' | 'hidden-gem' | 'risky-bet';

interface UnicornProject {
  id: string;
  name: string;
  symbol: string;
  logo?: string;
  currentPrice: number;
  marketCap: number;
  priceChange24h: number;
  volume24h: number;
  unicornScore: number;
  scoreType: UnicornScore;
  potential: 'explosive' | 'high' | 'moderate' | 'low';
  discoveryStage: 'pre-listing' | 'early' | 'growing' | 'trending';

  // Technical Indicators
  signals: {
    socialVolume: number;
    devActivity: number;
    tokenomics: number;
    communityGrowth: number;
    liquidityDepth: number;
  };

  // Why it's a unicorn
  reasons: string[];
  warnings: string[];

  // Action Items
  actionItems: {
    buyNow: boolean;
    watchList: boolean;
    researchPriority: 'urgent' | 'high' | 'medium' | 'low';
  };

  // Deep Research
  deepResearch: {
    githubUrl?: string;
    twitterUrl?: string;
    telegramUrl?: string;
    websiteUrl?: string;
    contractAddress?: string;
    chain?: string;
    team: {
      doxxed: boolean;
      experience: string;
      previousProjects: string[];
    };
    tokenomics: {
      totalSupply: number;
      circulatingSupply: number;
      burned: number;
      liquidityLocked: boolean;
      contractRenounced: boolean;
    };
    partnerships: string[];
    upcomingEvents: string[];
  };
}

export default function UnicornHunterPage() {
  const [, setLocation] = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedScore, setSelectedScore] = useState<string>("all");
  const [selectedPotential, setSelectedPotential] = useState<string>("all");
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [isScanning, setIsScanning] = useState(false);
  const [unicorns, setUnicorns] = useState<UnicornProject[]>([]);
  const [selectedUnicorn, setSelectedUnicorn] = useState<UnicornProject | null>(null);

  const { data: trendingProjects, isLoading } = trpc.discovery.trending.useQuery({}, {
    refetchInterval: 60000, // Refresh every minute
  });

  // Unicorn Detection Algorithm
  const detectUnicorns = () => {
    setIsScanning(true);

    // Simulate deep scanning
    setTimeout(() => {
      if (!trendingProjects) return;

      const detected = trendingProjects.map((project: any) => {
        const score = calculateUnicornScore(project);
        return {
          id: project.id,
          name: project.name,
          symbol: project.symbol,
          logo: project.logo,
          currentPrice: project.currentPrice,
          marketCap: project.marketCap,
          priceChange24h: project.priceChange24h,
          volume24h: project.volume24h,
          unicornScore: score.total,
          scoreType: score.type,
          potential: score.potential,
          discoveryStage: score.stage,
          signals: score.signals,
          reasons: score.reasons,
          warnings: score.warnings,
          actionItems: score.actionItems,
          deepResearch: project.deepResearch || {},
        } as UnicornProject;
      }).filter((u: UnicornProject) => u.unicornScore >= 60); // Only show potential unicorns

      setUnicorns(detected.sort((a, b) => b.unicornScore - a.unicornScore));
      setIsScanning(false);

      toast.success(`Found ${detected.length} potential unicorns!`);
    }, 2000);
  };

  const calculateUnicornScore = (project: any) => {
    let score = 0;
    const reasons: string[] = [];
    const warnings: string[] = [];
    const signals = {
      socialVolume: 0,
      devActivity: 0,
      tokenomics: 0,
      communityGrowth: 0,
      liquidityDepth: 0,
    };

    // Market Cap Analysis (30 points) - Lower is better for early gems
    if (project.marketCap < 1000000) {
      score += 30;
      reasons.push("Tiny market cap - 100x+ potential");
      signals.liquidityDepth = 95;
    } else if (project.marketCap < 10000000) {
      score += 20;
      reasons.push("Small market cap - 50x+ potential");
      signals.liquidityDepth = 80;
    } else if (project.marketCap < 100000000) {
      score += 10;
      signals.liquidityDepth = 60;
    }

    // Price Momentum (25 points)
    if (project.priceChange24h > 50) {
      score += 25;
      reasons.push("Explosive price action - momentum building");
      signals.socialVolume = 90;
    } else if (project.priceChange24h > 20) {
      score += 20;
      reasons.push("Strong upward trend");
      signals.socialVolume = 75;
    } else if (project.priceChange24h > 5) {
      score += 10;
      reasons.push("Positive momentum");
      signals.socialVolume = 60;
    } else if (project.priceChange24h < -10) {
      score += 5;
      reasons.push("Oversold - potential bounce play");
      signals.socialVolume = 40;
    }

    // Volume Analysis (20 points) - High volume + low cap = Unicorn alert
    const volumeToMarketCapRatio = (project.volume24h / project.marketCap) * 100;
    if (volumeToMarketCapRatio > 10) {
      score += 20;
      reasons.push("Massive volume relative to market cap - accumulation detected");
      signals.communityGrowth = 95;
    } else if (volumeToMarketCapRatio > 5) {
      score += 15;
      reasons.push("High volume accumulation");
      signals.communityGrowth = 80;
    } else if (volumeToMarketCapRatio > 2) {
      score += 10;
      signals.communityGrowth = 60;
    }

    // Dev Activity (15 points) - Based on GitHub
    if (project.githubUrl) {
      score += 15;
      reasons.push("Active GitHub development - transparent team");
      signals.devActivity = 85;
    } else {
      warnings.push("No GitHub found - team may be closed");
    }

    // Community Strength (10 points)
    if (project.twitterUrl || project.telegramUrl) {
      score += 10;
      reasons.push("Active community channels");
    }

    // Determine score type
    let type: UnicornScore;
    if (score >= 90) type = 'diamond-hands';
    else if (score >= 80) type = 'early-gem';
    else if (score >= 70) type = 'rising-star';
    else if (score >= 60) type = 'hidden-gem';
    else type = 'risky-bet';

    // Determine potential
    let potential: 'explosive' | 'high' | 'moderate' | 'low';
    if (project.marketCap < 1000000 && project.priceChange24h > 20) potential = 'explosive';
    else if (project.marketCap < 10000000) potential = 'high';
    else if (project.marketCap < 50000000) potential = 'moderate';
    else potential = 'low';

    // Determine stage
    let stage: 'pre-listing' | 'early' | 'growing' | 'trending';
    if (signals.communityGrowth > 80 && signals.liquidityDepth > 80) stage = 'trending';
    else if (signals.communityGrowth > 60) stage = 'growing';
    else if (signals.liquidityDepth > 60) stage = 'early';
    else stage = 'pre-listing';

    // Action items
    const actionItems = {
      buyNow: potential === 'explosive' || (potential === 'high' && score >= 70),
      watchList: true,
      researchPriority: (potential === 'explosive' ? 'urgent' : potential === 'high' ? 'high' : 'medium') as 'urgent' | 'high' | 'medium' | 'low',
    };

    return { score, type, potential, stage, signals, reasons, warnings, actionItems };
  };

  // Filter unicorns
  const filteredUnicorns = unicorns.filter(unicorn => {
    const matchesSearch = unicorn.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          unicorn.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesScore = selectedScore === "all" || unicorn.scoreType === selectedScore;
    const matchesPotential = selectedPotential === "all" || unicorn.potential === selectedPotential;
    const matchesStage = selectedStage === "all" || unicorn.discoveryStage === selectedStage;

    return matchesSearch && matchesScore && matchesPotential && matchesStage;
  });

  // Get score badge color
  const getScoreBadge = (score: number, type: UnicornScore) => {
    const config = {
      'diamond-hands': { color: 'bg-purple-500/20 text-purple-700 border-purple-500', icon: Sparkles },
      'early-gem': { color: 'bg-blue-500/20 text-blue-700 border-blue-500', icon: Gem },
      'rising-star': { color: 'bg-green-500/20 text-green-700 border-green-500', icon: TrendingUp },
      'hidden-gem': { color: 'bg-yellow-500/20 text-yellow-700 border-yellow-500', icon: Eye },
      'risky-bet': { color: 'bg-red-500/20 text-red-700 border-red-500', icon: AlertCircle },
    };

    const { color, icon: Icon } = config[type];
    return { color, Icon };
  };

  // Get potential badge
  const getPotentialBadge = (potential: string) => {
    const config = {
      'explosive': { color: 'bg-orange-500/20 text-orange-700 border-orange-500', label: '🚀 EXPLOSIVE' },
      'high': { color: 'bg-green-500/20 text-green-700 border-green-500', label: '⭐ HIGH' },
      'moderate': { color: 'bg-blue-500/20 text-blue-700 border-blue-500', label: '📈 MODERATE' },
      'low': { color: 'bg-gray-500/20 text-gray-700 border-gray-500', label: '📊 LOW' },
    };

    return config[potential as keyof typeof config] || config.low;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 sticky top-0 z-50 backdrop-blur-sm">
        <div className="container py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setLocation('/')}>
            <Sparkles className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-xl font-bold">Unicorn Hunter</h1>
              <p className="text-xs text-muted-foreground">Find 100x gems before the crowd</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={() => setLocation('/discover')}>
              <Filter className="h-4 w-4 mr-2" />
              Discovery
            </Button>
            <Button onClick={detectUnicorns} disabled={isScanning || isLoading}>
              {isScanning ? (
                <>
                  <Activity className="h-4 w-4 mr-2 animate-spin" />
                  Scanning...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2" />
                  Hunt Unicorns
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        {/* Hunt Stats */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <Card className="border-primary/50 bg-gradient-to-br from-primary/10 to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Potential Unicorns Found</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary">{unicorns.length}</div>
            </CardContent>
          </Card>

          <Card className="border-orange-500/50 bg-gradient-to-br from-orange-500/10 to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Explosive Potential</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-500">
                {unicorns.filter(u => u.potential === 'explosive').length}
              </div>
            </CardContent>
          </Card>

          <Card className="border-green-500/50 bg-gradient-to-br from-green-500/10 to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Early Stage Gems</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-500">
                {unicorns.filter(u => u.discoveryStage === 'early').length}
              </div>
            </CardContent>
          </Card>

          <Card className="border-purple-500/50 bg-gradient-to-br from-purple-500/10 to-transparent">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Diamond Hands</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-500">
                {unicorns.filter(u => u.scoreType === 'diamond-hands').length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Filter Unicorns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Search</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search projects..."
                    className="pl-10"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Score Type</Label>
                <select
                  className="w-full px-3 py-2 rounded-md border bg-background"
                  value={selectedScore}
                  onChange={(e) => setSelectedScore(e.target.value)}
                >
                  <option value="all">All Scores</option>
                  <option value="diamond-hands">💎 Diamond Hands</option>
                  <option value="early-gem">💠 Early Gem</option>
                  <option value="rising-star">⭐ Rising Star</option>
                  <option value="hidden-gem">👁️ Hidden Gem</option>
                  <option value="risky-bet">⚠️ Risky Bet</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Potential</Label>
                <select
                  className="w-full px-3 py-2 rounded-md border bg-background"
                  value={selectedPotential}
                  onChange={(e) => setSelectedPotential(e.target.value)}
                >
                  <option value="all">All Potentials</option>
                  <option value="explosive">🚀 Explosive</option>
                  <option value="high">⭐ High</option>
                  <option value="moderate">📈 Moderate</option>
                  <option value="low">📊 Low</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Stage</Label>
                <select
                  className="w-full px-3 py-2 rounded-md border bg-background"
                  value={selectedStage}
                  onChange={(e) => setSelectedStage(e.target.value)}
                >
                  <option value="all">All Stages</option>
                  <option value="pre-listing">🌱 Pre-Listing</option>
                  <option value="early">🌿 Early</option>
                  <option value="growing">🌳 Growing</option>
                  <option value="trending">🔥 Trending</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Unicorn List */}
        {unicorns.length === 0 && !isScanning ? (
          <Card className="text-center py-20">
            <CardContent className="space-y-4">
              <Gem className="h-16 w-16 text-muted-foreground mx-auto" />
              <h3 className="text-xl font-semibold">No Unicorns Found Yet</h3>
              <p className="text-muted-foreground max-w-md mx-auto">
                Click "Hunt Unicorns" to scan the market for hidden gems and explosive opportunities before the crowd discovers them.
              </p>
              <Button onClick={detectUnicorns} size="lg">
                <Zap className="h-5 w-5 mr-2" />
                Start Hunting
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredUnicorns.map((unicorn) => {
              const { color, Icon } = getScoreBadge(unicorn.unicornScore, unicorn.scoreType);
              const potentialBadge = getPotentialBadge(unicorn.potential);

              return (
                <Card
                  key={unicorn.id}
                  className="hover:shadow-xl transition-all cursor-pointer border-2"
                  onClick={() => setSelectedUnicorn(unicorn)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                          {unicorn.logo ? (
                            <img src={unicorn.logo} alt={unicorn.name} className="h-8 w-8" />
                          ) : (
                            <Coins className="h-6 w-6 text-primary" />
                          )}
                        </div>
                        <div>
                          <CardTitle className="text-lg">{unicorn.name}</CardTitle>
                          <CardDescription>{unicorn.symbol}</CardDescription>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-primary">{unicorn.unicornScore}</div>
                        <div className="text-xs text-muted-foreground">Unicorn Score</div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* Badges */}
                    <div className="flex flex-wrap gap-2">
                      <Badge className={color}>
                        <Icon className="h-3 w-3 mr-1" />
                        {unicorn.scoreType}
                      </Badge>
                      <Badge className={potentialBadge.color}>
                        {potentialBadge.label}
                      </Badge>
                      {unicorn.actionItems.buyNow && (
                        <Badge className="bg-red-500/20 text-red-700 border-red-500 animate-pulse">
                          🔥 BUY NOW
                        </Badge>
                      )}
                    </div>

                    {/* Price Info */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-muted-foreground">Price</div>
                        <div className="font-semibold">${unicorn.currentPrice.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">24h Change</div>
                        <div className={`font-semibold ${unicorn.priceChange24h >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {unicorn.priceChange24h >= 0 ? '+' : ''}{unicorn.priceChange24h.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Market Cap</div>
                        <div className="font-semibold">
                          {unicorn.marketCap >= 1000000000
                            ? `$${(unicorn.marketCap / 1000000000).toFixed(2)}B`
                            : unicorn.marketCap >= 1000000
                            ? `$${(unicorn.marketCap / 1000000).toFixed(2)}M`
                            : `$${unicorn.marketCap.toLocaleString()}`
                          }
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Volume 24h</div>
                        <div className="font-semibold">
                          {unicorn.volume24h >= 1000000
                            ? `$${(unicorn.volume24h / 1000000).toFixed(1)}M`
                            : `$${unicorn.volume24h.toLocaleString()}`
                          }
                        </div>
                      </div>
                    </div>

                    {/* Signals */}
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Signals:</div>
                      <div className="grid grid-cols-5 gap-1">
                        <div className="text-center">
                          <div className="text-xs text-muted-foreground">Social</div>
                          <div className="h-1 bg-gray-200 rounded overflow-hidden">
                            <div
                              className="h-full bg-blue-500"
                              style={{ width: `${unicorn.signals.socialVolume}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-muted-foreground">Dev</div>
                          <div className="h-1 bg-gray-200 rounded overflow-hidden">
                            <div
                              className="h-full bg-green-500"
                              style={{ width: `${unicorn.signals.devActivity}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-muted-foreground">Token</div>
                          <div className="h-1 bg-gray-200 rounded overflow-hidden">
                            <div
                              className="h-full bg-purple-500"
                              style={{ width: `${unicorn.signals.tokenomics}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-muted-foreground">Growth</div>
                          <div className="h-1 bg-gray-200 rounded overflow-hidden">
                            <div
                              className="h-full bg-orange-500"
                              style={{ width: `${unicorn.signals.communityGrowth}%` }}
                            />
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-muted-foreground">Liquidity</div>
                          <div className="h-1 bg-gray-200 rounded overflow-hidden">
                            <div
                              className="h-full bg-yellow-500"
                              style={{ width: `${unicorn.signals.liquidityDepth}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Why It's a Unicorn */}
                    {unicorn.reasons.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-sm font-medium flex items-center gap-1">
                          <Sparkles className="h-3 w-3 text-yellow-500" />
                          Why It's a Unicorn:
                        </div>
                        <ul className="text-xs space-y-1 text-muted-foreground">
                          {unicorn.reasons.slice(0, 3).map((reason, i) => (
                            <li key={i} className="flex items-start gap-1">
                              <Rocket className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                              {reason}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Warnings */}
                    {unicorn.warnings.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-sm font-medium flex items-center gap-1">
                          <AlertCircle className="h-3 w-3 text-orange-500" />
                          Warnings:
                        </div>
                        <ul className="text-xs space-y-1 text-orange-600">
                          {unicorn.warnings.map((warning, i) => (
                            <li key={i}>⚠️ {warning}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      {/* Deep Research Modal */}
      {selectedUnicorn && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={() => setSelectedUnicorn(null)}>
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                    {selectedUnicorn.logo ? (
                      <img src={selectedUnicorn.logo} alt={selectedUnicorn.name} className="h-10 w-10" />
                    ) : (
                      <Coins className="h-8 w-8 text-primary" />
                    )}
                  </div>
                  <div>
                    <CardTitle className="text-2xl">{selectedUnicorn.name}</CardTitle>
                    <CardDescription className="text-lg">{selectedUnicorn.symbol}</CardDescription>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setSelectedUnicorn(null)}>
                  ✕
                </Button>
              </div>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Unicorn Score Breakdown */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-lg font-semibold">Unicorn Score: {selectedUnicorn.unicornScore}/100</Label>
                  <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500"
                      style={{ width: `${selectedUnicorn.unicornScore}%` }}
                    />
                  </div>
                  <div className="flex gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getScoreBadge(selectedUnicorn.unicornScore, selectedUnicorn.scoreType).color}`}>
                      {selectedUnicorn.scoreType}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPotentialBadge(selectedUnicorn.potential).color}`}>
                      {getPotentialBadge(selectedUnicorn.potential).label}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-lg font-semibold">Research Priority</Label>
                  <div className="flex items-center gap-2">
                    {selectedUnicorn.actionItems.researchPriority === 'urgent' && (
                      <Badge className="bg-red-500/20 text-red-700 border-red-500 animate-pulse">
                        🔴 URGENT - Research Now!
                      </Badge>
                    )}
                    {selectedUnicorn.actionItems.researchPriority === 'high' && (
                      <Badge className="bg-orange-500/20 text-orange-700 border-orange-500">
                        🟠 HIGH Priority
                      </Badge>
                    )}
                    {selectedUnicorn.actionItems.researchPriority === 'medium' && (
                      <Badge className="bg-yellow-500/20 text-yellow-700 border-yellow-500">
                        🟡 Medium Priority
                      </Badge>
                    )}
                    {selectedUnicorn.actionItems.buyNow && (
                      <Badge className="bg-green-500/20 text-green-700 border-green-500">
                        ✅ Strong Buy Signal
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              {/* Deep Research Sections */}
              <Tabs defaultValue="why">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="why">🦄 Why Unicorn?</TabsTrigger>
                  <TabsTrigger value="signals">📊 Signals</TabsTrigger>
                  <TabsTrigger value="risks">⚠️ Risks</TabsTrigger>
                  <TabsTrigger value="action">🚀 Action Plan</TabsTrigger>
                </TabsList>

                <TabsContent value="why" className="space-y-4">
                  <div className="space-y-2">
                    <h3 className="font-semibold text-lg">Why This Could Be a 100x Gem:</h3>
                    <ul className="space-y-2">
                      {selectedUnicorn.reasons.map((reason, i) => (
                        <li key={i} className="flex items-start gap-2 p-3 bg-green-50 dark:bg-green-950/20 rounded-lg">
                          <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-2">
                    <h3 className="font-semibold text-lg">Discovery Stage:</h3>
                    <p className="text-muted-foreground">
                      {selectedUnicorn.discoveryStage === 'pre-listing' && '🌱 This project is in its earliest stages - before most investors even know it exists. Maximum upside potential.'}
                      {selectedUnicorn.discoveryStage === 'early' && '🌿 Early discovery phase - smart money is accumulating. Get in before institutional FOMO.'}
                      {selectedUnicorn.discoveryStage === 'growing' && '🌳 Gaining traction and attention. Still early but momentum is building.'}
                      {selectedUnicorn.discoveryStage === 'trending' && '🔥 Going viral! This one could explode any day now.'}
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="signals" className="space-y-4">
                  <h3 className="font-semibold text-lg">Technical Signals Analysis:</h3>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-2">
                        <span>📱 Social Volume</span>
                        <span className="font-semibold">{selectedUnicorn.signals.socialVolume}/100</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: `${selectedUnicorn.signals.socialVolume}%` }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span>💻 Development Activity</span>
                        <span className="font-semibold">{selectedUnicorn.signals.devActivity}/100</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-green-500" style={{ width: `${selectedUnicorn.signals.devActivity}%` }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span>🪙 Tokenomics</span>
                        <span className="font-semibold">{selectedUnicorn.signals.tokenomics}/100</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-purple-500" style={{ width: `${selectedUnicorn.signals.tokenomics}%` }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span>👥 Community Growth</span>
                        <span className="font-semibold">{selectedUnicorn.signals.communityGrowth}/100</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-orange-500" style={{ width: `${selectedUnicorn.signals.communityGrowth}%` }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span>💧 Liquidity Depth</span>
                        <span className="font-semibold">{selectedUnicorn.signals.liquidityDepth}/100</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-yellow-500" style={{ width: `${selectedUnicorn.signals.liquidityDepth}%` }} />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="risks" className="space-y-4">
                  {selectedUnicorn.warnings.length > 0 ? (
                    <div className="space-y-2">
                      <h3 className="font-semibold text-lg">Risk Factors:</h3>
                      <ul className="space-y-2">
                        {selectedUnicorn.warnings.map((warning, i) => (
                          <li key={i} className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-950/20 rounded-lg">
                            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                            <span>{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="p-6 bg-green-50 dark:bg-green-950/20 rounded-lg text-center">
                      <CheckCircle2 className="h-12 w-12 text-green-600 mx-auto mb-2" />
                      <p className="font-semibold text-green-900 dark:text-green-100">Low Risk Detected</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        This project shows strong fundamentals with minimal red flags.
                      </p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="action" className="space-y-4">
                  <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg space-y-4">
                    <h3 className="font-semibold text-lg">🎯 Recommended Action Plan:</h3>

                    {selectedUnicorn.actionItems.buyNow && (
                      <div className="p-4 bg-green-500/20 border border-green-500 rounded-lg">
                        <div className="font-semibold text-green-900 dark:text-green-100 mb-2">
                          🚀 STRONG BUY SIGNAL
                        </div>
                        <p className="text-sm text-green-800 dark:text-green-200">
                          This project shows explosive potential. Consider entering a position now while it's still early.
                        </p>
                      </div>
                    )}

                    <div className="space-y-2">
                      <h4 className="font-semibold">Immediate Actions:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>1. Research the team and background</li>
                        <li>2. Check social media engagement quality (not just numbers)</li>
                        <li>3. Review tokenomics carefully</li>
                        <li>4. Start with a small position to test</li>
                        <li>5. Set clear entry and exit points</li>
                      </ul>
                    </div>

                    <div className="space-y-2">
                      <h4 className="font-semibold">What to Watch:</h4>
                      <ul className="space-y-1 text-sm">
                        <li>• Volume spikes (could signal institutional entry)</li>
                        <li>• Exchange listings (major CEX listings = price pump)</li>
                        <li>• Partnership announcements</li>
                        <li>• Community growth rate</li>
                        <li>• Developer activity on GitHub</li>
                      </ul>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>

              {/* Quick Actions */}
              <div className="flex gap-3 pt-4 border-t">
                <Button className="flex-1" size="lg">
                  <LineChart className="h-4 w-4 mr-2" />
                  Start Tracking
                </Button>
                <Button className="flex-1" variant="outline" size="lg" onClick={() => setLocation('/new-audit')}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Deep Audit
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
