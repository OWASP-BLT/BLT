import React, { useState, useEffect } from 'react';
import { useWebSocketContext } from '@/contexts/websocket-context';
import { 
  Bell,
  CheckCircle,
  AlertCircle,
  Info,
  X
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { WebSocketMessage } from '@/hooks/use-websocket';

export function NotificationsIndicator() {
  const { lastMessage, connected } = useWebSocketContext();
  const { toast } = useToast();
  const [notificationCount, setNotificationCount] = useState(0);
  const [lastNotifications, setLastNotifications] = useState<WebSocketMessage[]>([]);

  // Process new notifications from WebSocket messages
  useEffect(() => {
    if (lastMessage && 
        (lastMessage.type === 'new_bug_report' || 
         lastMessage.type === 'new_security_issue' || 
         lastMessage.type === 'new_activity')) {
      
      // Update notification count
      setNotificationCount(prev => prev + 1);
      
      // Add to recent notifications list
      setLastNotifications(prev => [lastMessage, ...prev].slice(0, 5));
      
      // Show toast notification
      let title = 'New Notification';
      let description = 'Something happened in the system.';
      let variant: 'default' | 'destructive' = 'default';
      
      switch (lastMessage.type) {
        case 'new_bug_report':
          title = 'New Bug Report';
          description = `Bug ${lastMessage.data.bugId}: ${lastMessage.data.title}`;
          break;
        case 'new_security_issue':
          title = 'New Security Issue';
          description = `Issue: ${lastMessage.data.title}`;
          variant = 'destructive';
          break;
        case 'new_activity':
          title = 'New Activity';
          description = lastMessage.data.description;
          break;
      }
      
      toast({
        title,
        description,
        variant
      });
    }
  }, [lastMessage, toast]);
  
  // Reset notification count when clicked
  const handleClick = () => {
    setNotificationCount(0);
  };
  
  return (
    <div className="relative">
      <button 
        onClick={handleClick}
        className="relative p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        aria-label="Notifications"
      >
        <Bell size={20} className={connected ? 'text-primary' : 'text-gray-400'} />
        {notificationCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center w-4 h-4 text-xs font-bold text-white bg-red-500 rounded-full">
            {notificationCount > 9 ? '9+' : notificationCount}
          </span>
        )}
      </button>
      
      {/* Connection status indicator */}
      <div className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-gray-300">
        <div className={`absolute inset-0 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-400'} ${connected ? 'animate-pulse' : ''}`}></div>
      </div>
    </div>
  );
}

interface NotificationItemProps {
  message: WebSocketMessage;
  onClose: () => void;
}

function NotificationItem({ message, onClose }: NotificationItemProps) {
  const getIcon = () => {
    switch (message.type) {
      case 'new_bug_report':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'new_security_issue':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'new_activity':
        if (message.data.activityType === 'resolved') {
          return <CheckCircle className="h-4 w-4 text-green-500" />;
        }
        return <Info className="h-4 w-4 text-blue-500" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };
  
  const getTitle = () => {
    switch (message.type) {
      case 'new_bug_report':
        return `Bug ${message.data.bugId}`;
      case 'new_security_issue':
        return 'Security Issue';
      case 'new_activity':
        return message.data.user?.name || 'System';
      default:
        return 'Notification';
    }
  };
  
  const getDescription = () => {
    switch (message.type) {
      case 'new_bug_report':
        return message.data.title;
      case 'new_security_issue':
        return message.data.title;
      case 'new_activity':
        return message.data.description;
      default:
        return 'New notification received';
    }
  };
  
  return (
    <div className="flex items-start gap-2 p-2 border-b border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900">
      <div className="mt-1">{getIcon()}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{getTitle()}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{getDescription()}</p>
      </div>
      <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function NotificationsPanel() {
  const { lastMessage } = useWebSocketContext();
  const [notifications, setNotifications] = useState<WebSocketMessage[]>([]);
  
  useEffect(() => {
    if (lastMessage && 
        (lastMessage.type === 'new_bug_report' || 
         lastMessage.type === 'new_security_issue' || 
         lastMessage.type === 'new_activity')) {
      setNotifications(prev => [lastMessage, ...prev].slice(0, 10));
    }
  }, [lastMessage]);
  
  const removeNotification = (index: number) => {
    setNotifications(prev => prev.filter((_, i) => i !== index));
  };
  
  return (
    <div className="w-80 max-h-96 overflow-auto shadow-lg rounded-md border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-800">
        <h3 className="text-sm font-medium">Notifications</h3>
        <button 
          onClick={() => setNotifications([])}
          className="text-xs text-primary hover:underline"
        >
          Clear all
        </button>
      </div>
      
      <div className="divide-y divide-gray-200 dark:divide-gray-800">
        {notifications.length === 0 ? (
          <p className="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
            No new notifications
          </p>
        ) : (
          notifications.map((notification, index) => (
            <NotificationItem
              key={index}
              message={notification}
              onClose={() => removeNotification(index)}
            />
          ))
        )}
      </div>
    </div>
  );
}