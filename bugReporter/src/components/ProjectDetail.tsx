import { useState, useEffect } from 'react';
import { X, Calendar, User, Tag, Bug, Trash2, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import type { Project } from '../types';

interface ProjectDetailProps {
  projectId: number;
  onClose: () => void;
  onDelete?: (projectId: number) => void;
}

export default function ProjectDetail({ projectId, onClose, onDelete }: ProjectDetailProps) {
  const { error: showError, success } = useNotification();
  const { user } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    try {
      const response = await apiService.getProject(projectId);
      setProject(response.project);
    } catch (error) {
      showError('Failed to load project details', 'Please try again later');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    setDeleting(true);
    try {
      await apiService.deleteProject(project.id);
      success('Project deleted', `Project "${project.name}" has been deleted`);
      onDelete?.(project.id);
      onClose();
    } catch (error) {
      showError('Failed to delete project', 'Please try again');
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            <span>Loading project details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">Project Details</h2>
            <span className="text-sm text-gray-500">#{project.id}</span>
          </div>
          <div className="flex items-center space-x-2">
            {user?.role === 'admin' && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete project"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
              <Tag className="w-6 h-6 text-blue-600" />
              <span>{project.name}</span>
            </h1>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Created by</div>
                <div className="text-sm font-medium">{(project as any).created_by_name || 'Unknown'}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Created</div>
                <div className="text-sm font-medium">{new Date(project.created_at).toLocaleDateString()}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Bug className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Bugs</div>
                <div className="text-sm font-medium">{(project as any).bugs_count || 0}</div>
              </div>
            </div>
          </div>

          {project.description && (
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Description</h3>
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 whitespace-pre-line">{project.description}</p>
              </div>
            </div>
          )}

          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>Created: {new Date(project.created_at).toLocaleString()}</span>
              {project.updated_at && project.updated_at !== project.created_at && (
                <span>Last updated: {new Date(project.updated_at).toLocaleString()}</span>
              )}
            </div>
          </div>
        </div>

        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-60 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center space-x-3 mb-4">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <h3 className="text-lg font-semibold text-gray-900">Delete Project</h3>
              </div>
              <p className="text-gray-600 mb-6">
                Are you sure you want to delete "{project.name}"? This action cannot be undone and will also delete associated repositories and bugs.
              </p>
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="btn-secondary"
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deleting ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Deleting...</span>
                    </div>
                  ) : (
                    'Delete Project'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}