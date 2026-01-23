import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Loader2, TrendingUp, ExternalLink, Github, Twitter, Globe, MessageCircle, Star, Filter, X } from "lucide-react";
import { Link, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState, useMemo } from "react";
import { thaiTranslations as t } from "@/i18n/th";

export default function DiscoverV2() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [, setLocation] = useLocation();
  const [creatingProjectId, setCreatingProjectId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filters state
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [minScore, setMinScore] = useState<number>(0);
  
  const { data: projects, isLoading, error, refetch } = trpc.discovery.trending.useQuery({
    category: selectedCategory || undefined,
    status: (selectedStatus as any) || undefined,
    minScore: minScore > 0 ? minScore : undefined,
  });

  const { data: categories } = trpc.discovery.getCategories.useQuery();
  const sendNotificationMutation = trpc.discovery.sendNotification.useMutation({
    onSuccess: () => {
      toast.success("Send notification to your email successfully!");
    },
    onError: (error) => {
      toast.error(`Failed to send notification: ${error.message}`);
    },
  });

  // Removed createMutation - will be added in next phase

  const analyzeMutation = trpc.project.analyze.useMutation({
    onSuccess: (data, variables) => {
      toast.success("วิเคราะห์เริ่มต้นแล้ว!");
      setLocation(`/audit/${variables.projectId}`);
      setCreatingProjectId(null);
    },
    onError: (error) => {
      toast.error(`${t.notifications.analysisFailed}: ${error.message}`);
      setCreatingProjectId(null);
    },
  });

  const handleAuditProject = (project: any) => {
    if (!isAuthenticated) {
      toast.error(t.discover.signInTip);
      return;
    }

    setCreatingProjectId(project.id);
    // TODO: Create project mutation will be added in next phase
    // For now, just navigate to audit page
    setLocation(`/audit/${project.id}`);
    setCreatingProjectId(null);
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000000) return `$${(num / 1000000000).toFixed(2)}B`;
    if (num >= 1000000) return `$${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500";
    if (score >= 60) return "text-blue-500";
    if (score >= 40) return "text-yellow-500";
    return "text-red-500";
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "hot": return "bg-red-500/20 text-red-700";
      case "new": return "bg-blue-500/20 text-blue-700";
      case "trending": return "bg-purple-500/20 text-purple-700";
      default: return "bg-gray-500/20 text-gray-700";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "hot": return "🔥 ร้อน";
      case "new": return "✨ ใหม่";
      case "trending": return "📈 ยอดนิยม";
      default: return "✓ ที่ยอมรับ";
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 sticky top-0 z-50 backdrop-blur-sm">
        <div className="container py-4 flex items-center justify-between">
          <Link href="/">
            <div className="flex items-center gap-2 cursor-pointer">
              <Shield className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-bold">{APP_TITLE}</h1>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-muted-foreground hidden sm:inline">
                  {user?.name || user?.email}
                </span>
                <Link href="/dashboard">
                  <Button variant="ghost">{t.header.dashboard}</Button>
                </Link>
              </>
            ) : (
              <a href={getLoginUrl()}>
                <Button>{t.header.signIn}</Button>
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        {/* Hero Section */}
        <div className="mb-8 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
            <TrendingUp className="h-4 w-4" />
            {t.discover.aiCurated}
          </div>
          <h2 className="text-4xl font-bold mb-4">{t.discover.title}</h2>
          <p className="text-muted-foreground text-lg">
            {t.discover.subtitle}
          </p>
        </div>

        {/* Filters & Actions */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-sm">
              {projects?.length || 0} {t.discover.projectsFound}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              {t.filters.title}
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => refetch()} 
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                t.discover.refresh
              )}
            </Button>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <Card className="mb-6 bg-muted/50">
            <CardContent className="pt-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Category Filter */}
                <div>
                  <label className="text-sm font-medium mb-2 block">{t.filters.category}</label>
                  <select 
                    value={selectedCategory || ""} 
                    onChange={(e) => setSelectedCategory(e.target.value || null)}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="">{t.filters.allCategories}</option>
                    {categories?.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                {/* Status Filter */}
                <div>
                  <label className="text-sm font-medium mb-2 block">{t.filters.status}</label>
                  <select 
                    value={selectedStatus || ""} 
                    onChange={(e) => setSelectedStatus(e.target.value || null)}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="">{t.filters.allCategories}</option>
                    <option value="hot">{t.filters.hot}</option>
                    <option value="new">{t.filters.new}</option>
                    <option value="trending">{t.filters.trending}</option>
                    <option value="established">{t.filters.established}</option>
                  </select>
                </div>

                {/* Score Filter */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    {t.filters.minScore}: {minScore}
                  </label>
                  <input 
                    type="range" 
                    min="0" 
                    max="100" 
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="w-full"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  onClick={() => refetch()}
                >
                  {t.filters.apply}
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => {
                    setSelectedCategory(null);
                    setSelectedStatus(null);
                    setMinScore(0);
                  }}
                >
                  {t.filters.reset}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Projects Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <Card className="border-destructive">
            <CardContent className="flex items-center gap-4 py-8">
              <div>
                <h3 className="font-semibold">{t.status.error}</h3>
                <p className="text-sm text-muted-foreground">{error.message}</p>
              </div>
            </CardContent>
          </Card>
        ) : !projects || projects.length === 0 ? (
          <Card className="text-center py-20">
            <CardContent>
              <TrendingUp className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold">{t.discover.noProjects}</h3>
              <p className="text-muted-foreground">{t.discover.tryRefreshing}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card key={project.id} className="hover:shadow-lg transition-all hover:border-primary/50 flex flex-col">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <CardTitle className="text-xl">{project.name}</CardTitle>
                        <Badge variant="secondary" className="text-xs">
                          {project.symbol}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <span>อันดับ #{project.rank}</span>
                        <span>•</span>
                        <span className={project.priceChange24h >= 0 ? "text-green-500" : "text-red-500"}>
                          {project.priceChange24h >= 0 ? "+" : ""}
                          {project.priceChange24h.toFixed(2)}%
                        </span>
                      </div>
                      <Badge className={`text-xs ${getStatusBadgeColor(project.status)}`}>
                        {getStatusLabel(project.status)}
                      </Badge>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <div className={`text-2xl font-bold ${getScoreColor(project.recommendationScore)}`}>
                        {project.recommendationScore}
                      </div>
                      <div className="flex items-center gap-1">
                        <Star className="h-3 w-3 fill-current" />
                        <span className="text-xs text-muted-foreground">คะแนน</span>
                      </div>
                    </div>
                  </div>
                  
                  <CardDescription className="line-clamp-2 text-sm">
                    {project.briefSummary || project.description}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-4 flex-1 flex flex-col">
                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground text-xs">มูลค่าตลาด</div>
                      <div className="font-semibold">{formatNumber(project.marketCap)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">ปริมาณ 24 ชม.</div>
                      <div className="font-semibold">{formatNumber(project.volume24h)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">ราคา</div>
                      <div className="font-semibold">{formatNumber(project.price)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">หมวดหมู่</div>
                      <div className="font-semibold text-xs truncate">{project.category}</div>
                    </div>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1">
                    {project.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  {/* Links */}
                  <div className="flex items-center gap-2 pt-2 border-t">
                    {project.website && (
                      <a href={project.website} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Website">
                          <Globe className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.githubUrl && (
                      <a href={project.githubUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="GitHub">
                          <Github className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.twitterUrl && (
                      <a href={project.twitterUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Twitter">
                          <Twitter className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.telegramUrl && (
                      <a href={project.telegramUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0" title="Telegram">
                          <MessageCircle className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2 mt-auto">
                    <Button 
                      className="flex-1" 
                      onClick={() => handleAuditProject(project)}
                      disabled={creatingProjectId === project.id || !isAuthenticated}
                    >
                      {creatingProjectId === project.id ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          {t.discover.creating}
                        </>
                      ) : (
                        <>
                          <Shield className="h-4 w-4 mr-2" />
                          {t.discover.auditThis}
                        </>
                      )}
                    </Button>
                    <Button 
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (isAuthenticated) {
                          sendNotificationMutation.mutate({
                            projectId: project.id,
                            projectName: project.name,
                            projectSymbol: project.symbol,
                            score: project.recommendationScore,
                            category: project.category,
                            marketCap: project.marketCap,
                            priceChange24h: project.priceChange24h,
                            briefSummary: project.briefSummary || project.description,
                            tags: project.tags,
                          });
                        } else {
                          toast.error(t.discover.signInTip);
                        }
                      }}
                      disabled={!isAuthenticated}
                      title="Send notification to email"
                    >
                      📧
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* CTA Section */}
        {!isAuthenticated && (
          <Card className="mt-12 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
            <CardContent className="p-8 text-center space-y-4">
              <h3 className="text-2xl font-bold">{t.discover.readyToAudit}</h3>
              <p className="text-muted-foreground">
                {t.discover.joinThousands}
              </p>
              <a href={getLoginUrl()}>
                <Button size="lg">
                  {t.discover.signInNow}
                </Button>
              </a>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
