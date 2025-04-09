import { useState } from "react";
import { Category } from "@/types/compliance";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

type CategoryAccordionProps = {
  categories: Category[];
};

export default function CategoryAccordion({ categories }: CategoryAccordionProps) {
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({});

  const toggleCategory = (categoryId: string) => {
    setOpenCategories((prev) => ({
      ...prev,
      [categoryId]: !prev[categoryId],
    }));
  };

  const getCategoryScoreClass = (score: number, maxPoints: number) => {
    const percentage = (score / maxPoints) * 100;
    if (percentage >= 80) return "bg-green-50 text-green-700";
    if (percentage >= 60) return "bg-orange-50 text-orange-700";
    return "bg-red-50 text-red-700";
  };

  return (
    <div className="space-y-4">
      {categories.map((category) => (
        <Collapsible
          key={category.id}
          open={openCategories[category.id]}
          onOpenChange={() => toggleCategory(category.id)}
          className="border border-neutral-200 rounded-lg overflow-hidden"
        >
          <CollapsibleTrigger className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 hover:bg-neutral-100 focus:outline-none transition-colors">
            <div className="flex items-center">
              <h3 className="text-base font-medium text-neutral-900">{category.name}</h3>
              <div className={cn("ml-3 px-2 py-1 rounded-full text-xs font-medium", getCategoryScoreClass(category.score, category.maxPoints))}>
                <span>{category.score}/{category.maxPoints}</span>
              </div>
            </div>
            <ChevronDown 
              className={cn("h-5 w-5 text-neutral-500 transition-transform", 
                openCategories[category.id] ? "transform rotate-180" : ""
              )} 
            />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="px-4 py-5 bg-white">
              {category.checkpoints.map((checkpoint, index) => (
                <div key={index} className="py-2 flex items-start">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className={cn("rounded-full p-1", 
                      checkpoint.passed 
                        ? "text-green-500 bg-green-50" 
                        : "text-red-500 bg-red-50"
                    )}>
                      {checkpoint.passed ? (
                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-neutral-800">{checkpoint.description}</p>
                    {!checkpoint.passed && checkpoint.recommendation && (
                      <div className="mt-1 p-2 bg-neutral-50 rounded border-l-2 border-orange-500">
                        <p className="text-xs text-neutral-600">
                          <span className="font-semibold">Recommendation: </span>
                          <span>{checkpoint.recommendation}</span>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      ))}
    </div>
  );
}
