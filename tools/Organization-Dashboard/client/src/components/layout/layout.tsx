import React, { useState } from 'react';
import { Link, useLocation } from 'wouter';
import { 
  BarChart, 
  Shield, 
  Bug, 
  Users, 
  Activity, 
  Settings,
  Menu,
  X
} from 'lucide-react';
import { NotificationsIndicator } from '@/components/ui/notifications';
import { useWebSocketContext } from '@/contexts/websocket-context';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

interface LayoutProps {
  children: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    href: '/',
    label: 'Dashboard',
    icon: <BarChart className="h-5 w-5" />
  },
  {
    href: '/security-issues',
    label: 'Security Issues',
    icon: <Shield className="h-5 w-5" />
  },
  {
    href: '/bug-reports',
    label: 'Bug Reports',
    icon: <Bug className="h-5 w-5" />
  },
  {
    href: '/contributors',
    label: 'Contributors',
    icon: <Users className="h-5 w-5" />
  },
  {
    href: '/activity',
    label: 'Activity',
    icon: <Activity className="h-5 w-5" />
  },
  {
    href: '/settings',
    label: 'Settings',
    icon: <Settings className="h-5 w-5" />
  }
];

export function Layout({ children }: LayoutProps) {
  const [location] = useLocation();
  const { connected } = useWebSocketContext();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };
  
  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}
      
      {/* Sidebar */}
      <aside 
        className={cn(
          "fixed inset-y-0 left-0 z-30 w-64 transform bg-white dark:bg-gray-950 shadow-lg lg:shadow-none transition-transform lg:translate-x-0 lg:static lg:inset-auto",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-800">
          <Link href="/" className="flex items-center space-x-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="text-lg font-semibold">SecureDash</span>
          </Link>
          <button 
            className="p-1.5 rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden"
            onClick={toggleSidebar}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <Link 
              key={item.href} 
              href={item.href}
              className={cn(
                "flex items-center px-4 py-2.5 text-sm font-medium rounded-md transition-colors",
                location === item.href 
                  ? "bg-primary/10 text-primary" 
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              )}
            >
              <span className="mr-3">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        
        <div className="absolute bottom-0 w-full p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="flex items-center space-x-3 px-4 py-2">
            <div className={cn(
              "w-2.5 h-2.5 rounded-full",
              connected ? "bg-green-500" : "bg-gray-400",
              connected && "animate-pulse"
            )}></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {connected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </aside>
      
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white dark:bg-gray-950 shadow-sm border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between h-16 px-4">
            <button 
              className="p-2 rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 lg:hidden"
              onClick={toggleSidebar}
            >
              <Menu className="h-5 w-5" />
            </button>
            
            <div className="flex items-center space-x-3">
              <NotificationsIndicator />
              
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="text-sm font-medium text-primary">AD</span>
              </div>
            </div>
          </div>
        </header>
        
        {/* Page content */}
        <main className="flex-1 p-4 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}