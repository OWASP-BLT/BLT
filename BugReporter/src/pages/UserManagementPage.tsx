import { useState, useEffect } from 'react';
import { Users, Calendar, Bug, Edit, Trash2, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';
import type { User } from '../types';

export default function UserManagementPage() {
  const { success, error: showError } = useNotification();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState<'admin' | 'user'>('user');
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await apiService.getUsers();
      setUsers(response.users);
    } catch (error) {
      showError('Failed to load users', 'Please try refreshing the page');
    } finally {
      setLoading(false);
    }
  };

  const handleEditUser = (userId: number) => {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    setEditingUser(user);
    setEditRole(user.role as 'admin' | 'user');
  };

  const submitEditUser = async () => {
    if (!editingUser) return;
    setActionLoading(editingUser.id);
    try {
      const { user } = await apiService.updateUser(editingUser.id, { role: editRole } as Partial<User>);
      setUsers(prev => prev.map(u => u.id === user.id ? user : u));
      success('User updated', 'Role has been updated');
      setEditingUser(null);
    } catch (error) {
      showError('Failed to update user', 'Please try again');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteUser = (userId: number) => {
    const user = users.find(u => u.id === userId) || null;
    setDeleteTarget(user);
  };

  const confirmDeleteUser = async () => {
    if (!deleteTarget) return;
    setActionLoading(deleteTarget.id);
    try {
      await apiService.deleteUser(deleteTarget.id);
      setUsers(prev => prev.filter(u => u.id !== deleteTarget.id));
      success('User deleted', 'The user has been removed');
      setDeleteTarget(null);
    } catch (error) {
      showError('Failed to delete user', 'Please try again');
    } finally {
      setActionLoading(null);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800';
      case 'user': return 'bg-gray-100 text-gray-800';
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
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-600 mt-1">Manage users and their permissions</p>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">All Users</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Bugs Reported
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        {user.avatar_url ? (
                          <img className="h-10 w-10 rounded-full" src={user.avatar_url} alt="" />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                            <Users className="h-5 w-5 text-primary-600" />
                          </div>
                        )}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{user.name}</div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-900">
                      <Bug className="w-4 h-4 mr-1" />
                      {(user as any).bugs_reported || 0}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center text-sm text-gray-500">
                      <Calendar className="w-4 h-4 mr-1" />
                      {new Date(user.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button 
                        onClick={() => handleEditUser(user.id)}
                        disabled={actionLoading === user.id}
                        className="text-blue-600 hover:text-blue-700 disabled:opacity-50 flex items-center space-x-1 transition-colors"
                      >
                        <Edit className="w-3 h-3" />
                        <span>Edit</span>
                      </button>
                      <button 
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={actionLoading === user.id}
                        className="text-red-600 hover:text-red-700 disabled:opacity-50 flex items-center space-x-1 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Role Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Edit User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                <select
                  className="input-field"
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value as 'admin' | 'user')}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex justify-end space-x-3">
                <button className="btn-secondary" onClick={() => setEditingUser(null)}>Cancel</button>
                <button className="btn-primary" onClick={submitEditUser} disabled={actionLoading === editingUser.id}>
                  {actionLoading === editingUser.id ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex items-center space-x-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-red-600" />
              <h3 className="text-lg font-semibold text-gray-900">Delete User</h3>
            </div>
            <p className="text-gray-600 mb-6">Are you sure you want to delete {deleteTarget.name}? This action cannot be undone.</p>
            <div className="flex justify-end space-x-3">
              <button className="btn-secondary" onClick={() => setDeleteTarget(null)} disabled={actionLoading === deleteTarget.id}>Cancel</button>
              <button className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed" onClick={confirmDeleteUser} disabled={actionLoading === deleteTarget.id}>
                {actionLoading === deleteTarget.id ? 'Deleting...' : 'Delete User'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}