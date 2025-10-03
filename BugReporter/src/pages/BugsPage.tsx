import { useState, useEffect, useCallback } from 'react';
import { Plus, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
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
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bugs</h1>
          <p className="text-gray-600 mt-1">Report and track bugs across your projects</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center space-x-2"
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

      <div className="space-y-4">
        {bugs.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No bugs found</h3>
            <p className="text-gray-600">
              {Object.keys(searchParams).length === 0
                ? "No bugs have been reported yet. Click 'Report Bug' to get started."
                : "No bugs match your search criteria. Try adjusting your filters."
              }
            </p>
          </div>
        ) : (
          bugs.map((bug) => (
            <BugCard
              key={bug.id}
              bug={bug}
              onUpdate={handleBugUpdated}
              canEdit={user?.role === 'admin' || bug.reporter_id === user?.id}
            />
          ))
        )}
      </div>
    </div>
  );
}