import { ComplianceReport } from "@shared/schema";

// Interface for storage operations
export interface IStorage {
  saveComplianceReport(report: ComplianceReport): Promise<ComplianceReport>;
  getComplianceReport(id: string): Promise<ComplianceReport | undefined>;
  listComplianceReports(): Promise<ComplianceReport[]>;
}

// Memory-based storage implementation
export class MemStorage implements IStorage {
  private reports: Map<string, ComplianceReport>;

  constructor() {
    this.reports = new Map();
  }

  async saveComplianceReport(report: ComplianceReport): Promise<ComplianceReport> {
    this.reports.set(report.id, report);
    return report;
  }

  async getComplianceReport(id: string): Promise<ComplianceReport | undefined> {
    return this.reports.get(id);
  }

  async listComplianceReports(): Promise<ComplianceReport[]> {
    return Array.from(this.reports.values());
  }
}

// Create and export the storage instance
export const storage = new MemStorage();
