import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { AlertCircle, ShieldCheck, Users, AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "wouter";

type StatsData = {
  totalIssues: number;
  criticalVulnerabilities: number;
  resolvedIssues: number;
  activeContributors: number;
};

export default function OverviewStats() {
  const { data, isLoading, error } = useQuery<StatsData>({
    queryKey: ['/api/dashboard/stats']
  });

  if (error) {
    return (
      <div className="px-4 py-6 md:px-6 lg:px-8">
        <div className="p-4 bg-red-50 text-red-800 rounded-lg">
          Failed to load dashboard statistics
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 md:px-6 lg:px-8">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Issues */}
        <StatCard
          icon={<AlertCircle className="w-6 h-6 text-white" />}
          iconBgColor="bg-blue-500"
          title="Total Issues"
          value={isLoading ? undefined : data?.totalIssues}
          linkText="View all"
          linkHref="/security-issues"
          linkColor="text-blue-600 hover:text-blue-500"
        />

        {/* Critical Vulnerabilities */}
        <StatCard
          icon={<AlertTriangle className="w-6 h-6 text-white" />}
          iconBgColor="bg-red-500"
          title="Critical Vulnerabilities"
          value={isLoading ? undefined : data?.criticalVulnerabilities}
          linkText="Urgent attention"
          linkHref="/security-issues?severity=critical"
          linkColor="text-red-600 hover:text-red-500"
        />

        {/* Resolved Issues */}
        <StatCard
          icon={<ShieldCheck className="w-6 h-6 text-white" />}
          iconBgColor="bg-green-500"
          title="Resolved Issues"
          value={isLoading ? undefined : data?.resolvedIssues}
          linkText="View details"
          linkHref="/bug-reports?status=resolved"
          linkColor="text-green-600 hover:text-green-500"
        />

        {/* Active Contributors */}
        <StatCard
          icon={<Users className="w-6 h-6 text-white" />}
          iconBgColor="bg-indigo-500"
          title="Active Contributors"
          value={isLoading ? undefined : data?.activeContributors}
          linkText="View all"
          linkHref="/contributors"
          linkColor="text-indigo-600 hover:text-indigo-500"
        />
      </div>
    </div>
  );
}

type StatCardProps = {
  icon: React.ReactNode;
  iconBgColor: string;
  title: string;
  value: number | undefined;
  linkText: string;
  linkHref: string;
  linkColor: string;
};

function StatCard({ icon, iconBgColor, title, value, linkText, linkHref, linkColor }: StatCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex items-center">
          <div className={`flex-shrink-0 p-3 ${iconBgColor} rounded-md`}>
            {icon}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd>
                {value !== undefined ? (
                  <div className="text-lg font-medium text-gray-900">{value}</div>
                ) : (
                  <Skeleton className="h-7 w-12" />
                )}
              </dd>
            </dl>
          </div>
        </div>
      </CardContent>
      <CardFooter className="px-5 py-3 bg-gray-50">
        <div className="text-sm">
          <Link href={linkHref}>
            <a className={`font-medium ${linkColor} cursor-pointer`}>
              {linkText}
            </a>
          </Link>
        </div>
      </CardFooter>
    </Card>
  );
}
