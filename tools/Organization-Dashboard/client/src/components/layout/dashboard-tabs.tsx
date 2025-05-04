import { Link } from "wouter";

type TabType = "overview" | "security-metrics" | "bug-reports" | "contributor-activity";

interface DashboardTabsProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export default function DashboardTabs({ activeTab, onTabChange }: DashboardTabsProps) {
  const tabs = [
    { id: "overview" as const, name: "Overview", href: "/" },
    { id: "security-metrics" as const, name: "Security Metrics", href: "/security-issues" },
    { id: "bug-reports" as const, name: "Bug Reports", href: "/bug-reports" },
    { id: "contributor-activity" as const, name: "Contributor Activity", href: "/contributors" }
  ];

  return (
    <div className="mb-6">
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px space-x-8">
          {tabs.map((tab) => (
            <Link
              key={tab.id}
              href={tab.href}
              onClick={(e) => {
                // Only prevent default if on the dashboard page, otherwise navigate
                if (window.location.pathname === '/') {
                  e.preventDefault();
                  onTabChange(tab.id);
                }
              }}
            >
              <a
                className={`px-1 py-4 text-sm font-medium border-b-2 whitespace-nowrap cursor-pointer ${
                  activeTab === tab.id
                    ? "text-blue-600 border-blue-500"
                    : "text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {tab.name}
              </a>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}
