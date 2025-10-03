import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import BugsPage from './pages/BugsPage';
import ProjectsPage from './pages/ProjectsPage';
import RepositoriesPage from './pages/RepositoriesPage';
import UserManagementPage from './pages/UserManagementPage';
import LoadingSpinner from './components/LoadingSpinner';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user || user.role !== 'admin') {
    return <Navigate to="/bugs" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <Routes>
      <Route 
        path="/login" 
        element={user ? <Navigate to="/bugs" replace /> : <LoginPage />} 
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/bugs" replace />} />
        <Route path="bugs" element={<BugsPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="repositories" element={<RepositoriesPage />} />
        <Route 
          path="users" 
          element={
            <AdminRoute>
              <UserManagementPage />
            </AdminRoute>
          } 
        />
      </Route>
      <Route path="*" element={<Navigate to="/bugs" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <Router>
          <AppRoutes />
        </Router>
      </NotificationProvider>
    </AuthProvider>
  );
}

export default App;
