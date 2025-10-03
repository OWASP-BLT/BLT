import { NavLink } from 'react-router-dom';
import { X, Bug, FolderOpen, GitBranch, Users } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import clsx from 'clsx';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navigation = [
  { name: 'Bugs', href: '/bugs', icon: Bug },
  { name: 'Projects', href: '/projects', icon: FolderOpen },
  { name: 'Repositories', href: '/repositories', icon: GitBranch },
];

const adminNavigation = [
  { name: 'User Management', href: '/users', icon: Users },
];

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { isAdmin } = useAuth();

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside className={clsx(
        'fixed top-0 left-0 h-full w-64 bg-white border-r border-gray-200 z-50 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-auto',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="p-4 pt-20 lg:pt-4">
          {/* Close button for mobile */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100 lg:hidden"
          >
            <X className="w-6 h-6" />
          </button>

          {/* Main Navigation */}
          <div className="mb-8">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Main
            </h3>
            <nav className="space-y-1">
              {navigation.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  onClick={onClose}
                  className={({ isActive }) =>
                    clsx(
                      'sidebar-item',
                      isActive ? 'sidebar-item-active' : 'sidebar-item-inactive'
                    )
                  }
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </NavLink>
              ))}
            </nav>
          </div>

          {/* Admin Navigation */}
          {isAdmin && (
            <div className="mb-8">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Admin
              </h3>
              <nav className="space-y-1">
                {adminNavigation.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    onClick={onClose}
                    className={({ isActive }) =>
                      clsx(
                        'sidebar-item',
                        isActive ? 'sidebar-item-active' : 'sidebar-item-inactive'
                      )
                    }
                  >
                    <item.icon className="mr-3 h-5 w-5" />
                    {item.name}
                  </NavLink>
                ))}
              </nav>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
