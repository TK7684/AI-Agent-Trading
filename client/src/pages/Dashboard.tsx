import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Plus, Loader2, AlertCircle, CheckCircle, Clock, XCircle, GitCompare } from "lucide-react";
import { Link, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { useState } from "react";

export default function Dashboard() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [, setLocation] = useLocation();
  const [selectedProjects, setSelectedProjects] = useState<number[]>([]);

  const { data: projects, isLoading, error } = trpc.project.list.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  const toggleProjectSelection = (projectId: number) => {
    if (selectedProjects.includes(projectId)) {
      setSelectedProjects(selectedProjects.filter((id) => id !== projectId));
    } else if (selectedProjects.length < 4) {
      setSelectedProjects([...selectedProjects, projectId]);
    }
  };

  const handleCompare = () => {
    if (selectedProjects.length >= 2) {
      // Build URL with selected project IDs
      const params = new URLSearchParams();
      selectedProjects.forEach((id) => params.append("ids", id.toString()));
      setLocation(`/comparison?${params.toString()}`);
    }
  };

  if (authLoading) {
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
            <CardDescription>Please sign in to view your dashboard</CardDescription>
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "analyzing":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      analyzing: "secondary",
      failed: "destructive",
      pending: "outline",
    };
    return (
      <Badge variant={variants[status] || "outline"} className="capitalize">
        {status}
      </Badge>
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
          <div className="flex items-center gap-4">
            <Link href="/discover">
              <Button variant="ghost">Discover</Button>
            </Link>
            <span className="text-sm text-muted-foreground hidden sm:inline" data-testid="user-name">
              {user?.name || user?.email}
            </span>
            <Link href="/new-audit">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Audit
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold mb-2">Your Audits</h2>
            <p className="text-muted-foreground">
              Manage and review your crypto project audits
            </p>
          </div>
          {selectedProjects.length > 0 && (
            <Button onClick={handleCompare} disabled={selectedProjects.length < 2}>
              <GitCompare className="h-4 w-4 mr-2" />
              Compare {selectedProjects.length} project{selectedProjects.length > 1 ? "s" : ""}
            </Button>
          )}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <Card className="border-destructive">
            <CardContent className="flex items-center gap-4 py-8">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <div>
                <h3 className="font-semibold">Error loading projects</h3>
                <p className="text-sm text-muted-foreground">{error.message}</p>
              </div>
            </CardContent>
          </Card>
        ) : !projects || projects.length === 0 ? (
          <Card className="text-center py-20">
            <CardContent className="space-y-4">
              <Shield className="h-16 w-16 text-muted-foreground mx-auto" />
              <h3 className="text-xl font-semibold">No audits yet</h3>
              <p className="text-muted-foreground">
                Create your first crypto project audit to get started
              </p>
              <Link href="/new-audit">
                <Button size="lg" className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Audit
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => {
                const isSelected = selectedProjects.includes(project.id);
                const canSelect = project.status === "completed" && selectedProjects.length < 4;

                return (
                  <Card
                    key={project.id}
                    className={`hover:shadow-lg transition-all relative ${
                      isSelected ? "ring-2 ring-primary" : ""
                    }`}
                  >
                    {/* Compare Checkbox */}
                    {project.status === "completed" && (
                      <div className="absolute top-3 right-3 z-10">
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleProjectSelection(project.id)}
                          disabled={!canSelect && !isSelected}
                          className="bg-background"
                        />
                      </div>
                    )}

                    <CardHeader
                      className={`cursor-pointer ${isSelected ? "pr-12" : ""}`}
                      onClick={(e) => {
                        // Prevent navigation if clicking checkbox
                        if (!(e.target as HTMLElement).closest('.comparison-checkbox')) {
                          setLocation(`/audit/${project.id}`);
                        }
                      }}
                    >
                      <div className="flex items-start justify-between pr-8">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(project.status)}
                          <CardTitle className="text-lg">{project.name}</CardTitle>
                        </div>
                        {getStatusBadge(project.status)}
                      </div>
                      {project.description && (
                        <CardDescription className="line-clamp-2">
                          {project.description}
                        </CardDescription>
                      )}
                    </CardHeader>
                    <CardContent
                      className="space-y-2 cursor-pointer"
                      onClick={() => setLocation(`/audit/${project.id}`)}
                    >
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                        {project.githubUrl && (
                          <Badge variant="outline" className="text-xs">
                            GitHub
                          </Badge>
                        )}
                        {project.contractAddress && (
                          <Badge variant="outline" className="text-xs">
                            Contract
                          </Badge>
                        )}
                        {project.twitterUrl && (
                          <Badge variant="outline" className="text-xs">
                            Twitter
                          </Badge>
                        )}
                        {project.telegramUrl && (
                          <Badge variant="outline" className="text-xs">
                            Telegram
                          </Badge>
                        )}
                        {project.discordUrl && (
                          <Badge variant="outline" className="text-xs">
                            Discord
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground pt-2">
                        Created {new Date(project.createdAt).toLocaleDateString()}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Floating Action Button for Comparison */}
            {selectedProjects.length >= 2 && (
              <div className="fixed bottom-6 right-6 z-50">
                <Button
                  size="lg"
                  onClick={handleCompare}
                  className="shadow-lg"
                >
                  <GitCompare className="h-5 w-5 mr-2" />
                  Compare {selectedProjects.length} Projects
                </Button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
