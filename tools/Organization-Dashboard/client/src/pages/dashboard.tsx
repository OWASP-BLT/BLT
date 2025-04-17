import { useState } from "react";
import OverviewStats from "@/components/dashboard/overview-stats";
import SecurityTrendsChart from "@/components/dashboard/security-trends-chart";
import RiskDistributionChart from "@/components/dashboard/risk-distribution-chart";
import BugReportsTable from "@/components/dashboard/bug-reports-table";
import ActivityFeed from "@/components/dashboard/activity-feed";
import { RealTimeActivityFeed } from "@/components/activity/real-time-activity-feed";
import DashboardTabs from "@/components/layout/dashboard-tabs";

type TabType = "overview" | "security-metrics" | "bug-reports" | "contributor-activity";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  return (
    <main className="relative flex-1 overflow-y-auto focus:outline-none">
      {/* Overview Stats */}
      <OverviewStats />

      {/* Dashboard Main Content */}
      <div className="px-4 py-6 md:px-6 lg:px-8">
        <DashboardTabs activeTab={activeTab} onTabChange={setActiveTab} />
        
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Security Trends Chart */}
          <SecurityTrendsChart />
          
          {/* Risk Distribution */}
          <RiskDistributionChart />
          
          {/* Bug Reports Table */}
          <BugReportsTable />
          
          {/* Activity Feed */}
          <RealTimeActivityFeed />
        </div>
      </div>
    </main>
  );
}
