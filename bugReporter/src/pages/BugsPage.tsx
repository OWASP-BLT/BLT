import { useState, useEffect, useCallback } from 'react';
import { Plus, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../contexts/NotificationContext';
import type { Bug, Project, Repository } from '../types';
import BugForm from '../components/BugForm';
import BugCard from '../components/BugCard';
import SearchAndFilter from '../components/SearchAndFilter';

export default function BugsPage() {
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [searchParams, setSearchParams] = useState<{
    search?: string;
    status?: string;
    severity?: string;
    project?: string;
  }>({});
  const { user } = useAuth();
  const { error: showError } = useNotification();

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [bugsResponse, projectsResponse, repositoriesResponse] = await Promise.all([
        apiService.getBugs(searchParams),
        apiService.getProjects(),
        apiService.getRepositories(),
      ]);
      
      setBugs(bugsResponse.bugs);
      setProjects(projectsResponse.projects);
      setRepositories(repositoriesResponse.repositories);
    } catch (error) {
      console.error('Failed to load data:', error);
      showError('Failed to load data', 'Unable to fetch bugs, projects, or repositories. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, [searchParams, showError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleBugCreated = (newBug: Bug) => {
    setBugs(prev => [newBug, ...prev]);
    setShowForm(false);
  };

  const handleBugUpdated = (updatedBug: Bug) => {
    setBugs(prev => prev.map(bug => bug.id === updatedBug.id ? updatedBug : bug));
  };

  const handleSearchChange = (search: string) => {
    setSearchParams(prev => ({ ...prev, search: search || undefined }));
  };

  const handleFilterChange = (filters: Record<string, string>) => {
    setSearchParams(prev => ({ ...prev, ...filters }));
  };

  const filterOptions = {
    status: {
      label: 'Status',
      options: [
        { label: 'Open', value: 'open' },
        { label: 'In Progress', value: 'in_progress' },
        { label: 'Resolved', value: 'resolved' },
        { label: 'Closed', value: 'closed' }
      ]
    },
    severity: {
      label: 'Severity',
      options: [
        { label: 'Low', value: 'low' },
        { label: 'Medium', value: 'medium' },
        { label: 'High', value: 'high' },
        { label: 'Critical', value: 'critical' }
      ]
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bugs</h1>
          <p className="text-gray-600 mt-1">Report and track bugs across your projects</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center justify-center space-x-2 w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Report Bug</span>
        </button>
      </div>

      {showForm && (
        <BugForm
          projects={projects}
          repositories={repositories}
          onSubmit={handleBugCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="card p-4 sm:p-5">
        <SearchAndFilter
        searchPlaceholder="Search bugs by title, description, reporter, or project..."
        onSearchChange={handleSearchChange}
        onFilterChange={handleFilterChange}
        filters={filterOptions}
        initialSearch={searchParams.search}
        initialFilters={{
          status: searchParams.status || '',
          severity: searchParams.severity || ''
        }}
        />
      </div>

      <div className="space-y-4">
        {bugs.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No bugs found</h3>
            <p className="text-gray-600">
              {Object.values(searchParams).some(value => value && value.trim() !== '')
                ? "No bugs match your search criteria. Try adjusting your filters."
                : "No bugs have been reported yet. Click 'Report Bug' to get started."
              }
            </p>
          </div>
        ) : (
          bugs.map((bug) => (
            <BugCard
              key={bug.id}
              bug={bug}
              onUpdate={handleBugUpdated}
              canEdit={user?.role === 'admin' || (user?.id && bug.reporter_id === user.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}