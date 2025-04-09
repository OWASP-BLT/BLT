import React, { useState, useEffect } from 'react';
import { useWebSocketContext } from '@/contexts/websocket-context';
import { 
  CheckCircle,
  AlertCircle,
  User,
  Clock,
  Bell
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { WebSocketMessage } from '@/hooks/use-websocket';

interface ActivityItem {
  id: number;
  user: {
    id: number;
    name: string;
    avatar: string | null;
  };
  activityType: string;
  description: string;
  timestamp: string;
  relatedBug?: {
    id: number;
    bugId: string;
    title: string;
  } | null;
  relatedIssue?: {
    id: number;
    title: string;
  } | null;
}

export function RealTimeActivityFeed() {
  const { lastMessage, connected } = useWebSocketContext();
  const [activityItems, setActivityItems] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Fetch initial activity data
  useEffect(() => {
    fetch('/api/activity?limit=10')
      .then(response => response.json())
      .then(data => {
        setActivityItems(data);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching activity data:', error);
        setIsLoading(false);
      });
  }, []);
  
  // Handle real-time updates
  useEffect(() => {
    if (lastMessage?.type === 'new_activity') {
      const newActivity = lastMessage.data;
      
      // Add to the beginning of the list
      setActivityItems(prev => [newActivity, ...prev.slice(0, 9)]);
    } else if (lastMessage?.type === 'recent_activities') {
      // Replace all with the latest activities
      setActivityItems(lastMessage.data);
    }
  }, [lastMessage]);
  
  if (isLoading) {
    return <div className="p-4 text-center">Loading activity feed...</div>;
  }
  
  return (
    <div className="bg-white dark:bg-gray-950 rounded-md shadow">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <h3 className="text-lg font-medium">Recent Activity</h3>
        <div className="flex items-center space-x-2">
          <Badge variant={connected ? "default" : "outline"} className="h-6">
            {connected ? 'Live Updates' : 'Offline'}
          </Badge>
        </div>
      </div>
      
      <div className="divide-y divide-gray-200 dark:divide-gray-800">
        {activityItems.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            No recent activity
          </div>
        ) : (
          activityItems.map((activity, index) => (
            <ActivityFeedItem key={`${activity.id}-${index}`} activity={activity} />
          ))
        )}
      </div>
    </div>
  );
}

interface ActivityFeedItemProps {
  activity: ActivityItem;
}

function ActivityFeedItem({ activity }: ActivityFeedItemProps) {
  // Format the timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  // Get icon based on activity type
  const getIcon = () => {
    switch (activity.activityType) {
      case 'created':
        return <Bell className="h-4 w-4 text-blue-500" />;
      case 'updated':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'closed':
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
      case 'assigned':
        return <User className="h-4 w-4 text-indigo-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };
  
  return (
    <div className="flex items-start gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-900">
      <div className="mt-0.5">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium">
            {activity.user.name}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
            <Clock className="h-3 w-3 mr-1" />
            {formatTime(activity.timestamp)}
          </span>
        </div>
        
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {activity.description}
        </p>
        
        {activity.relatedBug && (
          <Badge variant="outline" className="mt-1">
            Bug {activity.relatedBug.bugId}
          </Badge>
        )}
        
        {activity.relatedIssue && (
          <Badge variant="outline" className="mt-1 bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
            Security Issue
          </Badge>
        )}
      </div>
    </div>
  );
}