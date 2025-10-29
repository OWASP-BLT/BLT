import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../services/api';
import { API_ENDPOINTS } from '../config/api';

const Dashboard = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [userIssues, setUserIssues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [profileRes, issuesRes] = await Promise.all([
        apiClient.get(API_ENDPOINTS.PROFILE),
        apiClient.get(`${API_ENDPOINTS.ISSUES}?user=me&limit=10`)
      ]);
      
      const profileData = profileRes.data.results?.[0] || profileRes.data;
      setUserInfo(profileData);
      setUserIssues(issuesRes.data.results || issuesRes.data || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: '#e74c3c' }}></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">
          Welcome back{userInfo?.username ? `, ${userInfo.username}` : ''}!
        </h1>
        <p className="text-body">Here's an overview of your activity</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-card p-6">
          <div className="text-body mb-2">Total Points</div>
          <div className="text-3xl font-bold" style={{ color: '#e74c3c' }}>
            {userInfo?.score || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-card p-6">
          <div className="text-body mb-2">Issues Reported</div>
          <div className="text-3xl font-bold" style={{ color: '#e74c3c' }}>
            {userIssues.length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-card p-6">
          <div className="text-body mb-2">Rank</div>
          <div className="text-3xl font-bold" style={{ color: '#e74c3c' }}>
            #{userInfo?.rank || '-'}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-card p-6 mb-8">
        <h2 className="text-2xl font-bold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/issues/new"
            className="p-4 border border-stroke rounded-lg hover:shadow-2 transition-shadow text-center"
          >
            <div className="text-2xl mb-2">🐛</div>
            <div className="font-semibold">Report Issue</div>
          </Link>
          <Link
            to="/issues"
            className="p-4 border border-stroke rounded-lg hover:shadow-2 transition-shadow text-center"
          >
            <div className="text-2xl mb-2">🔍</div>
            <div className="font-semibold">Browse Issues</div>
          </Link>
          <Link
            to="/leaderboard"
            className="p-4 border border-stroke rounded-lg hover:shadow-2 transition-shadow text-center"
          >
            <div className="text-2xl mb-2">🏆</div>
            <div className="font-semibold">View Leaderboard</div>
          </Link>
        </div>
      </div>

      {/* Recent Issues */}
      <div className="bg-white rounded-lg shadow-card p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Your Recent Issues</h2>
          <Link to="/issues?user=me" className="text-sm font-semibold hover:underline" style={{ color: '#e74c3c' }}>
            View All
          </Link>
        </div>
        
        {userIssues.length === 0 ? (
          <div className="text-center py-8 text-body">
            <p>You haven't reported any issues yet.</p>
            <Link to="/issues/new" className="inline-block mt-4 font-semibold hover:underline" style={{ color: '#e74c3c' }}>
              Report your first issue →
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {userIssues.slice(0, 5).map((issue) => (
              <div key={issue.id} className="border border-stroke rounded-lg p-4 hover:shadow-2 transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold mb-1">
                      {issue.title || issue.description || 'Untitled Issue'}
                    </h3>
                    <p className="text-sm text-body line-clamp-2">
                      {issue.description || 'No description'}
                    </p>
                  </div>
                  <Link
                    to={`/issues/${issue.id}`}
                    className="ml-4 font-semibold text-sm hover:underline"
                    style={{ color: '#e74c3c' }}
                  >
                    View →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
