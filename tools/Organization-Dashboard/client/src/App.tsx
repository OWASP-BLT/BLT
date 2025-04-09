import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { WebSocketProvider } from "@/contexts/websocket-context";
import { Layout } from "@/components/layout/layout";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/dashboard";
import SecurityIssues from "@/pages/security-issues";
import BugReports from "@/pages/bug-reports";
import Contributors from "@/pages/contributors";
import Activity from "@/pages/activity";
import Settings from "@/pages/settings";

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/security-issues" component={SecurityIssues} />
        <Route path="/bug-reports" component={BugReports} />
        <Route path="/contributors" component={Contributors} />
        <Route path="/activity" component={Activity} />
        <Route path="/settings" component={Settings} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WebSocketProvider>
        <Router />
        <Toaster />
      </WebSocketProvider>
    </QueryClientProvider>
  );
}

export default App;
