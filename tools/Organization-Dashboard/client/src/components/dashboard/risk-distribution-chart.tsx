import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

type RiskDistributionData = {
  labels: string[];
  datasets: [{
    data: number[];
    backgroundColor: string[];
    borderWidth: number;
  }];
};

export default function RiskDistributionChart() {
  const { data, isLoading, error } = useQuery<RiskDistributionData>({
    queryKey: ['/api/dashboard/risk-distribution']
  });

  // Transform data for Recharts
  const chartData = data ? data.labels.map((label, index) => ({
    name: label,
    value: data.datasets[0].data[index],
    color: data.datasets[0].backgroundColor[index]
  })) : [];

  const RADIAN = Math.PI / 180;
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }: any) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        fontSize={12}
        fontWeight={600}
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <Card className="overflow-hidden">
      <CardHeader className="px-4 py-5 sm:px-6">
        <CardTitle>Risk Distribution</CardTitle>
        <CardDescription>Current vulnerability assessment</CardDescription>
      </CardHeader>
      <CardContent className="px-4 py-5 sm:p-6">
        <div className="h-64">
          {isLoading && (
            <div className="w-full h-full flex items-center justify-center">
              <Skeleton className="h-full w-full rounded-full" />
            </div>
          )}
          
          {error && (
            <div className="w-full h-full flex items-center justify-center">
              <p className="text-red-500">Failed to load risk distribution data</p>
            </div>
          )}
          
          {data && (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderCustomizedLabel}
                  outerRadius={80}
                  innerRadius={40}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: number, name: string) => {
                    const total = chartData.reduce((sum, item) => sum + item.value, 0);
                    const percent = ((value / total) * 100).toFixed(1);
                    return [`${value} (${percent}%)`, name];
                  }}
                />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
