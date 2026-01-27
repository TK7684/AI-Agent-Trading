import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { APP_TITLE, getLoginUrl } from "@/const";
import { Shield, Github, Coins, Users, TrendingUp, AlertTriangle, Sparkles } from "lucide-react";
import { Link } from "wouter";

export default function Home() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-8 w-8 text-primary" />
            <h1 className="text-2xl font-bold">{APP_TITLE}</h1>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/unicorn-hunter">
              <Button variant="ghost" className="text-purple-600 hover:text-purple-700">
                <Sparkles className="h-4 w-4 mr-2" />
                Unicorn Hunter
              </Button>
            </Link>
            <Link href="/discover">
              <Button variant="ghost">Discover</Button>
            </Link>
            {isAuthenticated ? (
              <>
                <Link href="/dashboard">
                  <Button variant="ghost">Dashboard</Button>
                </Link>
                <Link href="/new-audit">
                  <Button>New Audit</Button>
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

      {/* Hero Section */}
      <section className="container py-20 md:py-32">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            <Shield className="h-4 w-4" />
            AI-Powered Crypto Project Auditor
          </div>
          
          <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
            Audit Crypto Projects
            <br />
            <span className="text-primary">Before You Invest</span>
          </h2>
          
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Comprehensive AI-driven analysis of crypto projects. Evaluate GitHub activity, tokenomics, smart contract risks, and community engagement—all in one place.
          </p>

          <div className="flex items-center justify-center gap-4 pt-4 flex-wrap">
            <Link href="/unicorn-hunter">
              <Button size="lg" className="text-lg px-8 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
                <Sparkles className="h-5 w-5 mr-2" />
                Hunt Unicorns
              </Button>
            </Link>
            <Link href="/discover">
              <Button size="lg" variant="outline" className="text-lg px-8">
                Discover Projects
              </Button>
            </Link>
            {isAuthenticated ? (
              <Link href="/new-audit">
                <Button size="lg" variant="outline" className="text-lg px-8">
                  Create Custom Audit
                </Button>
              </Link>
            ) : (
              <a href={getLoginUrl()}>
                <Button size="lg" variant="outline" className="text-lg px-8">
                  Sign In
                </Button>
              </a>
            )}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container py-20 bg-card/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h3 className="text-3xl font-bold mb-4">Comprehensive Analysis</h3>
            <p className="text-muted-foreground text-lg">
              Our AI analyzes multiple aspects of crypto projects to give you a complete picture
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <Github className="h-10 w-10 text-primary mb-2" />
                <CardTitle>GitHub Analysis</CardTitle>
                <CardDescription>
                  Evaluate code quality, commit history, contributors, and development activity
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <Coins className="h-10 w-10 text-primary mb-2" />
                <CardTitle>Tokenomics Review</CardTitle>
                <CardDescription>
                  Analyze token distribution, supply metrics, and economic sustainability
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <AlertTriangle className="h-10 w-10 text-primary mb-2" />
                <CardTitle>Contract Risk Assessment</CardTitle>
                <CardDescription>
                  Detect honeypots, malicious functions, and security vulnerabilities
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <Users className="h-10 w-10 text-primary mb-2" />
                <CardTitle>Community Analysis</CardTitle>
                <CardDescription>
                  Monitor Twitter, Telegram, and Discord for engagement and sentiment
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <TrendingUp className="h-10 w-10 text-primary mb-2" />
                <CardTitle>AI-Powered Scoring</CardTitle>
                <CardDescription>
                  Get an overall risk score and investment recommendation from our AI
                </CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-primary/50 transition-colors">
              <CardHeader>
                <Shield className="h-10 w-10 text-primary mb-2" />
                <CardTitle>Detailed Reports</CardTitle>
                <CardDescription>
                  Receive comprehensive audit reports with actionable insights
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container py-20">
        <Card className="max-w-4xl mx-auto bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
          <CardContent className="p-12 text-center space-y-6">
            <h3 className="text-3xl font-bold">Ready to Audit Your First Project?</h3>
            <p className="text-lg text-muted-foreground">
              Join thousands of investors making informed decisions with AI-powered crypto audits
            </p>
            {isAuthenticated ? (
              <Link href="/new-audit">
                <Button size="lg" className="text-lg px-8">
                  Create New Audit
                </Button>
              </Link>
            ) : (
              <a href={getLoginUrl()}>
                <Button size="lg" className="text-lg px-8">
                  Sign Up Now
                </Button>
              </a>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t bg-card/50">
        <div className="container py-8 text-center text-muted-foreground">
          <p>&copy; 2024 {APP_TITLE}. AI-powered crypto project auditing platform.</p>
        </div>
      </footer>
    </div>
  );
}
