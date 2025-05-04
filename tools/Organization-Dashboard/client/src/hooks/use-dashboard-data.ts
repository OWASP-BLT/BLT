import { useQuery } from "@tanstack/react-query";

export function useDashboardStats() {
  return useQuery({
    queryKey: ['/api/dashboard/stats'],
    staleTime: 60000 // 1 minute
  });
}

export function useSecurityTrends() {
  return useQuery({
    queryKey: ['/api/dashboard/security-trends'],
    staleTime: 300000 // 5 minutes
  });
}

export function useRiskDistribution() {
  return useQuery({
    queryKey: ['/api/dashboard/risk-distribution'],
    staleTime: 300000 // 5 minutes
  });
}

export function useBugReports(filters: any = {}) {
  return useQuery({
    queryKey: ['/api/bugs', filters],
    staleTime: 60000 // 1 minute
  });
}

export function useActivityLogs(limit: number = 10) {
  return useQuery({
    queryKey: [`/api/activity?limit=${limit}`],
    staleTime: 60000 // 1 minute
  });
}
