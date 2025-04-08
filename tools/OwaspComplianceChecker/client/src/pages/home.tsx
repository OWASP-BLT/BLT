import { useState } from "react";
import UrlInput from "@/components/url-input";
import ResultsDashboard from "@/components/results-dashboard";
import InfoCards from "@/components/info-cards";
import LimitationsDisclaimer from "@/components/limitations-disclaimer";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { ComplianceReport } from "@/types/compliance";
import { useToast } from "@/hooks/use-toast";

export default function Home() {
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const { toast } = useToast();

  const checkComplianceMutation = useMutation({
    mutationFn: async (repoUrl: string) => {
      const res = await apiRequest("POST", "/api/compliance/check", { url: repoUrl });
      return res.json();
    },
    onSuccess: (data: ComplianceReport) => {
      setReport(data);
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to check repository compliance. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleCheckCompliance = (repoUrl: string) => {
    checkComplianceMutation.mutate(repoUrl);
  };

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <UrlInput 
        onSubmit={handleCheckCompliance} 
        isLoading={checkComplianceMutation.isPending} 
      />
      
      <LimitationsDisclaimer />
      
      {report ? (
        <ResultsDashboard report={report} />
      ) : (
        <InfoCards />
      )}
    </div>
  );
}
