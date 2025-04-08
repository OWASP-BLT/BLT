import { Card, CardContent } from "@/components/ui/card";
import { Recommendation } from "@/types/compliance";
import { InfoIcon } from "lucide-react";

type RecommendationsSummaryProps = {
  recommendations: Recommendation[];
};

export default function RecommendationsSummary({ recommendations }: RecommendationsSummaryProps) {
  if (recommendations.length === 0) {
    return null;
  }

  return (
    <Card className="mb-6">
      <CardContent className="pt-6">
        <h2 className="text-lg font-medium text-neutral-900 mb-4">Key Recommendations</h2>
        <div className="space-y-3">
          {recommendations.map((recommendation, index) => (
            <div key={index} className="flex items-start">
              <div className="flex-shrink-0">
                <InfoIcon className="h-5 w-5 text-orange-500" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-neutral-800">{recommendation.category}</h3>
                <p className="mt-1 text-sm text-neutral-600">{recommendation.text}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
