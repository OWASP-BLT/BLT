import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { CheckCircle2, Edit, AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
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

export default function ActivityFeed() {
  const { data, isLoading, error } = useQuery<ActivityItem[]>({
    queryKey: ['/api/activity?limit=4']
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
    <Card className="overflow-hidden">
      <CardHeader className="px-4 py-5 sm:px-6">
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Contributor actions and system events</CardDescription>
      </CardHeader>
      <CardContent className="px-4 py-5 bg-gray-50 sm:p-6">
        <div className="flow-root">
          <ul role="list" className="-mb-8">
            {isLoading && (
              Array(4).fill(0).map((_, idx) => (
                <li key={idx}>
                  <div className="relative pb-8">
                    {idx < 3 && <span className="absolute top-5 left-5 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>}
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
              <li className="text-center py-4 text-red-500">
                Failed to load activity data
              </li>
            )}

            {!isLoading && !error && data?.length === 0 && (
              <li className="text-center py-4 text-gray-500">
                No recent activity to display
              </li>
            )}

            {!isLoading && !error && data?.map((activity, idx) => (
              <li key={activity.id}>
                <div className="relative pb-8">
                  {idx < data.length - 1 && (
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
                        {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-6">
          <Link href="/activity">
            <Button variant="outline" className="w-full">
              View all activity
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
