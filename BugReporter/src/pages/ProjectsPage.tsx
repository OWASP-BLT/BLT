import { useState, useEffect, useCallback } from 'react';
import { Plus, FolderOpen, Calendar, Bug, Eye } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import type { Project } from '../types';
import ProjectForm from '../components/ProjectForm';
import ProjectDetail from '../components/ProjectDetail';
import SearchAndFilter from '../components/SearchAndFilter';

export default function ProjectsPage() {
  const { success } = useNotification();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [searchParams, setSearchParams] = useState<{
    search?: string;
    status?: string;
  }>({});

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.getProjects(searchParams);
      setProjects(response.projects);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  }, [searchParams]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleProjectCreated = (newProject: Project) => {
    setProjects(prev => [newProject, ...prev]);
    setShowForm(false);
    success('Project created successfully', `Project "${newProject.name}" has been created`);
  };

  const handleProjectDeleted = (projectId: number) => {
    setProjects(prev => prev.filter(p => p.id !== projectId));
    setSelectedProjectId(null);
  };

  const handleProjectClick = (projectId: number) => {
    setSelectedProjectId(projectId);
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
        { label: 'Active', value: 'active' },
        { label: 'Inactive', value: 'inactive' },
        { label: 'Archived', value: 'archived' }
      ]
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 border-green-200';
      case 'inactive': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'archived': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-1">Manage your security testing projects</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create Project</span>
        </button>
      </div>

      {/* Project Form Modal */}
      {showForm && (
        <ProjectForm
          onSubmit={handleProjectCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Project Detail Modal */}
      {selectedProjectId && (
        <ProjectDetail
          projectId={selectedProjectId}
          onClose={() => setSelectedProjectId(null)}
          onDelete={handleProjectDeleted}
        />
      )}

      <SearchAndFilter
        searchPlaceholder="Search projects by name, description, or creator..."
        onSearchChange={handleSearchChange}
        onFilterChange={handleFilterChange}
        filters={filterOptions}
        initialSearch={searchParams.search}
        initialFilters={{
          status: searchParams.status || ''
        }}
      />

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.length === 0 ? (
          <div className="col-span-full text-center py-12">
            <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No projects found</h3>
            <p className="text-gray-600 mb-4">Create your first project to get started with bug tracking.</p>
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary"
            >
              Create Project
            </button>
          </div>
        ) : (
          projects.map((project) => (
            <div 
              key={project.id} 
              className="card p-6 cursor-pointer hover:shadow-lg hover:border-primary-200 transition-all duration-200 transform hover:-translate-y-1"
              onClick={() => handleProjectClick(project.id)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 hover:text-primary-600 transition-colors">{project.name}</h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(project.status || 'active')}`}>
                    {project.status || 'active'}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <FolderOpen className="w-6 h-6 text-gray-400" />
                  <Eye className="w-4 h-4 text-gray-400" />
                </div>
              </div>
              
              {project.description && (
                <p className="text-gray-600 text-sm mb-4 line-clamp-2">{project.description}</p>
              )}
              
              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(project.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Bug className="w-4 h-4" />
                  <span>{(project as any).bugs_count || 0} bugs</span>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                    Click to view details
                  </span>
                  <Eye className="w-3 h-3 text-gray-400" />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}