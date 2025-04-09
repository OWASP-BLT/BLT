import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { SecurityIssue } from "@shared/schema";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusCircle, Search } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ExportImport } from "@/components/export-import";

type FilterState = {
  severity: string;
  status: string;
  assignee: string;
  search: string;
};

type EnhancedSecurityIssue = SecurityIssue & {
  assignee: {
    id: number;
    name: string;
    avatar: string | null;
  } | null;
  reporter: {
    id: number;
    name: string;
    avatar: string | null;
  } | null;
};

export default function SecurityIssues() {
  const [filters, setFilters] = useState<FilterState>({
    severity: "all",
    status: "all",
    assignee: "all",
    search: ""
  });

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;
  
  const queryClient = useQueryClient();
  
  const { data, isLoading, error } = useQuery<EnhancedSecurityIssue[]>({
    queryKey: ['/api/security-issues', filters]
  });
  
  const handleImportComplete = () => {
    // Refresh the security issues data after import
    queryClient.invalidateQueries({ queryKey: ['/api/security-issues'] });
  };

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  // Get the filtered security issues based on current filters
  const filteredIssues = data || [];
  
  // Calculate pagination
  const totalItems = filteredIssues.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
  const paginatedIssues = filteredIssues.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Status badge styles
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return <Badge className="bg-blue-100 text-blue-800">Open</Badge>;
      case 'in_progress':
        return <Badge className="bg-yellow-100 text-yellow-800">In Progress</Badge>;
      case 'resolved':
        return <Badge className="bg-green-100 text-green-800">Resolved</Badge>;
      case 'closed':
        return <Badge className="bg-gray-100 text-gray-800">Closed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  // Severity badge styles
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <Badge className="bg-red-500 text-white">Critical</Badge>;
      case 'high':
        return <Badge className="bg-orange-500 text-white">High</Badge>;
      case 'medium':
        return <Badge className="bg-yellow-500 text-white">Medium</Badge>;
      case 'low':
        return <Badge className="bg-green-500 text-white">Low</Badge>;
      default:
        return <Badge>{severity}</Badge>;
    }
  };

  return (
    <div className="container px-4 py-6 mx-auto max-w-7xl sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Security Issues</h1>
          <p className="mt-1 text-sm text-gray-500">Manage and track security vulnerabilities</p>
        </div>
        
        <Card className="overflow-hidden">
          <CardHeader className="px-4 py-5 sm:px-6">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Security Vulnerabilities</CardTitle>
                <CardDescription>Critical security issues requiring attention</CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                <ExportImport 
                  entityType="security-issues" 
                  onImportComplete={handleImportComplete}
                />
                <Button className="flex items-center gap-2">
                  <PlusCircle className="w-5 h-5" />
                  <span>New Issue</span>
                </Button>
              </div>
            </div>
          </CardHeader>
          
          {/* Filters */}
          <div className="px-4 py-3 bg-gray-50 border-t border-b border-gray-200 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {/* Severity Filter */}
                <div>
                  <Select
                    value={filters.severity}
                    onValueChange={(value) => handleFilterChange('severity', value)}
                  >
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="All Severities" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Severities</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Status Filter */}
                <div>
                  <Select
                    value={filters.status}
                    onValueChange={(value) => handleFilterChange('status', value)}
                  >
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="All Statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Assignee Filter */}
                <div>
                  <Select
                    value={filters.assignee}
                    onValueChange={(value) => handleFilterChange('assignee', value)}
                  >
                    <SelectTrigger className="w-[140px]">
                      <SelectValue placeholder="All Assignees" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Assignees</SelectItem>
                      <SelectItem value="unassigned">Unassigned</SelectItem>
                      <SelectItem value="me">Assigned to me</SelectItem>
                      <SelectItem value="team">My team</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Search */}
              <div className="relative flex-grow max-w-xs">
                <Input
                  type="text"
                  placeholder="Search issues..."
                  className="pl-10"
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                />
                <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                  <Search className="w-5 h-5 text-gray-400" />
                </div>
              </div>
            </div>
          </div>
          
          {/* Table */}
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-gray-50">
                <TableRow>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">ID</TableHead>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">Title</TableHead>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">Severity</TableHead>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">Status</TableHead>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">Assignee</TableHead>
                  <TableHead className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">Reported</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading && (
                  Array(4).fill(0).map((_, i) => (
                    <TableRow key={i} className="hover:bg-gray-50">
                      <TableCell className="px-6 py-4 whitespace-nowrap">
                        <Skeleton className="h-6 w-24" />
                      </TableCell>
                      <TableCell className="px-6 py-4">
                        <Skeleton className="h-6 w-full" />
                      </TableCell>
                      <TableCell className="px-6 py-4 whitespace-nowrap">
                        <Skeleton className="h-6 w-20" />
                      </TableCell>
                      <TableCell className="px-6 py-4 whitespace-nowrap">
                        <Skeleton className="h-6 w-20" />
                      </TableCell>
                      <TableCell className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <Skeleton className="h-8 w-8 rounded-full" />
                          <div className="ml-3">
                            <Skeleton className="h-4 w-24" />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="px-6 py-4 whitespace-nowrap">
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                    </TableRow>
                  ))
                )}
                
                {error && (
                  <TableRow>
                    <TableCell colSpan={6} className="px-6 py-4 text-center text-red-500">
                      Failed to load security issues
                    </TableCell>
                  </TableRow>
                )}
                
                {!isLoading && !error && paginatedIssues.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="px-6 py-4 text-center text-gray-500">
                      No security issues match your filters
                    </TableCell>
                  </TableRow>
                )}
                
                {!isLoading && !error && paginatedIssues.map((issue) => (
                  <TableRow key={issue.id} className="hover:bg-gray-50">
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">SEC-{issue.id}</div>
                    </TableCell>
                    <TableCell className="px-6 py-4">
                      <div className="text-sm text-gray-900">{issue.title}</div>
                    </TableCell>
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      {getSeverityBadge(issue.severity)}
                    </TableCell>
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(issue.status)}
                    </TableCell>
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      {issue.assignee ? (
                        <div className="flex items-center">
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={issue.assignee.avatar || undefined} alt={issue.assignee.name} />
                            <AvatarFallback>{issue.assignee.name.charAt(0)}</AvatarFallback>
                          </Avatar>
                          <div className="ml-3">
                            <div className="text-sm font-medium text-gray-900">{issue.assignee.name}</div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-500">Unassigned</span>
                      )}
                    </TableCell>
                    <TableCell className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">
                        {formatDistanceToNow(new Date(issue.createdAt), { addSuffix: true })}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          
          {/* Pagination */}
          {!isLoading && !error && totalItems > 0 && (
            <CardFooter className="flex items-center justify-between px-4 py-3 bg-white border-t border-gray-200 sm:px-6">
              <div className="flex justify-between flex-1 sm:hidden">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing <span className="font-medium">{Math.min(totalItems, (currentPage - 1) * itemsPerPage + 1)}</span>{' '}
                    to <span className="font-medium">{Math.min(totalItems, currentPage * itemsPerPage)}</span>{' '}
                    of <span className="font-medium">{totalItems}</span> results
                  </p>
                </div>
                <div className="flex space-x-1">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    <span className="sr-only">Previous</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path>
                    </svg>
                  </Button>
                  
                  {Array.from({ length: Math.min(3, totalPages) }).map((_, idx) => {
                    let pageNumber: number;
                    if (totalPages <= 3) {
                      pageNumber = idx + 1;
                    } else if (currentPage <= 2) {
                      pageNumber = idx + 1;
                    } else if (currentPage >= totalPages - 1) {
                      pageNumber = totalPages - 2 + idx;
                    } else {
                      pageNumber = currentPage - 1 + idx;
                    }
                    
                    return (
                      <Button
                        key={idx}
                        variant={currentPage === pageNumber ? "default" : "outline"}
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => setCurrentPage(pageNumber)}
                      >
                        {pageNumber}
                      </Button>
                    );
                  })}
                  
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <span className="sr-only">Next</span>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                  </Button>
                </div>
              </div>
            </CardFooter>
          )}
        </Card>
      </div>
  );
}