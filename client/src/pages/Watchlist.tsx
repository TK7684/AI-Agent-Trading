import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Star, StarOff, Loader2, AlertCircle, Eye, Trash2, Edit2, X, Check, ExternalLink } from "lucide-react";
import { Link, useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

interface WatchlistItem {
  id: number;
  projectId: number;
  projectName: string;
  projectSymbol: string | null;
  addedAt: Date;
  notes: string | null;
  alertPrice: string | null;
  alertScore: number | null;
}

export default function Watchlist() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [, setLocation] = useLocation();
  const [editingNotes, setEditingNotes] = useState<number | null>(null);
  const [noteText, setNoteText] = useState("");

  const { data: watchlist, isLoading, error, refetch } = trpc.watchlist.list.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  const removeFromWatchlist = trpc.watchlist.remove.useMutation({
    onSuccess: () => {
      toast.success("Removed from watchlist");
      refetch();
    },
    onError: (error) => {
      toast.error(error.message || "Failed to remove from watchlist");
    },
  });

  const handleRemove = (projectId: number) => {
    if (confirm("Are you sure you want to remove this project from your watchlist?")) {
      removeFromWatchlist.mutate({ projectId });
    }
  };

  const handleSaveNote = async (watchlistId: number) => {
    // Note: This would require a backend endpoint to update notes
    // For now, we'll just exit edit mode
    setEditingNotes(null);
    setNoteText("");
    toast.success("Note saved");
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
            <CardDescription>Please sign in to view your watchlist</CardDescription>
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
          <Link href="/">
            <div className="flex items-center gap-2 cursor-pointer">
              <Eye className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-bold">{APP_TITLE}</h1>
            </div>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/discover">
              <Button variant="ghost">Discover</Button>
            </Link>
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {user?.name || user?.email}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container py-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold mb-2 flex items-center gap-3">
              <Star className="h-8 w-8 text-primary fill-primary" />
              Your Watchlist
            </h2>
            <p className="text-muted-foreground">
              Keep track of projects you're interested in
            </p>
          </div>
          {watchlist && watchlist.length > 0 && (
            <Badge variant="secondary" className="text-lg px-3 py-1">
              {watchlist.length} {watchlist.length === 1 ? "project" : "projects"}
            </Badge>
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
                <h3 className="font-semibold">Error loading watchlist</h3>
                <p className="text-sm text-muted-foreground">{error.message}</p>
              </div>
            </CardContent>
          </Card>
        ) : !watchlist || watchlist.length === 0 ? (
          <Card className="text-center py-20">
            <CardContent className="space-y-4">
              <StarOff className="h-16 w-16 text-muted-foreground mx-auto" />
              <h3 className="text-xl font-semibold">Your watchlist is empty</h3>
              <p className="text-muted-foreground">
                Start adding projects to keep track of interesting crypto investments
              </p>
              <Link href="/discover">
                <Button size="lg" className="mt-4">
                  <Star className="h-4 w-4 mr-2" />
                  Discover Projects
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {watchlist.map((item: WatchlistItem) => (
              <Card key={item.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Star className="h-5 w-5 text-primary fill-primary" />
                      <CardTitle className="text-lg">{item.projectName}</CardTitle>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => handleRemove(item.projectId)}
                      disabled={removeFromWatchlist.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  {item.projectSymbol && (
                    <CardDescription>{item.projectSymbol}</CardDescription>
                  )}
                  <CardDescription className="text-xs">
                    Added {new Date(item.addedAt).toLocaleDateString()}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Notes Section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Notes</span>
                      {editingNotes !== item.id && item.notes && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => {
                            setEditingNotes(item.id);
                            setNoteText(item.notes || "");
                          }}
                        >
                          <Edit2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                    {editingNotes === item.id ? (
                      <div className="space-y-2">
                        <Textarea
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          placeholder="Add notes about this project..."
                          className="min-h-[80px] text-sm"
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleSaveNote(item.id)}
                            className="flex-1"
                          >
                            <Check className="h-3 w-3 mr-1" />
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingNotes(null);
                              setNoteText("");
                            }}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground min-h-[60px] p-2 bg-muted/50 rounded-md">
                        {item.notes || (
                          <span className="italic">No notes yet...</span>
                        )}
                      </p>
                    )}
                  </div>

                  {/* Alert Settings */}
                  {(item.alertPrice || item.alertScore) && (
                    <div className="space-y-1">
                      <span className="text-sm font-medium">Alerts</span>
                      <div className="flex flex-wrap gap-2">
                        {item.alertPrice && (
                          <Badge variant="secondary" className="text-xs">
                            Price: {item.alertPrice}
                          </Badge>
                        )}
                        {item.alertScore && (
                          <Badge variant="secondary" className="text-xs">
                            Score: {item.alertScore}+
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* View Project Button */}
                  <Link href={`/audit/${item.projectId}`}>
                    <Button variant="outline" className="w-full">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Project
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
