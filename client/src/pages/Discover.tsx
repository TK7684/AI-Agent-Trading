import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Loader2, TrendingUp, ExternalLink, Github, Twitter, Globe, MessageCircle, Star } from "lucide-react";
import { Link, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState } from "react";

export default function Discover() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [, setLocation] = useLocation();
  const [creatingProjectId, setCreatingProjectId] = useState<string | null>(null);
  
  const { data: projects, isLoading, error, refetch } = trpc.discovery.trending.useQuery();

  // Removed createMutation - will be added in next phase

  const analyzeMutation = trpc.project.analyze.useMutation({
    onSuccess: (data, variables) => {
      toast.success("Analysis started!");
      setLocation(`/audit/${variables.projectId}`);
      setCreatingProjectId(null);
    },
    onError: (error) => {
      toast.error(`Failed to start analysis: ${error.message}`);
      setCreatingProjectId(null);
    },
  });

  const handleAuditProject = (project: any) => {
    if (!isAuthenticated) {
      toast.error("Please sign in to audit projects");
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
                  <Button variant="ghost">Dashboard</Button>
                </Link>
              </>
            ) : (
              <a href={getLoginUrl()}>
                <Button>Sign In</Button>
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
            AI-Curated Projects
          </div>
          <h2 className="text-4xl font-bold mb-4">Discover Trending Crypto Projects</h2>
          <p className="text-muted-foreground text-lg">
            Explore top cryptocurrency projects ranked by our AI recommendation system. 
            Click "Audit Project" to get a comprehensive security analysis.
          </p>
        </div>

        {/* Filters & Actions */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-sm">
              {projects?.length || 0} Projects Found
            </Badge>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Refresh"
            )}
          </Button>
        </div>

        {/* Projects Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <Card className="border-destructive">
            <CardContent className="flex items-center gap-4 py-8">
              <div>
                <h3 className="font-semibold">Error loading projects</h3>
                <p className="text-sm text-muted-foreground">{error.message}</p>
              </div>
            </CardContent>
          </Card>
        ) : !projects || projects.length === 0 ? (
          <Card className="text-center py-20">
            <CardContent>
              <TrendingUp className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold">No projects found</h3>
              <p className="text-muted-foreground">Try refreshing to load trending projects</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card key={project.id} className="hover:shadow-lg transition-all hover:border-primary/50" data-testid="project-card">
                <CardHeader>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <CardTitle className="text-xl">{project.name}</CardTitle>
                        <Badge variant="secondary" className="text-xs">
                          {project.symbol}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>Rank #{project.rank}</span>
                        <span>•</span>
                        <span
                          className={project.priceChange24h >= 0 ? "text-green-500" : "text-red-500"}
                          data-testid="price-change"
                        >
                          {project.priceChange24h >= 0 ? "+" : ""}
                          {project.priceChange24h.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <div className={`text-2xl font-bold ${getScoreColor(project.recommendationScore)}`}>
                        {project.recommendationScore}
                      </div>
                      <div className="flex items-center gap-1">
                        <Star className="h-3 w-3 fill-current" />
                        <span className="text-xs text-muted-foreground">Score</span>
                      </div>
                    </div>
                  </div>
                  
                  <CardDescription className="line-clamp-3 text-sm">
                    {project.description}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-4">
                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <div className="text-muted-foreground text-xs">Market Cap</div>
                      <div className="font-semibold">{formatNumber(project.marketCap)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">24h Volume</div>
                      <div className="font-semibold">{formatNumber(project.volume24h)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">Price</div>
                      <div className="font-semibold">{formatNumber(project.price)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground text-xs">Category</div>
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
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <Globe className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.githubUrl && (
                      <a href={project.githubUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <Github className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.twitterUrl && (
                      <a href={project.twitterUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <Twitter className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                    {project.telegramUrl && (
                      <a href={project.telegramUrl} target="_blank" rel="noopener noreferrer">
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MessageCircle className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                  </div>

                  {/* Action Button */}
                  <Button
                    className="w-full"
                    onClick={() => handleAuditProject(project)}
                    disabled={creatingProjectId === project.id || !isAuthenticated}
                    data-testid="audit-button"
                  >
                    {creatingProjectId === project.id ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Shield className="h-4 w-4 mr-2" />
                        Audit This Project
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* CTA Section */}
        {!isAuthenticated && (
          <Card className="mt-12 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
            <CardContent className="p-8 text-center space-y-4">
              <h3 className="text-2xl font-bold">Sign In to Audit Projects</h3>
              <p className="text-muted-foreground">
                Create an account to start auditing crypto projects and making informed investment decisions
              </p>
              <a href={getLoginUrl()}>
                <Button size="lg">
                  Sign In Now
                </Button>
              </a>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
