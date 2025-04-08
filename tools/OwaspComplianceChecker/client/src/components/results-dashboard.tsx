import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { ComplianceReport } from "@/types/compliance";
import CategoryProgress from "./category-progress";
import CategoryAccordion from "./category-accordion";
import RecommendationsSummary from "./recommendations-summary";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

type ResultsDashboardProps = {
  report: ComplianceReport;
};

export default function ResultsDashboard({ report }: ResultsDashboardProps) {
  const { toast } = useToast();

  const downloadReportMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/compliance/download", { reportId: report.id });
      return res.blob();
    },
    onSuccess: (blob) => {
      // Create URL for the blob
      const url = window.URL.createObjectURL(blob);
      // Create temporary link element
      const a = document.createElement("a");
      a.href = url;
      a.download = `owasp-compliance-report-${report.repoName.replace(/\//g, "-")}.pdf`;
      // Trigger download
      document.body.appendChild(a);
      a.click();
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: "Report Downloaded",
        description: "The compliance report has been downloaded successfully.",
      });
    },
    onError: () => {
      toast({
        title: "Download Failed",
        description: "Failed to download the compliance report. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleDownload = () => {
    downloadReportMutation.mutate();
  };

  return (
    <div className="px-4 sm:px-0">
      {/* Overall Score Card */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-medium text-neutral-900">Overall Compliance Score</h2>
              <p className="text-sm text-neutral-500">Based on 100-point OWASP compliance checklist</p>
            </div>
            <div className="mt-4 md:mt-0">
              <Button
                variant="outline"
                className="text-primary-600 bg-primary-50 hover:bg-primary-100 border-primary-200"
                onClick={handleDownload}
                disabled={downloadReportMutation.isPending}
              >
                {downloadReportMutation.isPending ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-5 w-5" />
                    Download Report
                  </>
                )}
              </Button>
            </div>
          </div>
          
          <div className="mt-6 flex flex-col md:flex-row items-start">
            <div className="w-full md:w-1/3 flex justify-center mb-6 md:mb-0">
              <div className="relative w-48 h-48">
                <svg className="w-48 h-48">
                  <circle cx="96" cy="96" r="80" fill="none" stroke="#e1e5eb" strokeWidth="24" />
                  <circle 
                    cx="96" 
                    cy="96" 
                    r="80" 
                    fill="none" 
                    stroke={report.overallScore < 60 ? "hsl(4, 90%, 58%)" : (report.overallScore < 80 ? "hsl(36, 100%, 50%)" : "hsl(142, 71%, 45%)")} 
                    strokeWidth="24" 
                    strokeDasharray="502" 
                    strokeDashoffset={502 - (502 * report.overallScore / 100)} 
                    style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 1.5s ease-in-out" }}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center flex-col">
                  <span className="text-4xl font-bold">{Math.round(report.overallScore)}</span>
                  <span className="text-neutral-500 text-sm">out of 100</span>
                </div>
              </div>
            </div>
            
            <div className="w-full md:w-2/3">
              <div className="space-y-5">
                {report.categories.map((category) => (
                  <CategoryProgress 
                    key={category.id} 
                    category={category} 
                  />
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Category Details */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="border-b border-neutral-200 pb-4 mb-4">
            <h2 className="text-lg font-medium text-neutral-900">Detailed Compliance Results</h2>
            <p className="text-sm text-neutral-500">Expand each category to see detailed compliance checks</p>
          </div>
          
          <CategoryAccordion categories={report.categories} />
        </CardContent>
      </Card>
      
      {/* Recommendations Summary */}
      <RecommendationsSummary recommendations={report.recommendations} />
    </div>
  );
}
