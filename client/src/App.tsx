import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import LoginPage from "./pages/LoginPage";
import UnicornHunter from "./pages/UnicornHunter";
import Dashboard from "./pages/Dashboard";
import NewAudit from "./pages/NewAudit";
import AuditDetail from "./pages/AuditDetail";
import DiscoverV2 from "./pages/DiscoverV2";
import Watchlist from "./pages/Watchlist";
import Comparison from "./pages/Comparison";

function Router() {
  // make sure to consider if you need authentication for certain routes
  return (
    <Switch>
      <Route path={"/"} component={Home} />
      <Route path="/login" component={LoginPage} />
      <Route path="/unicorn-hunter" component={UnicornHunter} />
      <Route path="/discover" component={DiscoverV2} />
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/watchlist" component={Watchlist} />
      <Route path="/comparison" component={Comparison} />
      <Route path="/comparison/:id" component={Comparison} />
      <Route path="/new-audit" component={NewAudit} />
      <Route path="/audit/:id" component={AuditDetail} />
      <Route path={"/404"} component={NotFound} />
      {/* Final fallback route */}
      <Route component={NotFound} />
    </Switch>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
