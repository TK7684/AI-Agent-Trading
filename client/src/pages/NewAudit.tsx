import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Loader2, ArrowLeft } from "lucide-react";
import { Link, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { useState } from "react";
import { toast } from "sonner";

export default function NewAudit() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [, setLocation] = useLocation();
  
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    githubUrl: "",
    contractAddress: "",
    chain: "ethereum",
    websiteUrl: "",
    twitterUrl: "",
    telegramUrl: "",
    discordUrl: "",
  });

  const createMutation = trpc.project.create.useMutation({
    onSuccess: (data) => {
      toast.success("Project created successfully!");
      // Start analysis immediately
      analyzeMutation.mutate({ projectId: Number(data.projectId) });
    },
    onError: (error) => {
      toast.error(`Failed to create project: ${error.message}`);
    },
  });

  const analyzeMutation = trpc.project.analyze.useMutation({
    onSuccess: (data, variables) => {
      toast.success("Analysis started!");
      setLocation(`/audit/${variables.projectId}`);
    },
    onError: (error) => {
      toast.error(`Failed to start analysis: ${error.message}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error("Project name is required");
      return;
    }

    if (!formData.githubUrl && !formData.contractAddress) {
      toast.error("Please provide at least GitHub URL or Contract Address");
      return;
    }

    createMutation.mutate(formData);
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
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
            <CardDescription>Please sign in to create an audit</CardDescription>
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

  const isLoading = createMutation.isPending || analyzeMutation.isPending;

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
          <Link href="/dashboard">
            <Button variant="ghost">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8 max-w-3xl">
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-2">Create New Audit</h2>
          <p className="text-muted-foreground">
            Provide project information to start a comprehensive security audit
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle>Project Information</CardTitle>
              <CardDescription>
                Fill in the details about the crypto project you want to audit
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Project Name *</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Awesome DeFi Protocol"
                    value={formData.name}
                    onChange={(e) => handleChange("name", e.target.value)}
                    required
                    data-testid="project-name"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Brief description of the project..."
                    value={formData.description}
                    onChange={(e) => handleChange("description", e.target.value)}
                    rows={3}
                  />
                </div>
              </div>

              {/* Code & Contract */}
              <div className="space-y-4 pt-4 border-t">
                <h3 className="font-semibold">Code & Smart Contract</h3>
                
                <div className="space-y-2">
                  <Label htmlFor="githubUrl">GitHub Repository URL</Label>
                  <Input
                    id="githubUrl"
                    type="url"
                    placeholder="https://github.com/username/repo"
                    value={formData.githubUrl}
                    onChange={(e) => handleChange("githubUrl", e.target.value)}
                    data-testid="github-url"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="contractAddress">Contract Address</Label>
                    <Input
                      id="contractAddress"
                      placeholder="0x..."
                      value={formData.contractAddress}
                      onChange={(e) => handleChange("contractAddress", e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="chain">Blockchain</Label>
                    <Select value={formData.chain} onValueChange={(value) => handleChange("chain", value)}>
                      <SelectTrigger id="chain">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="ethereum">Ethereum</SelectItem>
                        <SelectItem value="bsc">Binance Smart Chain</SelectItem>
                        <SelectItem value="polygon">Polygon</SelectItem>
                        <SelectItem value="arbitrum">Arbitrum</SelectItem>
                        <SelectItem value="optimism">Optimism</SelectItem>
                        <SelectItem value="avalanche">Avalanche</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Social Media */}
              <div className="space-y-4 pt-4 border-t">
                <h3 className="font-semibold">Social Media & Community</h3>
                
                <div className="space-y-2">
                  <Label htmlFor="websiteUrl">Website URL</Label>
                  <Input
                    id="websiteUrl"
                    type="url"
                    placeholder="https://example.com"
                    value={formData.websiteUrl}
                    onChange={(e) => handleChange("websiteUrl", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="twitterUrl">Twitter/X URL</Label>
                  <Input
                    id="twitterUrl"
                    type="url"
                    placeholder="https://twitter.com/username"
                    value={formData.twitterUrl}
                    onChange={(e) => handleChange("twitterUrl", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="telegramUrl">Telegram URL</Label>
                  <Input
                    id="telegramUrl"
                    type="url"
                    placeholder="https://t.me/groupname"
                    value={formData.telegramUrl}
                    onChange={(e) => handleChange("telegramUrl", e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="discordUrl">Discord Invite URL</Label>
                  <Input
                    id="discordUrl"
                    type="url"
                    placeholder="https://discord.gg/invite"
                    value={formData.discordUrl}
                    onChange={(e) => handleChange("discordUrl", e.target.value)}
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="pt-4">
                <Button type="submit" className="w-full" size="lg" disabled={isLoading} data-testid="create-project-button">
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating & Analyzing...
                    </>
                  ) : (
                    "Create Audit & Start Analysis"
                  )}
                </Button>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  * At least GitHub URL or Contract Address is required
                </p>
              </div>
            </CardContent>
          </Card>
        </form>
      </main>
    </div>
  );
}
