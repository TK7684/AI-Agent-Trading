import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Loader2, ArrowLeft, Github, Coins, AlertTriangle, Users, TrendingUp, ExternalLink, RefreshCw, Download, FileJson, FileText } from "lucide-react";
import { Link, useParams } from "wouter";
import { trpc } from "@/lib/trpc";
import { Streamdown } from "streamdown";
import { toast } from "sonner";
import { downloadJSON, downloadPDF, generateFilename } from "@/lib/export";
import { useState } from "react";

export default function AuditDetail() {
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, loading: authLoading } = useAuth();
  
  const { data, isLoading, error, refetch } = trpc.project.getById.useQuery(
    { id: parseInt(id || "0") },
    { enabled: isAuthenticated && !!id }
  );

  const analyzeMutation = trpc.project.analyze.useMutation({
    onSuccess: () => {
      toast.success("Analysis restarted!");
      refetch();
    },
    onError: (error) => {
      toast.error(`Failed to restart analysis: ${error.message}`);
    },
  });

  const [isExporting, setIsExporting] = useState(false);

  const handleExportJSON = async () => {
    setIsExporting(true);
    try {
      const response = await fetch(
        `/api/trpc/export.json?input=${encodeURIComponent(JSON.stringify({ projectId: project.id }))}`
      );
      if (!response.ok) throw new Error("Export failed");
      const data = await response.json();
      downloadJSON(data.result.data.json, generateFilename(project.name, "json"));
      toast.success("Exported to JSON");
    } catch (error: any) {
      toast.error(`Failed to export: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      const response = await fetch(
        `/api/trpc/export.pdf?input=${encodeURIComponent(JSON.stringify({ projectId: project.id }))}`
      );
      if (!response.ok) throw new Error("Export failed");
      const data = await response.json();
      downloadPDF(data.result.data.pdfBase64, generateFilename(project.name, "pdf"));
      toast.success("Exported to PDF");
    } catch (error: any) {
      toast.error(`Failed to export: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>Please sign in to view audit details</CardDescription>
          </CardHeader>
          <CardContent>
            <a href={getLoginUrl()}>
              <Button className="w-full">Sign In</Button>
            </a>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !data || !data.project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Project Not Found</CardTitle>
            <CardDescription>
              {error?.message || "The requested audit could not be found"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard">
              <Button className="w-full">Back to Dashboard</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { project, report } = data;

  const getRiskColor = (level?: string) => {
    switch (level) {
      case "low": return "text-green-500";
      case "medium": return "text-yellow-500";
      case "high": return "text-orange-500";
      case "critical": return "text-red-500";
      default: return "text-muted-foreground";
    }
  };

  const getRiskBadge = (level?: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      low: "default",
      medium: "secondary",
      high: "destructive",
      critical: "destructive",
    };
    return (
      <Badge variant={variants[level || ""] || "outline"} className="capitalize">
        {level || "N/A"}
      </Badge>
    );
  };

  const ScoreCard = ({ title, score, icon: Icon, data }: { title: string; score: number | null; icon: any; data?: string }) => {
    const parsedData = data ? JSON.parse(data) : null;
    
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">{title}</CardTitle>
            </div>
            <span className="text-2xl font-bold">{score !== null ? score : "—"}</span>
          </div>
        </CardHeader>
        <CardContent>
          {score !== null && (
            <>
              <Progress value={score} className="mb-4" />
              {parsedData?.analysis && (
                <div className="text-sm text-muted-foreground mt-4 prose prose-sm max-w-none">
                  <Streamdown>{parsedData.analysis}</Streamdown>
                </div>
              )}
              {parsedData?.issues && parsedData.issues.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold mb-2 text-destructive">Issues:</h4>
                  <ul className="text-sm space-y-1">
                    {parsedData.issues.map((issue: string, i: number) => (
                      <li key={i} className="text-muted-foreground">• {issue}</li>
                    ))}
                  </ul>
                </div>
              )}
              {parsedData?.strengths && parsedData.strengths.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold mb-2 text-green-600">Strengths:</h4>
                  <ul className="text-sm space-y-1">
                    {parsedData.strengths.map((strength: string, i: number) => (
                      <li key={i} className="text-muted-foreground">• {strength}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
          {score === null && (
            <p className="text-sm text-muted-foreground">No data available</p>
          )}
        </CardContent>
      </Card>
    );
  };

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
          <div className="flex items-center gap-2">
            {project.status === "completed" && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportJSON}
                  disabled={isExporting}
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FileJson className="h-4 w-4 mr-2" />
                  )}
                  JSON
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportPDF}
                  disabled={isExporting}
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4 mr-2" />
                  )}
                  PDF
                </Button>
              </>
            )}
            <Link href="/dashboard">
              <Button variant="ghost">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        {/* Project Header */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-3xl font-bold mb-2">{project.name}</h2>
              {project.description && (
                <p className="text-muted-foreground">{project.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={project.status === "completed" ? "default" : "secondary"} className="capitalize">
                {project.status}
              </Badge>
              {(project.status === "failed" || project.status === "completed") && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => analyzeMutation.mutate({ projectId: project.id })}
                  disabled={analyzeMutation.isPending}
                >
                  {analyzeMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Re-analyze
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>

          {/* Project Links */}
          <div className="flex flex-wrap gap-2">
            {project.githubUrl && (
              <a href={project.githubUrl} target="_blank" rel="noopener noreferrer">
                <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                  GitHub <ExternalLink className="h-3 w-3 ml-1" />
                </Badge>
              </a>
            )}
            {project.websiteUrl && (
              <a href={project.websiteUrl} target="_blank" rel="noopener noreferrer">
                <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                  Website <ExternalLink className="h-3 w-3 ml-1" />
                </Badge>
              </a>
            )}
            {project.twitterUrl && (
              <a href={project.twitterUrl} target="_blank" rel="noopener noreferrer">
                <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                  Twitter <ExternalLink className="h-3 w-3 ml-1" />
                </Badge>
              </a>
            )}
            {project.telegramUrl && (
              <a href={project.telegramUrl} target="_blank" rel="noopener noreferrer">
                <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                  Telegram <ExternalLink className="h-3 w-3 ml-1" />
                </Badge>
              </a>
            )}
            {project.discordUrl && (
              <a href={project.discordUrl} target="_blank" rel="noopener noreferrer">
                <Badge variant="outline" className="cursor-pointer hover:bg-accent">
                  Discord <ExternalLink className="h-3 w-3 ml-1" />
                </Badge>
              </a>
            )}
          </div>
        </div>

        {/* Overall Score */}
        {report && report.overallScore !== null && (
          <Card className="mb-8 bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
            <CardContent className="p-8">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold mb-2">Overall Security Score</h3>
                  <div className="flex items-center gap-4">
                    <span className="text-5xl font-bold">{report.overallScore}</span>
                    <div>
                      <p className="text-muted-foreground">Risk Level:</p>
                      <div className={`text-xl font-semibold ${getRiskColor(report.riskLevel || undefined)}`}>
                        {getRiskBadge(report.riskLevel || undefined)}
                      </div>
                    </div>
                  </div>
                </div>
                <TrendingUp className="h-24 w-24 text-primary opacity-20" />
              </div>
              <Progress value={report.overallScore} className="mt-6 h-3" />
            </CardContent>
          </Card>
        )}

        {/* AI Analysis Summary */}
        {report?.aiAnalysis && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                AI Analysis Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="prose prose-sm max-w-none">
              <Streamdown>{report.aiAnalysis}</Streamdown>
            </CardContent>
          </Card>
        )}

        {/* Detailed Scores */}
        <div className="space-y-6">
          <h3 className="text-2xl font-bold">Detailed Analysis</h3>
          
          <div className="grid gap-6 md:grid-cols-2">
            <ScoreCard
              title="GitHub Analysis"
              score={report?.githubScore || null}
              icon={Github}
              data={report?.githubData || undefined}
            />
            
            <ScoreCard
              title="Tokenomics"
              score={report?.tokenomicsScore || null}
              icon={Coins}
              data={report?.tokenomicsData || undefined}
            />
            
            <ScoreCard
              title="Contract Risk"
              score={report?.contractRiskScore || null}
              icon={AlertTriangle}
              data={report?.contractRiskData || undefined}
            />
            
            <ScoreCard
              title="Twitter/X"
              score={report?.twitterScore || null}
              icon={Users}
              data={report?.twitterData || undefined}
            />
            
            <ScoreCard
              title="Telegram"
              score={report?.telegramScore || null}
              icon={Users}
              data={report?.telegramData || undefined}
            />
            
            <ScoreCard
              title="Discord"
              score={report?.discordScore || null}
              icon={Users}
              data={report?.discordData || undefined}
            />
          </div>
        </div>

        {/* Analyzing State */}
        {project.status === "analyzing" && (
          <Card className="mt-8 border-primary/50 bg-primary/5">
            <CardContent className="flex items-center gap-4 py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <div>
                <h3 className="font-semibold">Analysis in Progress</h3>
                <p className="text-sm text-muted-foreground">
                  This may take a few minutes. The page will update automatically.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
