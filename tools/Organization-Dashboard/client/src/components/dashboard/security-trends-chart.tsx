import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

type SecurityTrendDataset = {
  label: string;
  data: number[];
  borderColor: string;
  backgroundColor: string;
};

type SecurityTrendData = {
  labels: string[];
  datasets: SecurityTrendDataset[];
};

export default function SecurityTrendsChart() {
  const { data, isLoading, error } = useQuery<SecurityTrendData>({
    queryKey: ['/api/dashboard/security-trends']
  });

  // Transform data for Recharts
  const chartData = data ? data.labels.map((label, index) => {
    const dataPoint: any = { name: label };
    data.datasets.forEach(dataset => {
      dataPoint[dataset.label] = dataset.data[index];
    });
    return dataPoint;
  }) : [];

  return (
    <Card className="overflow-hidden lg:col-span-2">
      <CardHeader className="px-4 py-5 sm:px-6">
        <CardTitle>Security Trends</CardTitle>
        <CardDescription>30-day historical view of security incidents</CardDescription>
      </CardHeader>
      <CardContent className="px-4 py-5 sm:p-6">
        <div className="h-64">
          {isLoading && (
            <div className="w-full h-full flex items-center justify-center">
              <Skeleton className="h-full w-full" />
            </div>
          )}
          
          {error && (
            <div className="w-full h-full flex items-center justify-center">
              <p className="text-red-500">Failed to load security trends data</p>
            </div>
          )}
          
          {data && (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="Critical Issues" 
                  stroke="#EF4444" 
                  fill="rgba(239, 68, 68, 0.1)" 
                  strokeWidth={2}
                  activeDot={{ r: 8 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="High Issues" 
                  stroke="#F59E0B" 
                  fill="rgba(245, 158, 11, 0.1)" 
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="Medium Issues" 
                  stroke="#10B981" 
                  fill="rgba(16, 185, 129, 0.1)" 
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
