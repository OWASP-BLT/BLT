// API configuration for BLT
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Auth endpoints
  LOGIN: `${API_BASE_URL}/auth/`,
  REGISTER: `${API_BASE_URL}/auth/registration/`,
  LOGOUT: `${API_BASE_URL}/auth/logout/`,
  
  // Issue endpoints
  ISSUES: `${API_BASE_URL}/api/v1/issues/`,
  ISSUE_DETAIL: (id) => `${API_BASE_URL}/api/v1/issues/${id}/`,
  CREATE_ISSUE: `${API_BASE_URL}/api/v1/createissues/`,
  SEARCH_ISSUES: `${API_BASE_URL}/api/v1/search/`,
  
  // User endpoints
  PROFILE: `${API_BASE_URL}/api/v1/profile/`,
  USER_SCORE: `${API_BASE_URL}/api/v1/userscore/`,
  
  // Organization endpoints
  ORGANIZATIONS: `${API_BASE_URL}/api/v1/organizations/`,
  DOMAINS: `${API_BASE_URL}/api/v1/domain/`,
  
  // Leaderboard
  LEADERBOARD: `${API_BASE_URL}/api/v1/leaderboard/`,
  SCOREBOARD: `${API_BASE_URL}/api/v1/scoreboard/`,
  
  // Stats
  STATS: `${API_BASE_URL}/api/v1/stats/`,
};

export default API_BASE_URL;
