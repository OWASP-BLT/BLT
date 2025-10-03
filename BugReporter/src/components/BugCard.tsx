import { useState } from 'react';
import { Calendar, User, AlertTriangle, CheckCircle, Clock, XCircle, Edit, Eye } from 'lucide-react';
import clsx from 'clsx';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import BugDetail from './BugDetail';
import type { Bug } from '../types';

interface BugCardProps {
  bug: Bug;
  onUpdate: (bug: Bug) => void;
  canEdit: boolean;
}

export default function BugCard({ bug, onUpdate, canEdit }: BugCardProps) {
  const { success, error: showError } = useNotification();
  const [isEditing, setIsEditing] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [status, setStatus] = useState<Bug['status']>(bug.status);
  const [loading, setLoading] = useState(false);

  const handleStatusChange = async (newStatus: Bug['status']) => {
    if (!canEdit) return;
    setLoading(true);
    try {
      const response = await apiService.updateBug(bug.id, { status: newStatus as Bug['status'] });
      onUpdate(response.bug);
      setStatus(newStatus);
      setIsEditing(false);
      success('Status updated', `Bug status changed to ${newStatus.replace('_', ' ')}`);
    } catch (error) {
      showError('Failed to update status', 'Please try again later');
    } finally {
      setLoading(false);
    }
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't open detail if clicking on buttons or interactive elements
    if ((e.target as HTMLElement).closest('button, select, a')) {
      return;
    }
    setShowDetail(true);
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
      case 'open': return 'bg-blue-100 text-blue-800 border-blue-200';
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

  return (
    <>
      <div 
        className="card p-6 cursor-pointer hover:shadow-lg hover:border-primary-200 transition-all duration-200 transform hover:-translate-y-1"
        onClick={handleCardClick}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <h3 className="text-lg font-semibold text-gray-900 hover:text-primary-600 transition-colors">{bug.title}</h3>
              <span className={clsx('px-2 py-1 rounded-full text-xs font-medium border', getSeverityColor(bug.severity))}>
                {bug.severity}
              </span>
              <span className={clsx('px-2 py-1 rounded-full text-xs font-medium border flex items-center space-x-1', getStatusColor(bug.status))}>
                {getStatusIcon(bug.status)}
                <span className="capitalize">{bug.status.replace('_', ' ')}</span>
              </span>
            </div>
          
            {bug.description && (
              <p className="text-gray-600 mb-3">{bug.description}</p>
            )}

            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <User className="w-4 h-4" />
                <span>{bug.reporter_name || bug.reporter_email}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Calendar className="w-4 h-4" />
                <span>{new Date(bug.created_at).toLocaleDateString()}</span>
              </div>
              {bug.project_name && (
                <div className="flex items-center space-x-1">
                  <span className="text-blue-600">{bug.project_name}</span>
                </div>
              )}
              {bug.repository_name && (
                <div className="flex items-center space-x-1">
                  <span className="text-purple-600">{bug.repository_name}</span>
                </div>
              )}
            </div>
          </div>

          {canEdit && (
            <div className="flex items-center space-x-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditing(!isEditing);
                }}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="Edit status"
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowDetail(true);
                }}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="View details"
              >
                <Eye className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Quick preview of additional details */}
        {(bug.steps_to_reproduce || bug.expected_behavior || bug.actual_behavior) && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              {bug.steps_to_reproduce && (
                <div className="mb-2">
                  <span className="font-medium">Steps:</span> {bug.steps_to_reproduce.substring(0, 100)}
                  {bug.steps_to_reproduce.length > 100 && '...'}
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">Click to view full details</span>
                <Eye className="w-3 h-3 text-gray-400" />
              </div>
            </div>
          </div>
        )}

        {/* Status Update */}
        {isEditing && canEdit && (
          <div className="border-t border-gray-200 pt-4 mt-4">
            <div className="flex items-center space-x-3">
              <label className="text-sm font-medium text-gray-700">Status:</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as Bug['status'])}
                className="input-field w-auto"
                disabled={loading}
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
              <button
                onClick={() => handleStatusChange(status)}
                disabled={loading || status === bug.status}
                className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center space-x-1">
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                    <span>Updating...</span>
                  </div>
                ) : (
                  'Update'
                )}
              </button>
              <button
                onClick={() => {
                  setIsEditing(false);
                  setStatus(bug.status);
                }}
                className="btn-secondary text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bug Detail Modal */}
      {showDetail && (
        <BugDetail
          bugId={bug.id}
          onClose={() => setShowDetail(false)}
          canEdit={canEdit}
        />
      )}
    </>
  );
}