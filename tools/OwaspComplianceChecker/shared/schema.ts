import { pgTable, text, serial, integer, boolean, jsonb, timestamp } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Define the checkpoint type
export type Checkpoint = {
  description: string;
  passed: boolean;
  recommendation?: string;
};

// Define the category type
export type Category = {
  id: string;
  name: string;
  score: number;
  maxPoints: number;
  checkpoints: Checkpoint[];
};

// Define the recommendation type
export type Recommendation = {
  category: string;
  text: string;
};

// Define the compliance report type
export type ComplianceReport = {
  id: string;
  repoUrl: string;
  repoName: string;
  overallScore: number;
  categories: Category[];
  recommendations: Recommendation[];
  createdAt: string;
};

// Define database schema for persistence (used with drizzle-orm)
export const complianceReports = pgTable("compliance_reports", {
  id: text("id").primaryKey(),
  repoUrl: text("repo_url").notNull(),
  repoName: text("repo_name").notNull(),
  overallScore: integer("overall_score").notNull(),
  categories: jsonb("categories").notNull().$type<Category[]>(),
  recommendations: jsonb("recommendations").notNull().$type<Recommendation[]>(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

// Define the insert schema for compliance reports
export const insertComplianceReportSchema = createInsertSchema(complianceReports).omit({
  createdAt: true
});

export type InsertComplianceReport = z.infer<typeof insertComplianceReportSchema>;
