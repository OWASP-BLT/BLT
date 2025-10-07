import { useState, useEffect } from 'react';
import { X, Calendar, GitBranch, ExternalLink, AlertTriangle, Trash2, User } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import { useAuth } from '../contexts/AuthContext';
import type { Repository } from '../types';

interface RepositoryDetailProps {
  repositoryId: number;
  onClose: () => void;
  onDelete?: (repositoryId: number) => void;
}

export default function RepositoryDetail({ repositoryId, onClose, onDelete }: RepositoryDetailProps) {
  const { error: showError, success } = useNotification();
  const { user } = useAuth();
  const [repository, setRepository] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    loadRepository();
  }, [repositoryId]);

  const loadRepository = async () => {
    try {
      const response = await apiService.getRepository(repositoryId);
      setRepository(response.repository);
    } catch (error) {
      showError('Failed to load repository details', 'Please try again later');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!repository) return;
    setDeleting(true);
    try {
      await apiService.deleteRepository(repository.id);
      success('Repository deleted', `Repository "${repository.name}" has been deleted`);
      onDelete?.(repository.id);
      onClose();
    } catch (error) {
      showError('Failed to delete repository', 'Please try again');
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
            <span>Loading repository details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!repository) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">Repository Details</h2>
            <span className="text-sm text-gray-500">#{repository.id}</span>
          </div>
          <div className="flex items-center space-x-2">
            {user?.role === 'admin' && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete repository"
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
              <GitBranch className="w-6 h-6 text-blue-600" />
              <span>{repository.name}</span>
            </h1>
            {repository.url && (
              <a 
                href={repository.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 text-sm inline-flex items-center space-x-1"
              >
                <span>{repository.url}</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Created</div>
                <div className="text-sm font-medium">{new Date(repository.created_at).toLocaleDateString()}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Vulnerabilities</div>
                <div className="text-sm font-medium">{repository.vulnerabilities_count}</div>
              </div>
            </div>
            
            {repository.language && (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <div>
                  <div className="text-xs text-gray-500">Language</div>
                  <div className="text-sm font-medium">{repository.language}</div>
                </div>
              </div>
            )}
            
            {repository.project_name && (
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4 text-gray-500" />
                <div>
                  <div className="text-xs text-gray-500">Project</div>
                  <div className="text-sm font-medium">{repository.project_name}</div>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-gray-900">Status</h3>
            <div className="flex items-center space-x-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                repository.status === 'active' ? 'bg-green-100 text-green-800' :
                repository.status === 'scanning' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {repository.status}
              </span>
              {repository.last_scan && (
                <span className="text-sm text-gray-500">
                  Last scan: {new Date(repository.last_scan).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>Created: {new Date(repository.created_at).toLocaleString()}</span>
              {repository.updated_at && repository.updated_at !== repository.created_at && (
                <span>Last updated: {new Date(repository.updated_at).toLocaleString()}</span>
              )}
            </div>
          </div>
        </div>

        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-60 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center space-x-3 mb-4">
                <AlertTriangle className="w-6 h-6 text-red-600" />
                <h3 className="text-lg font-semibold text-gray-900">Delete Repository</h3>
              </div>
              <p className="text-gray-600 mb-6">
                Are you sure you want to delete "{repository.name}"? This action cannot be undone and will also delete all associated bugs.
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
                    'Delete Repository'
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