import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../services/api';
import { API_ENDPOINTS } from '../config/api';

const Issues = () => {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    fetchIssues();
  }, [page]);

  const fetchIssues = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`${API_ENDPOINTS.ISSUES}?page=${page}&limit=20`);
      const data = response.data.results || response.data || [];
      
      if (page === 1) {
        setIssues(data);
      } else {
        setIssues(prev => [...prev, ...data]);
      }
      
      setHasMore(response.data.next != null);
    } catch (error) {
      console.error('Error fetching issues:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">All Issues</h1>
        <p className="text-body">Browse reported bugs and security issues</p>
      </div>

      {loading && page === 1 ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: '#e74c3c' }}></div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {issues.map((issue) => (
              <div key={issue.id} className="bg-white rounded-lg shadow-card p-6 hover:shadow-2 transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-lg line-clamp-2 flex-1">
                    {issue.title || issue.description || 'Untitled Issue'}
                  </h3>
                  {issue.verified && (
                    <span className="ml-2 px-2 py-1 bg-success bg-opacity-10 text-success text-xs rounded-full">
                      Verified
                    </span>
                  )}
                </div>
                
                <p className="text-sm text-body mb-4 line-clamp-3">
                  {issue.description || 'No description provided'}
                </p>
                
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center space-x-4">
                    <span className="text-body">
                      By {issue.user || 'Anonymous'}
                    </span>
                    {issue.domain && (
                      <span className="text-body">
                        {issue.domain}
                      </span>
                    )}
                  </div>
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

          {hasMore && (
            <div className="text-center mt-8">
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={loading}
                className="px-6 py-3 rounded-lg text-white font-semibold transition-colors disabled:opacity-50"
                style={{ backgroundColor: '#e74c3c' }}
                onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#c0392b')}
                onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#e74c3c')}
              >
                {loading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Issues;
