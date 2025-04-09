import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { InfoIcon, FileDown } from "lucide-react";

export default function LimitationsDisclaimer() {
  const handleDownloadLimitations = () => {
    // Create a link to download the limitations file
    window.open("/api/limitations/download", "_blank");
  };

  return (
    <Alert className="my-4 border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
      <InfoIcon className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="text-amber-800 dark:text-amber-300 font-medium">Important Disclaimer</AlertTitle>
      <AlertDescription className="text-amber-700 dark:text-amber-300">
        <p className="mb-2">This compliance checker provides automated assessment based on available repository data. Results should be used as guidance and not as a definitive security evaluation.</p>
        <Button 
          variant="outline" 
          size="sm" 
          className="mt-2 text-amber-700 border-amber-300 hover:bg-amber-100 dark:text-amber-300 dark:border-amber-700 dark:hover:bg-amber-900"
          onClick={handleDownloadLimitations}
        >
          <FileDown className="mr-2 h-4 w-4" />
          Download Full Limitations Document
        </Button>
      </AlertDescription>
    </Alert>
  );
}