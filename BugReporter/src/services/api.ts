import type { AuthResponse, Bug, Project, Repository, User, DashboardStats } from '../types';

const API_BASE = 'https://bug-reporter-api.bugreporting.workers.dev';

class ApiService {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>).Authorization = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        // If token is invalid, clear it and redirect to login
        if (response.status === 401) {
          this.logout();
          window.location.href = '/login';
          throw new Error('Session expired. Please login again.');
        }

        const error = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Raw upload using FormData
  async uploadFile(file: File): Promise<{ url: string }> {
    const url = `${API_BASE}/protected/uploads`;
    const formData = new FormData();
    formData.append('file', file);

    const headers: HeadersInit = {};
    if (this.token) {
      (headers as Record<string, string>).Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers, // do not set Content-Type; browser will set multipart boundary
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.logout();
        window.location.href = '/login';
        throw new Error('Session expired. Please login again.');
      }
      const error = await response.json().catch(() => ({ message: 'Upload failed' }));
      throw new Error(error.message || 'Upload failed');
    }

    return response.json();
  }

  // Auth methods
  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    this.token = response.token;
    localStorage.setItem('auth_token', response.token);
    return response;
  }

  async register(email: string, name: string, password: string): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, name, password }),
    });
    
    this.token = response.token;
    localStorage.setItem('auth_token', response.token);
    return response;
  }

  async getCurrentUser(): Promise<{ user: User }> {
    return this.request<{ user: User }>('/api/protected/me');
  }

  logout(): void {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  // Bug methods
  async getBugs(params?: { search?: string; status?: string; severity?: string; project?: string }): Promise<{ bugs: Bug[] }> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.project) searchParams.append('project', params.project);
    
    const queryString = searchParams.toString();
    const endpoint = `/api/protected/bugs${queryString ? `?${queryString}` : ''}`;
    
    return this.request<{ bugs: Bug[] }>(endpoint);
  }

  async getBug(id: number): Promise<{ bug: Bug }> {
    return this.request<{ bug: Bug }>(`/api/protected/bugs/${id}`);
  }

  async createBug(bugData: Partial<Bug>): Promise<{ bug: Bug }> {
    return this.request<{ bug: Bug }>('/api/protected/bugs', {
      method: 'POST',
      body: JSON.stringify(bugData),
    });
  }

  async updateBug(id: number, updates: Partial<Bug>): Promise<{ bug: Bug }> {
    return this.request<{ bug: Bug }>(`/protected/bugs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  // Project methods
  async getProjects(params?: { search?: string; status?: string }): Promise<{ projects: Project[] }> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    
    const queryString = searchParams.toString();
    const endpoint = `/api/protected/projects${queryString ? `?${queryString}` : ''}`;
    
    return this.request<{ projects: Project[] }>(endpoint);
  }

  async getProject(id: number): Promise<{ project: Project }> {
    return this.request<{ project: Project }>(`/protected/projects/${id}`);
  }

  async createProject(projectData: Partial<Project>): Promise<{ project: Project }> {
    return this.request<{ project: Project }>('/api/protected/projects', {
      method: 'POST',
      body: JSON.stringify(projectData),
    });
  }

  async deleteProject(id: number): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/protected/projects/${id}`, {
      method: 'DELETE',
    });
  }

  async findOrCreateProject(name: string): Promise<{ project: Project }> {
    return this.request<{ project: Project }>(`/protected/projects/find-or-create`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  // Repository methods
  async getRepositories(params?: { search?: string; status?: string; project?: string; language?: string }): Promise<{ repositories: Repository[] }> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.project) searchParams.append('project', params.project);
    if (params?.language) searchParams.append('language', params.language);
    
    const queryString = searchParams.toString();
    const endpoint = `/api/protected/repositories${queryString ? `?${queryString}` : ''}`;
    
    return this.request<{ repositories: Repository[] }>(endpoint);
  }

  async getRepository(id: number): Promise<{ repository: Repository }> {
    return this.request<{ repository: Repository }>(`/protected/repositories/${id}`);
  }

  async createRepository(repoData: Partial<Repository>): Promise<{ repository: Repository }> {
    return this.request<{ repository: Repository }>('/api/protected/repositories', {
      method: 'POST',
      body: JSON.stringify(repoData),
    });
  }

  async deleteRepository(id: number): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/protected/repositories/${id}`, {
      method: 'DELETE',
    });
  }

  async findOrCreateRepository(name: string, project_id: number): Promise<{ repository: Repository }> {
    return this.request<{ repository: Repository }>(`/protected/repositories/find-or-create`, {
      method: 'POST',
      body: JSON.stringify({ name, project_id }),
    });
  }

  // Admin methods
  async getUsers(params?: { search?: string; role?: string }): Promise<{ users: User[] }> {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.role) searchParams.append('role', params.role);
    
    const queryString = searchParams.toString();
    const endpoint = `/api/protected/admin/users${queryString ? `?${queryString}` : ''}`;
    
    return this.request<{ users: User[] }>(endpoint);
  }

  async updateUser(id: number, updates: Partial<User & { password?: string }>): Promise<{ user: User }> {
    return this.request<{ user: User }>(`/api/protected/admin/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return this.request<{ message: string }>('/api/protected/change-password', {
      method: 'PUT',
      body: JSON.stringify({ currentPassword, newPassword }),
    });
  }

  async deleteUser(id: number): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/protected/admin/users/${id}`, {
      method: 'DELETE',
    });
  }

  async getDashboardStats(): Promise<{ stats: DashboardStats }> {
    return this.request<{ stats: DashboardStats }>('/api/protected/admin/stats');
  }
}

export const apiService = new ApiService();