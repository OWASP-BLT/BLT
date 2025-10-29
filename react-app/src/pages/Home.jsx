import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import apiClient from '../services/api';
import { API_ENDPOINTS } from '../config/api';

const Home = () => {
  const [stats, setStats] = useState({ issues: 0, users: 0, organizations: 0 });
  const [recentIssues, setRecentIssues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, issuesRes] = await Promise.all([
          apiClient.get(API_ENDPOINTS.STATS),
          apiClient.get(`${API_ENDPOINTS.ISSUES}?limit=6`)
        ]);
        
        setStats(statsRes.data || { issues: 0, users: 0, organizations: 0 });
        setRecentIssues(issuesRes.data.results || issuesRes.data || []);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div>
      {/* Hero Section */}
      <section className="py-20 px-4" style={{ backgroundColor: '#e74c3c' }}>
        <div className="container mx-auto text-center text-white">
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            Make the Web More Secure
          </h1>
          <p className="text-xl md:text-2xl mb-8 opacity-90">
            Report bugs, earn points, and contribute to a safer internet
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/issues"
              className="px-8 py-3 bg-white rounded-lg font-semibold transition-transform hover:scale-105"
              style={{ color: '#e74c3c' }}
            >
              Browse Issues
            </Link>
            <Link
              to="/register"
              className="px-8 py-3 bg-transparent border-2 border-white text-white rounded-lg font-semibold hover:bg-white transition-colors"
              style={{ '--hover-color': '#e74c3c' }}
              onMouseEnter={(e) => e.target.style.color = '#e74c3c'}
              onMouseLeave={(e) => e.target.style.color = 'white'}
            >
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 bg-gray-2">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6 bg-white rounded-lg shadow-card">
              <div className="text-4xl font-bold mb-2" style={{ color: '#e74c3c' }}>
                {loading ? '...' : stats.issues || '1000+'}
              </div>
              <div className="text-body">Issues Reported</div>
            </div>
            <div className="text-center p-6 bg-white rounded-lg shadow-card">
              <div className="text-4xl font-bold mb-2" style={{ color: '#e74c3c' }}>
                {loading ? '...' : stats.users || '500+'}
              </div>
              <div className="text-body">Active Users</div>
            </div>
            <div className="text-center p-6 bg-white rounded-lg shadow-card">
              <div className="text-4xl font-bold mb-2" style={{ color: '#e74c3c' }}>
                {loading ? '...' : stats.organizations || '100+'}
              </div>
              <div className="text-body">Organizations</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-12">
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center text-white text-2xl font-bold" style={{ backgroundColor: '#e74c3c' }}>
                1
              </div>
              <h3 className="text-xl font-semibold mb-3">Report Issues</h3>
              <p className="text-body">
                Found a bug on any website? Report it on BLT and help make the web better.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center text-white text-2xl font-bold" style={{ backgroundColor: '#e74c3c' }}>
                2
              </div>
              <h3 className="text-xl font-semibold mb-3">Earn Points</h3>
              <p className="text-body">
                Get points for verified bugs and climb the leaderboard.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center text-white text-2xl font-bold" style={{ backgroundColor: '#e74c3c' }}>
                3
              </div>
              <h3 className="text-xl font-semibold mb-3">Make Impact</h3>
              <p className="text-body">
                Help organizations fix bugs and improve their security posture.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Recent Issues */}
      <section className="py-16 px-4 bg-gray-2">
        <div className="container mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-3xl font-bold">Recent Issues</h2>
            <Link to="/issues" className="font-semibold hover:underline" style={{ color: '#e74c3c' }}>
              View All →
            </Link>
          </div>
          
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: '#e74c3c' }}></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {recentIssues.slice(0, 6).map((issue) => (
                <div key={issue.id} className="bg-white rounded-lg shadow-card p-6 hover:shadow-2 transition-shadow">
                  <h3 className="font-semibold mb-2 line-clamp-2">{issue.title || issue.description || 'Untitled Issue'}</h3>
                  <p className="text-sm text-body mb-4 line-clamp-3">
                    {issue.description || 'No description provided'}
                  </p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-body">
                      {issue.user || 'Anonymous'}
                    </span>
                    <Link
                      to={`/issues/${issue.id}`}
                      className="font-semibold hover:underline"
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
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4" style={{ backgroundColor: '#e74c3c' }}>
        <div className="container mx-auto text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Get Started?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join the community and start reporting bugs today
          </p>
          <Link
            to="/register"
            className="inline-block px-8 py-3 bg-white rounded-lg font-semibold transition-transform hover:scale-105"
            style={{ color: '#e74c3c' }}
          >
            Create Free Account
          </Link>
        </div>
      </section>
    </div>
  );
};

export default Home;
