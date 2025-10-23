export type Role = 'user' | 'admin';
export type BugSeverity = 'low' | 'medium' | 'high' | 'critical';
export type BugStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type ProjectStatus = 'active' | 'inactive' | 'archived';
export type RepositoryStatus = 'active' | 'scanning' | 'completed';
export type ISODateString = string;

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  avatar_url?: string;
  created_at: ISODateString;
  bugs_reported?: number;
}

export interface Bug {
  id: number;
  title: string;
  description?: string;
  severity: BugSeverity;
  status: BugStatus;
  reporter_id: number;
  reporter_name?: string;
  reporter_email?: string;
  assignee_id?: number;
  project_id?: number;
  project_name?: string;
  repository_id?: number;
  repository_name?: string;
  screenshot_url?: string;
  steps_to_reproduce?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  status: ProjectStatus;
  created_by: number;
  created_by_name?: string;
  bugs_count?: number;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface Repository {
  id: number;
  name: string;
  url: string;
  language?: string;
  project_id: number;
  project_name?: string;
  status: RepositoryStatus;
  last_scan?: string;
  vulnerabilities_count: number;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface ApiResponse<T> {
  success?: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface DashboardStats {
  totalBugs: number;
  criticalBugs: number;
  resolvedBugs: number;
  totalUsers: number;
  totalProjects: number;
  totalRepositories: number;
}