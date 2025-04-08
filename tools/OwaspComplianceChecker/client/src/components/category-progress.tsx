import { Category } from "@/types/compliance";
import { cn } from "@/lib/utils";

type CategoryProgressProps = {
  category: Category;
};

export default function CategoryProgress({ category }: CategoryProgressProps) {
  const getCategoryColorClass = (score: number, maxPoints: number) => {
    const percentage = (score / maxPoints) * 100;
    if (percentage >= 80) return "bg-green-500";
    if (percentage >= 60) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className="category-item">
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-neutral-700">{category.name}</span>
        <span className="text-sm font-medium text-neutral-700">
          {category.score}/{category.maxPoints}
        </span>
      </div>
      <div className="w-full bg-neutral-100 rounded-full h-2.5">
        <div 
          className={cn("h-2.5 rounded-full transition-all duration-1000 ease-in-out", 
            getCategoryColorClass(category.score, category.maxPoints)
          )}
          style={{ width: `${(category.score / category.maxPoints) * 100}%` }}
        />
      </div>
    </div>
  );
}
