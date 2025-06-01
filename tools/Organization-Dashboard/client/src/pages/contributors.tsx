import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, BarChart4, GitBranch, GitCommit } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

interface Contributor {
  id: number;
  name: string;
  avatar: string | null;
  role: string;
  email: string;
  contributions: number;
  lastActive: string;
  status: 'active' | 'inactive' | 'vacation';
}

export default function Contributors() {
  const [searchQuery, setSearchQuery] = useState("");
  
  // Mock data until we have a proper API endpoint
  const { data: contributors, isLoading, error } = useQuery<Contributor[]>({
    queryKey: ['/api/users', { search: searchQuery }],
    select: (data) => {
      // Convert users to contributors (this would normally be done server-side)
      return data.map(user => ({
        id: user.id,
        name: user.name,
        avatar: user.avatar,
        role: 'Developer', // This would normally come from a role field
        email: `${user.name.toLowerCase().replace(/\s/g, '.')}@example.com`,
        contributions: Math.floor(Math.random() * 100),
        lastActive: new Date().toISOString(),
        status: 'active' as 'active' | 'inactive' | 'vacation'
      }));
    }
  });

  const filteredContributors = contributors || [];

  return (
      <div className="container px-4 py-6 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Contributors</h1>
          <p className="mt-1 text-sm text-gray-500">Manage team members and their activity</p>
        </div>
        
        {/* Search and Actions Bar */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
          <div className="relative flex-grow md:max-w-md">
            <Input
              type="text"
              placeholder="Search contributors..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <Search className="w-5 h-5 text-gray-400" />
            </div>
          </div>
          
          <div className="flex flex-col md:flex-row gap-2">
            <Button variant="outline" className="flex items-center gap-2">
              <BarChart4 className="w-4 h-4" />
              <span className="hidden sm:inline">Contribution Report</span>
              <span className="sm:hidden">Report</span>
            </Button>
            <Button className="flex items-center gap-2">
              <GitBranch className="w-4 h-4" />
              <span>Invite Member</span>
            </Button>
          </div>
        </div>
        
        {/* Contributors Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading && Array(6).fill(0).map((_, i) => (
            <Card key={i} className="transition-shadow hover:shadow-md">
              <CardContent className="p-6">
                <div className="flex items-start">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="ml-4 flex-1">
                    <Skeleton className="h-5 w-32 mb-1" />
                    <Skeleton className="h-4 w-24 mb-2" />
                    <Skeleton className="h-4 w-full mb-4" />
                    <div className="flex justify-between items-center">
                      <Skeleton className="h-6 w-16" />
                      <Skeleton className="h-8 w-8 rounded-full" />
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          
          {error && (
            <div className="col-span-full text-center py-8">
              <div className="text-red-500 mb-2">Failed to load contributors</div>
              <Button variant="outline" size="sm">Retry</Button>
            </div>
          )}
          
          {!isLoading && !error && filteredContributors.length === 0 && (
            <div className="col-span-full text-center py-8">
              <div className="text-gray-500 mb-2">No contributors found</div>
            </div>
          )}
          
          {!isLoading && !error && filteredContributors.map((contributor) => (
            <Card key={contributor.id} className="transition-shadow hover:shadow-md">
              <CardContent className="p-6">
                <div className="flex items-start">
                  <Avatar className="h-12 w-12">
                    <AvatarImage src={contributor.avatar || undefined} alt={contributor.name} />
                    <AvatarFallback>{contributor.name.charAt(0)}</AvatarFallback>
                  </Avatar>
                  
                  <div className="ml-4 flex-1">
                    <h3 className="text-lg font-medium text-gray-900">{contributor.name}</h3>
                    <p className="text-sm text-gray-500">{contributor.role}</p>
                    <p className="text-sm text-gray-500 mt-1">{contributor.email}</p>
                    
                    <div className="flex items-center justify-between mt-4">
                      <Badge
                        className={`
                          ${contributor.status === 'active' ? 'bg-green-100 text-green-800' : ''}
                          ${contributor.status === 'inactive' ? 'bg-gray-100 text-gray-800' : ''}
                          ${contributor.status === 'vacation' ? 'bg-yellow-100 text-yellow-800' : ''}
                        `}
                      >
                        {contributor.status === 'active' && 'Active'}
                        {contributor.status === 'inactive' && 'Inactive'}
                        {contributor.status === 'vacation' && 'Vacation'}
                      </Badge>
                      
                      <div className="flex items-center gap-1 text-gray-500">
                        <GitCommit className="w-4 h-4" />
                        <span className="text-sm font-medium">{contributor.contributions}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
  );
}