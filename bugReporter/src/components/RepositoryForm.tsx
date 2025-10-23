import { useState } from 'react';
import { X, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';
import type { Repository, Project } from '../types';

interface RepositoryFormProps {
  projects: Project[];
  onSubmit: (repository: Repository) => void;
  onCancel: () => void;
}

export default function RepositoryForm({ projects, onSubmit, onCancel }: RepositoryFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    language: '',
    project_id: '',
    project_name: '',
  });
  const [useCustomProject, setUseCustomProject] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let projectId = formData.project_id ? parseInt(formData.project_id) : undefined;

      if (useCustomProject && formData.project_name.trim()) {
        const projectResponse = await apiService.findOrCreateProject(formData.project_name.trim());
        projectId = projectResponse.project.id;
      }

      const repoData = {
        name: formData.name,
        url: formData.url,
        language: formData.language,
        project_id: projectId,
      } as Partial<Repository>;

      const response = await apiService.createRepository(repoData);
      onSubmit(response.repository);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create repository');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === 'project_id') {
      if (value === '__custom__') {
        setUseCustomProject(true);
        setFormData(prev => ({ ...prev, project_id: '' }));
      } else {
        setUseCustomProject(false);
        setFormData(prev => ({ ...prev, project_id: value, project_name: '' }));
      }
      return;
    }
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Add New Repository</h2>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Repository Name *
            </label>
            <input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleInputChange}
              className="input-field"
              placeholder="e.g., owner/repository-name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Repository URL *
            </label>
            <input
              type="url"
              name="url"
              required
              value={formData.url}
              onChange={handleInputChange}
              className="input-field"
              placeholder="https://github.com/owner/repository"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Primary Language
            </label>
            <input
              type="text"
              name="language"
              value={formData.language}
              onChange={handleInputChange}
              className="input-field"
              placeholder="e.g., JavaScript, Python, Java"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Project *
            </label>
            <select
              name="project_id"
              required={!useCustomProject}
              value={useCustomProject ? '__custom__' : formData.project_id}
              onChange={handleInputChange}
              className="input-field"
            >
              <option value="">Select a project</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
              <option value="__custom__">Custom...</option>
            </select>
            {useCustomProject && (
              <input
                type="text"
                name="project_name"
                value={formData.project_name}
                onChange={handleInputChange}
                className="input-field mt-2"
                placeholder="Enter new project name"
                required
              />
            )}
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Adding...</span>
                </div>
              ) : (
                'Add Repository'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}