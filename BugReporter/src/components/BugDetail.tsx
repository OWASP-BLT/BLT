import { useState, useEffect } from 'react';
import { X, Calendar, User, AlertTriangle, CheckCircle, Clock, XCircle, Edit, ExternalLink, Tag, GitBranch } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import type { Bug } from '../types';
import clsx from 'clsx';

interface BugDetailProps {
  bugId: number;
  onClose: () => void;
  canEdit: boolean;
}

export default function BugDetail({ bugId, onClose, canEdit }: BugDetailProps) {
  const { success, error: showError } = useNotification();
  const [bug, setBug] = useState<Bug | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [status, setStatus] = useState<Bug['status']>('open');
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadBug();
  }, [bugId]);

  const loadBug = async () => {
    try {
      const response = await apiService.getBug(bugId);
      setBug(response.bug);
      setStatus(response.bug.status);
    } catch (error) {
      showError('Failed to load bug details', 'Please try again later');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async () => {
    if (!bug || status === bug.status) return;
    
    setUpdating(true);
    try {
      const response = await apiService.updateBug(bug.id, { status: status as Bug['status'] });
      setBug(response.bug);
      setIsEditing(false);
      success('Status updated', `Bug status changed to ${status.replace('_', ' ')}`);
    } catch (error) {
      showError('Failed to update status', 'Please try again');
      setStatus(bug.status); // Reset to original status
    } finally {
      setUpdating(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-red-100 text-red-800 border-red-200';
      case 'in_progress': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'resolved': return 'bg-green-100 text-green-800 border-green-200';
      case 'closed': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'open': return <AlertTriangle className="w-4 h-4" />;
      case 'in_progress': return <Clock className="w-4 h-4" />;
      case 'resolved': return <CheckCircle className="w-4 h-4" />;
      case 'closed': return <XCircle className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            <span>Loading bug details...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!bug) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-semibold text-gray-900">Bug Details</h2>
            <span className="text-sm text-gray-500">#{bug.id}</span>
          </div>
          <div className="flex items-center space-x-2">
            {canEdit && (
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Edit className="w-4 h-4" />
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
          {/* Title and Status */}
          <div className="space-y-4">
            <h1 className="text-2xl font-bold text-gray-900">{bug.title}</h1>
            
            <div className="flex items-center space-x-3">
              <span className={clsx('px-3 py-1 rounded-full text-sm font-medium border', getSeverityColor(bug.severity))}>
                <Tag className="w-3 h-3 inline mr-1" />
                {bug.severity} severity
              </span>
              
              {isEditing && canEdit ? (
                <div className="flex items-center space-x-2">
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as Bug['status'])}
                    className="input-field text-sm py-1"
                    disabled={updating}
                  >
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>
                  <button
                    onClick={handleStatusUpdate}
                    disabled={updating || status === bug.status}
                    className="btn-primary text-sm py-1 px-3 disabled:opacity-50"
                  >
                    {updating ? 'Updating...' : 'Update'}
                  </button>
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setStatus(bug.status);
                    }}
                    className="btn-secondary text-sm py-1 px-3"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <span className={clsx('px-3 py-1 rounded-full text-sm font-medium border flex items-center space-x-1', getStatusColor(bug.status))}>
                  {getStatusIcon(bug.status)}
                  <span className="capitalize">{bug.status.replace('_', ' ')}</span>
                </span>
              )}
            </div>
          </div>

          {/* Meta Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <User className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Reporter</div>
                <div className="text-sm font-medium">{bug.reporter_name || bug.reporter_email}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <div>
                <div className="text-xs text-gray-500">Created</div>
                <div className="text-sm font-medium">{new Date(bug.created_at).toLocaleDateString()}</div>
              </div>
            </div>
            
            {bug.project_name && (
              <div className="flex items-center space-x-2">
                <Tag className="w-4 h-4 text-gray-500" />
                <div>
                  <div className="text-xs text-gray-500">Project</div>
                  <div className="text-sm font-medium text-blue-600">{bug.project_name}</div>
                </div>
              </div>
            )}
            
            {bug.repository_name && (
              <div className="flex items-center space-x-2">
                <GitBranch className="w-4 h-4 text-gray-500" />
                <div>
                  <div className="text-xs text-gray-500">Repository</div>
                  <div className="text-sm font-medium text-purple-600">{bug.repository_name}</div>
                </div>
              </div>
            )}
          </div>

          {/* Description */}
          {bug.description && (
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900">Description</h3>
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 whitespace-pre-line">{bug.description}</p>
              </div>
            </div>
          )}

          {/* Detailed Information */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {bug.steps_to_reproduce && (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-900">Steps to Reproduce</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-line font-sans">{bug.steps_to_reproduce}</pre>
                </div>
              </div>
            )}

            {bug.expected_behavior && (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-900">Expected Behavior</h3>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-gray-700">{bug.expected_behavior}</p>
                </div>
              </div>
            )}

            {bug.actual_behavior && (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-900">Actual Behavior</h3>
                <div className="bg-red-50 rounded-lg p-4">
                  <p className="text-sm text-gray-700">{bug.actual_behavior}</p>
                </div>
              </div>
            )}

            {bug.screenshot_url && (
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-900">Screenshot</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <a
                    href={bug.screenshot_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-700 flex items-center space-x-2 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>View Screenshot</span>
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Timestamps */}
          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>Created: {new Date(bug.created_at).toLocaleString()}</span>
              {bug.updated_at && bug.updated_at !== bug.created_at && (
                <span>Last updated: {new Date(bug.updated_at).toLocaleString()}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}