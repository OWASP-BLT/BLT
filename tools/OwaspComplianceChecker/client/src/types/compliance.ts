export type Checkpoint = {
  description: string;
  passed: boolean;
  recommendation?: string;
};

export type Category = {
  id: string;
  name: string;
  score: number;
  maxPoints: number;
  checkpoints: Checkpoint[];
};

export type Recommendation = {
  category: string;
  text: string;
};

export type ComplianceReport = {
  id: string;
  repoUrl: string;
  repoName: string;
  overallScore: number;
  categories: Category[];
  recommendations: Recommendation[];
  createdAt: string;
};
