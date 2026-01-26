import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Scale, Loader2, ArrowLeft, Plus, Trash2, Save, Check, X, GitCompare, Github, Coins, AlertTriangle, Users, TrendingUp } from "lucide-react";
import { Link, useParams, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState, useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

// Helper to parse query parameters
function useQuery() {
  const [location] = useLocation();
  return new URLSearchParams(location.split("?")[1] || "");
}

interface ProjectData {
  id: number;
  project: any;
  report: any;
}

interface ComparisonData {
  id: number;
  name: string;
  projectIds: number[];
  createdAt: Date;
  updatedAt: Date;
}

export default function Comparison() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const { id: comparisonId } = useParams<{ id: string }>();
  const [, setLocation] = useLocation();
  const query = useQuery();

  const [selectedProjectIds, setSelectedProjectIds] = useState<number[]>([]);
  const [projectsData, setProjectsData] = useState<ProjectData[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [comparisonName, setComparisonName] = useState("");

  // Load project IDs from query params on mount
  useEffect(() => {
    const idsFromQuery = query.getAll("ids").map((id) => parseInt(id)).filter((id) => !isNaN(id));
    if (idsFromQuery.length > 0 && !comparisonId) {
      setSelectedProjectIds(idsFromQuery);
    }
  }, []);

  // Fetch all user projects for selection
  const { data: userProjects, isLoading: isLoadingProjects } = trpc.project.list.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  // Fetch saved comparisons
  const { data: comparisons, isLoading: isLoadingComparisons, refetch: refetchComparisons } = trpc.comparison.list.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  // Fetch specific comparison if ID is provided
  const { data: comparisonData } = trpc.comparison.get.useQuery(
    { comparisonId: parseInt(comparisonId || "0") },
    { enabled: isAuthenticated && !!comparisonId }
  );

  const createComparisonMutation = trpc.comparison.create.useMutation({
    onSuccess: () => {
      toast.success("Comparison saved!");
      setSaveDialogOpen(false);
      setComparisonName("");
      refetchComparisons();
    },
    onError: (error) => {
      toast.error(`Failed to save: ${error.message}`);
    },
  });

  const deleteComparisonMutation = trpc.comparison.delete.useMutation({
    onSuccess: () => {
      toast.success("Comparison deleted");
      refetchComparisons();
      if (comparisonId) {
        setLocation("/comparison");
      }
    },
    onError: (error) => {
      toast.error(`Failed to delete: ${error.message}`);
    },
  });

  // Load comparison data when comparisonId changes
  useEffect(() => {
    if (comparisonData) {
      setSelectedProjectIds(comparisonData.projectIds);
      loadProjectsData(comparisonData.projectIds);
    }
  }, [comparisonData]);

  // Load projects data when selectedProjectIds changes
  useEffect(() => {
    if (selectedProjectIds.length > 0 && !comparisonId) {
      loadProjectsData(selectedProjectIds);
    }
  }, [selectedProjectIds]);

  const loadProjectsData = async (projectIds: number[]) => {
    setLoadingProjects(true);
    try {
      const promises = projectIds.map((id) =>
        fetch(`/api/trpc/project.getById?input=${encodeURIComponent(JSON.stringify({ id }))}`)
          .then((res) => res.json())
          .then((res) => res.result.data)
      );

      const results = await Promise.all(promises);
      setProjectsData(results.filter((r) => r?.project));
    } catch (error) {
      console.error("Failed to load projects:", error);
      toast.error("Failed to load some projects");
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleAddProject = (projectId: number) => {
    if (selectedProjectIds.includes(projectId)) {
      toast.error("Project already added to comparison");
      return;
    }
    if (selectedProjectIds.length >= 4) {
      toast.error("Maximum 4 projects can be compared at once");
      return;
    }
    setSelectedProjectIds([...selectedProjectIds, projectId]);
  };

  const handleRemoveProject = (projectId: number) => {
    setSelectedProjectIds(selectedProjectIds.filter((id) => id !== projectId));
    setProjectsData(projectsData.filter((p) => p.project.id !== projectId));
  };

  const handleSaveComparison = () => {
    if (!comparisonName.trim()) {
      toast.error("Please enter a name for this comparison");
      return;
    }
    if (selectedProjectIds.length < 2) {
      toast.error("Please select at least 2 projects to compare");
      return;
    }

    createComparisonMutation.mutate({
      name: comparisonName,
      projectIds: selectedProjectIds,
    });
  };

  const handleLoadComparison = (comp: ComparisonData) => {
    setLocation(`/comparison/${comp.id}`);
  };

  const handleDeleteComparison = (compId: number) => {
    if (confirm("Are you sure you want to delete this comparison?")) {
      deleteComparisonMutation.mutate({ comparisonId: compId });
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-500";
    if (score >= 60) return "text-blue-500";
    if (score >= 40) return "text-yellow-500";
    return "text-red-500";
  };

  const getRiskColor = (level?: string) => {
    switch (level) {
      case "low": return "bg-green-500/20 text-green-700 border-green-500/30";
      case "medium": return "bg-yellow-500/20 text-yellow-700 border-yellow-500/30";
      case "high": return "bg-orange-500/20 text-orange-700 border-orange-500/30";
      case "critical": return "bg-red-500/20 text-red-700 border-red-500/30";
      default: return "bg-gray-500/20 text-gray-700 border-gray-500/30";
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>Please sign in to use the comparison tool</CardDescription>
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 sticky top-0 z-50 backdrop-blur-sm">
        <div className="container py-4 flex items-center justify-between">
          <Link href="/dashboard">
            <div className="flex items-center gap-2 cursor-pointer">
              <Scale className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-bold">{APP_TITLE}</h1>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/discover">
              <Button variant="ghost">Discover</Button>
            </Link>
            <Link href="/watchlist">
              <Button variant="ghost">Watchlist</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        {/* Page Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold mb-2 flex items-center gap-3">
              <GitCompare className="h-8 w-8 text-primary" />
              Project Comparison
            </h2>
            <p className="text-muted-foreground">
              Compare multiple crypto projects side-by-side
            </p>
          </div>
          <div className="flex gap-2">
            {selectedProjectIds.length >= 2 && (
              <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Save className="h-4 w-4 mr-2" />
                    Save Comparison
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Save Comparison</DialogTitle>
                    <DialogDescription>
                      Give this comparison a name to save it for later
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <Input
                      placeholder="My Crypto Comparison"
                      value={comparisonName}
                      onChange={(e) => setComparisonName(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button onClick={handleSaveComparison} className="flex-1">
                        Save
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setSaveDialogOpen(false);
                          setComparisonName("");
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            )}
            <Link href="/dashboard">
              <Button variant="ghost">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
        </div>

        {/* Saved Comparisons */}
        {!comparisonId && comparisons && comparisons.length > 0 && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-lg">Saved Comparisons</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {comparisons.map((comp: ComparisonData) => (
                  <div
                    key={comp.id}
                    className="p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium">{comp.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          {comp.projectIds.length} projects
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive"
                        onClick={() => handleDeleteComparison(comp.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full"
                      onClick={() => handleLoadComparison(comp)}
                    >
                      <GitCompare className="h-4 w-4 mr-2" />
                      View
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Project Selector */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">Select Projects to Compare</CardTitle>
            <CardDescription>
              Choose 2-4 projects to compare side-by-side ({selectedProjectIds.length}/4 selected)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingProjects ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : !userProjects || userProjects.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No projects found. Create an audit first.
              </div>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                {userProjects
                  .filter((p) => p.status === "completed")
                  .map((project) => {
                    const isSelected = selectedProjectIds.includes(project.id);
                    return (
                      <div
                        key={project.id}
                        className={`p-3 border rounded-lg flex items-center justify-between transition-all ${
                          isSelected
                            ? "bg-primary/10 border-primary"
                            : "hover:bg-accent/50"
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{project.name}</p>
                          {project.description && (
                            <p className="text-xs text-muted-foreground truncate">
                              {project.description}
                            </p>
                          )}
                        </div>
                        {isSelected ? (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                            onClick={() => handleRemoveProject(project.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleAddProject(project.id)}
                            disabled={selectedProjectIds.length >= 4}
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    );
                  })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Comparison View */}
        {loadingProjects ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : projectsData.length < 2 ? (
          <Card className="text-center py-20">
            <CardContent className="space-y-4">
              <GitCompare className="h-16 w-16 text-muted-foreground mx-auto" />
              <h3 className="text-xl font-semibold">
                {projectsData.length === 0
                  ? "Select projects to compare"
                  : "Select at least 2 projects"}
              </h3>
              <p className="text-muted-foreground">
                Choose 2-4 completed audits from the list above to see a side-by-side comparison
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Overview Scores */}
            <Card>
              <CardHeader>
                <CardTitle>Overall Scores</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6" style={{ gridTemplateColumns: `repeat(${projectsData.length}, 1fr)` }}>
                  {projectsData.map(({ project, report }) => (
                    <div key={project.id} className="text-center">
                      <h3 className="font-semibold mb-3">{project.name}</h3>
                      <div className="text-4xl font-bold mb-2">
                        <span className={getScoreColor(report?.overallScore || 0)}>
                          {report?.overallScore || "N/A"}
                        </span>
                      </div>
                      <Badge className={getRiskColor(report?.riskLevel)}>
                        {report?.riskLevel || "Unknown"} risk
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Category Scores */}
            <Card>
              <CardHeader>
                <CardTitle>Category Scores</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {[
                  { key: "githubScore", label: "GitHub", icon: Github },
                  { key: "tokenomicsScore", label: "Tokenomics", icon: Coins },
                  { key: "contractRiskScore", label: "Contract Risk", icon: AlertTriangle },
                  { key: "twitterScore", label: "Twitter", icon: Users },
                  { key: "telegramScore", label: "Telegram", icon: TrendingUp },
                  { key: "discordScore", label: "Discord", icon: Users },
                ].map((category) => {
                  const maxScore = Math.max(
                    ...projectsData.map((p) => p.report?.[category.key] || 0),
                    1
                  );

                  return (
                    <div key={category.key} className="space-y-2">
                      <div className="flex items-center gap-2 font-medium">
                        <category.icon className="h-4 w-4" />
                        {category.label}
                      </div>
                      <div className="space-y-2">
                        {projectsData.map(({ project, report }) => {
                          const score = report?.[category.key] || 0;
                          const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0;

                          return (
                            <div key={project.id} className="space-y-1">
                              <div className="flex justify-between text-sm">
                                <span className="truncate flex-1">{project.name}</span>
                                <span className={`font-medium ${getScoreColor(score)}`}>
                                  {score || "N/A"}
                                </span>
                              </div>
                              <Progress value={score} className="h-2" />
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            {/* Project Details */}
            <Card>
              <CardHeader>
                <CardTitle>Project Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-3 font-medium">Attribute</th>
                        {projectsData.map(({ project }) => (
                          <th key={project.id} className="text-left p-3 font-medium">
                            {project.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b">
                        <td className="p-3 text-muted-foreground">Description</td>
                        {projectsData.map(({ project }) => (
                          <td key={project.id} className="p-3">
                            {project.description || "-"}
                          </td>
                        ))}
                      </tr>
                      <tr className="border-b">
                        <td className="p-3 text-muted-foreground">Chain</td>
                        {projectsData.map(({ project }) => (
                          <td key={project.id} className="p-3">
                            <Badge variant="outline">{project.chain || "N/A"}</Badge>
                          </td>
                        ))}
                      </tr>
                      <tr className="border-b">
                        <td className="p-3 text-muted-foreground">Status</td>
                        {projectsData.map(({ project }) => (
                          <td key={project.id} className="p-3">
                            <Badge>{project.status}</Badge>
                          </td>
                        ))}
                      </tr>
                      <tr>
                        <td className="p-3 text-muted-foreground">Created</td>
                        {projectsData.map(({ project }) => (
                          <td key={project.id} className="p-3 text-sm">
                            {new Date(project.createdAt).toLocaleDateString()}
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <div className="flex gap-2">
              {projectsData.map(({ project }) => (
                <Link key={project.id} href={`/audit/${project.id}`}>
                  <Button variant="outline" className="flex-1">
                    View {project.name} Details
                  </Button>
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
