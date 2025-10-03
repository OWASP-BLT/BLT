import { useState, useRef } from 'react';
import { X, Upload, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import type { Bug, Project, Repository } from '../types';

interface BugFormProps {
  projects: Project[];
  repositories: Repository[];
  onSubmit: (bug: Bug) => void;
  onCancel: () => void;
}

export default function BugForm({ projects, repositories, onSubmit, onCancel }: BugFormProps) {
  const { success, error: showError } = useNotification();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    severity: 'medium' as const,
    project_id: '',
    repository_id: '',
    project_name: '',
    repository_name: '',
    steps_to_reproduce: '',
    expected_behavior: '',
    actual_behavior: '',
    screenshot_url: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [useCustomProject, setUseCustomProject] = useState(false);
  const [useCustomRepository, setUseCustomRepository] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let projectId = formData.project_id ? parseInt(formData.project_id) : undefined;
      let repositoryId = formData.repository_id ? parseInt(formData.repository_id) : undefined;

      if (useCustomProject && formData.project_name.trim()) {
        try {
          const projectResponse = await apiService.findOrCreateProject(formData.project_name.trim());
          projectId = projectResponse.project.id;
          success('Project created successfully', `Project "${formData.project_name}" is ready to use`);
        } catch (err) {
          if (err instanceof Error && err.message.includes('already exists')) {
            showError('Project already exists', 'A project with this name already exists. Please choose a different name.');
            return;
          }
          throw err;
        }
      }

      if (useCustomRepository && formData.repository_name.trim() && projectId) {
        try {
          const repoResponse = await apiService.findOrCreateRepository(
            formData.repository_name.trim(),
            projectId
          );
          repositoryId = repoResponse.repository.id;
          success('Repository created successfully', `Repository "${formData.repository_name}" is ready to use`);
        } catch (err) {
          if (err instanceof Error && err.message.includes('already exists')) {
            showError('Repository already exists', 'A repository with this name already exists in this project.');
            return;
          }
          throw err;
        }
      }

      const bugData = {
        title: formData.title,
        description: formData.description,
        severity: formData.severity,
        steps_to_reproduce: formData.steps_to_reproduce,
        expected_behavior: formData.expected_behavior,
        actual_behavior: formData.actual_behavior,
        screenshot_url: formData.screenshot_url,
        project_id: projectId,
        repository_id: repositoryId,
      };

      const response = await apiService.createBug(bugData);
      success('Bug reported successfully', 'Your bug report has been created and is now visible to all users');
      onSubmit(response.bug);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create bug';
      setError(errorMessage);
      showError('Failed to create bug', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleProjectSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === '__custom__') {
      setUseCustomProject(true);
      setFormData(prev => ({ ...prev, project_id: '', repository_id: '' }));
    } else {
      setUseCustomProject(false);
      setFormData(prev => ({ ...prev, project_id: value, project_name: '', repository_id: '' }));
    }
  };

  const handleRepositorySelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === '__custom__') {
      setUseCustomRepository(true);
      setFormData(prev => ({ ...prev, repository_id: '' }));
    } else {
      setUseCustomRepository(false);
      setFormData(prev => ({ ...prev, repository_id: value, repository_name: '' }));
    }
  };

  const triggerFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleFileChosen = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const { url } = await apiService.uploadFile(file);
      setFormData(prev => ({ ...prev, screenshot_url: url }));
      success('Upload successful', 'Screenshot uploaded');
    } catch (err) {
      showError('Upload failed', err instanceof Error ? err.message : 'Could not upload file');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const filteredRepositories = repositories.filter(repo => 
    !formData.project_id || repo.project_id.toString() === formData.project_id
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Report a Bug</h2>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bug Title *
              </label>
              <input
                type="text"
                name="title"
                required
                value={formData.title}
                onChange={handleInputChange}
                className="input-field"
                placeholder="Brief description of the bug"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity *
              </label>
              <select
                name="severity"
                required
                value={formData.severity}
                onChange={handleInputChange}
                className="input-field"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Project
              </label>
              <select
                name="project_id"
                value={useCustomProject ? '__custom__' : formData.project_id}
                onChange={handleProjectSelect}
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

            <div className="md:col-span-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Repository
              </label>
              <select
                name="repository_id"
                value={useCustomRepository ? '__custom__' : formData.repository_id}
                onChange={handleRepositorySelect}
                className="input-field"
                disabled={!useCustomProject && !formData.project_id}
              >
                <option value="">Select a repository</option>
                {filteredRepositories.map((repo) => (
                  <option key={repo.id} value={repo.id}>
                    {repo.name}
                  </option>
                ))}
                {(useCustomProject || formData.project_id) && (
                  <option value="__custom__">Custom...</option>
                )}
              </select>
              {useCustomRepository && (
                <input
                  type="text"
                  name="repository_name"
                  value={formData.repository_name}
                  onChange={handleInputChange}
                  className="input-field mt-2"
                  placeholder="Enter new repository name"
                  required
                />
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              rows={4}
              className="input-field"
              placeholder="Detailed description of the bug"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Steps to Reproduce
            </label>
            <textarea
              name="steps_to_reproduce"
              value={formData.steps_to_reproduce}
              onChange={handleInputChange}
              rows={3}
              className="input-field"
              placeholder="1. Go to...&#10;2. Click on...&#10;3. See error"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Expected Behavior
              </label>
              <textarea
                name="expected_behavior"
                value={formData.expected_behavior}
                onChange={handleInputChange}
                rows={3}
                className="input-field"
                placeholder="What should happen?"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Actual Behavior
              </label>
              <textarea
                name="actual_behavior"
                value={formData.actual_behavior}
                onChange={handleInputChange}
                rows={3}
                className="input-field"
                placeholder="What actually happened?"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Screenshot URL
            </label>
            <div className="flex space-x-2">
              <input
                type="url"
                name="screenshot_url"
                value={formData.screenshot_url}
                onChange={handleInputChange}
                className="input-field"
                placeholder="https://example.com/screenshot.png"
              />
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChosen} />
              <button
                type="button"
                className="btn-secondary flex items-center space-x-2"
                onClick={triggerFilePicker}
              >
                <Upload className="w-4 h-4" />
                <span>Upload</span>
              </button>
            </div>
          </div>

          <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
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
                  <span>Creating...</span>
                </div>
              ) : (
                'Create Bug Report'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}