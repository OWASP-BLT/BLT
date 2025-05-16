import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDistanceToNow, parseISO } from "date-fns";
import { AlertCircle, Edit, CheckCircle2, Search } from "lucide-react";
import { Link } from "wouter";

type ActivityUser = {
  id: number;
  name: string;
  avatar: string | null;
};

type RelatedBug = {
  id: number;
  bugId: string;
  title: string;
};

type RelatedIssue = {
  id: number;
  title: string;
};

type ActivityItem = {
  id: number;
  userId: number;
  activityType: string;
  description: string;
  relatedBugId: number | null;
  relatedIssueId: number | null;
  timestamp: string;
  user: ActivityUser;
  relatedBug: RelatedBug | null;
  relatedIssue: RelatedIssue | null;
};

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activityFilter, setActivityFilter] = useState("all");
  
  const { data, isLoading, error } = useQuery<ActivityItem[]>({
    queryKey: ['/api/activity']
  });

  // Filter activities based on search and activity type
  const filteredActivities = data?.filter(activity => {
    // Apply search filter
    const searchMatches = 
      searchQuery === "" || 
      activity.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (activity.user?.name && activity.user.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (activity.relatedBug?.bugId && activity.relatedBug.bugId.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (activity.relatedBug?.title && activity.relatedBug.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (activity.relatedIssue?.title && activity.relatedIssue.title.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Apply activity type filter
    const typeMatches = 
      activityFilter === "all" || 
      activityFilter === activity.activityType;
    
    return searchMatches && typeMatches;
  });

  const getActivityIcon = (activityType: string) => {
    switch (activityType) {
      case 'resolved':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-green-100 rounded-full ring-8 ring-white">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          </div>
        );
      case 'updated':
      case 'assigned':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full ring-8 ring-white">
            <Edit className="w-5 h-5 text-blue-500" />
          </div>
        );
      case 'created':
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full ring-8 ring-white">
            <AlertCircle className="w-5 h-5 text-blue-500" />
          </div>
        );
      default:
        return (
          <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-full ring-8 ring-white">
            <AlertCircle className="w-5 h-5 text-gray-500" />
          </div>
        );
    }
  };

  return (
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Activity Logs</h1>
        <p className="text-muted-foreground mt-2">
          Track all activities and events across the organization
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <CardTitle>Activity Timeline</CardTitle>
              <CardDescription>Historical record of all actions</CardDescription>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative w-full sm:w-auto">
                <Input
                  type="text"
                  placeholder="Search activities..."
                  className="pl-10 w-full sm:w-64"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <Search className="w-5 h-5 text-gray-400" />
                </div>
              </div>
              <Tabs defaultValue="all" className="w-full sm:w-auto" onValueChange={setActivityFilter}>
                <TabsList>
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="created">Created</TabsTrigger>
                  <TabsTrigger value="updated">Updated</TabsTrigger>
                  <TabsTrigger value="resolved">Resolved</TabsTrigger>
                  <TabsTrigger value="assigned">Assigned</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 py-5 bg-gray-50 sm:p-6">
          <div className="flow-root">
            <ul role="list" className="-mb-8">
              {isLoading && (
                Array(10).fill(0).map((_, idx) => (
                  <li key={idx}>
                    <div className="relative pb-8">
                      {idx < 9 && <span className="absolute top-5 left-5 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>}
                      <div className="relative flex items-start space-x-3">
                        <div className="relative">
                          <Skeleton className="h-10 w-10 rounded-full" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div>
                            <div className="text-sm">
                              <Skeleton className="h-5 w-24" />
                            </div>
                            <p className="mt-0.5 text-sm text-gray-500">
                              <Skeleton className="h-4 w-48" />
                            </p>
                          </div>
                          <div className="mt-2 text-sm text-gray-700">
                            <Skeleton className="h-4 w-full" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))
              )}
              
              {error && (
                <li>
                  <div className="p-4 text-red-500 bg-red-50 rounded-md">
                    Failed to load activity logs
                  </div>
                </li>
              )}
              
              {!isLoading && !error && filteredActivities?.length === 0 && (
                <li>
                  <div className="p-4 text-gray-500 bg-gray-100 rounded-md text-center">
                    No activities match your search/filter criteria
                  </div>
                </li>
              )}
              
              {!isLoading && !error && filteredActivities?.map((activity, idx) => (
                <li key={activity.id}>
                  <div className="relative pb-8">
                    {idx < (filteredActivities.length - 1) && (
                      <span className="absolute top-5 left-5 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>
                    )}
                    <div className="relative flex items-start space-x-3">
                      {activity.user.id === 0 ? (
                        <div className="relative px-1">
                          {getActivityIcon(activity.activityType)}
                        </div>
                      ) : (
                        <div className="relative">
                          <Avatar className="h-10 w-10">
                            <AvatarImage src={activity.user.avatar || undefined} alt={activity.user.name} />
                            <AvatarFallback>{activity.user.name.charAt(0)}</AvatarFallback>
                          </Avatar>
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div>
                          <div className="text-sm">
                            <Link href={`/contributors/${activity.user.id}`}>
                              <a className="font-medium text-gray-900 hover:text-blue-600 cursor-pointer">
                                {activity.user.name}
                              </a>
                            </Link>
                          </div>
                          <p className="mt-0.5 text-sm text-gray-500">
                            {activity.activityType === 'created' && 'Created '}
                            {activity.activityType === 'updated' && 'Updated '}
                            {activity.activityType === 'resolved' && 'Resolved '}
                            {activity.activityType === 'assigned' && 'Assigned '}
                            
                            {activity.relatedBug && (
                              <Link href={`/bug-reports/${activity.relatedBug.id}`}>
                                <a className="font-medium text-gray-900 hover:text-blue-600 cursor-pointer">
                                  {activity.relatedBug.bugId}
                                </a>
                              </Link>
                            )}
                            
                            {activity.relatedIssue && (
                              <Link href={`/security-issues/${activity.relatedIssue.id}`}>
                                <a className="font-medium text-gray-900 hover:text-blue-600 cursor-pointer">
                                  Security Issue #{activity.relatedIssue.id}
                                </a>
                              </Link>
                            )}
                            
                            {!activity.relatedBug && !activity.relatedIssue && 
                              activity.description.split(/(BUG-\d+)/).map((part, i) => {
                                if (part.match(/BUG-\d+/)) {
                                  return (
                                    <Link key={i} href={`/bug-reports?search=${part}`}>
                                      <a className="font-medium text-gray-900 hover:text-blue-600 cursor-pointer">
                                        {part}
                                      </a>
                                    </Link>
                                  );
                                }
                                return part;
                              })
                            }
                          </p>
                        </div>
                        <div className="mt-2 text-sm text-gray-700">
                          <p>{activity.description}</p>
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          {formatDistanceToNow(parseISO(activity.timestamp), { addSuffix: true })}
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}