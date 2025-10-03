import { useState, useEffect } from 'react';
import { Plus, ExternalLink, Calendar, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import type { Repository, Project } from '../types';
import RepositoryForm from '../components/RepositoryForm';
import RepositoryDetail from '../components/RepositoryDetail';

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [reposResponse, projectsResponse] = await Promise.all([
        apiService.getRepositories(),
        apiService.getProjects(),
      ]);
      setRepositories(reposResponse.repositories);
      setProjects(projectsResponse.projects);
    } catch (error) {
      console.error('Failed to load data:', error);
      alert('Failed to load repositories. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  };

  const handleRepositoryCreated = (newRepository: Repository) => {
    setRepositories(prev => [newRepository, ...prev]);
    setShowForm(false);
  };

  const handleRepositoryDeleted = (repositoryId: number) => {
    setRepositories(prev => prev.filter(r => r.id !== repositoryId));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'scanning': return 'bg-blue-100 text-blue-800';
      case 'completed': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
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
          <h1 className="text-2xl font-bold text-gray-900">Repositories</h1>
          <p className="text-gray-600 mt-1">Monitor and scan your code repositories</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Add Repository</span>
        </button>
      </div>

      {/* Repository Form Modal */}
      {showForm && (
        <RepositoryForm
          projects={projects}
          onSubmit={handleRepositoryCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Repository Detail Modal */}
      {selectedRepoId && (
        <RepositoryDetail
          repositoryId={selectedRepoId}
          onClose={() => setSelectedRepoId(null)}
          onDelete={handleRepositoryDeleted}
        />
      )}

      <div className="space-y-4">
        {repositories.map((repo) => (
          <div key={repo.id} className="card p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{repo.name}</h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(repo.status)}`}>
                    {repo.status}
                  </span>
                  {repo.language && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                      {repo.language}
                    </span>
                  )}
                </div>
                <a 
                  href={repo.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 text-sm mb-3 inline-flex items-center space-x-1"
                >
                  <span>{repo.url}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
                <div className="flex items-center space-x-6 text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-4 h-4" />
                    <span>Last scan: {repo.last_scan ? new Date(repo.last_scan).toLocaleDateString() : 'Never'}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <AlertTriangle className="w-4 h-4" />
                    <span>{repo.vulnerabilities_count} vulnerabilities</span>
                  </div>
                  {repo.project_name && (
                    <span className="text-blue-600">{repo.project_name}</span>
                  )}
                </div>
              </div>
              <div className="flex space-x-2">
                <button className="btn-secondary text-sm" onClick={() => setSelectedRepoId(repo.id)}>View Details</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}