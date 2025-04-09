import { Link, useLocation } from "wouter";
import { Home, AlertCircle, Package, Users, Settings } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";

interface SidebarProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export default function Sidebar({ open, setOpen }: SidebarProps) {
  const [location] = useLocation();
  
  const navigation = [
    { name: "Dashboard", href: "/", icon: Home, current: location === "/" },
    { name: "Security Issues", href: "/security-issues", icon: AlertCircle, current: location === "/security-issues" },
    { name: "Bug Reports", href: "/bug-reports", icon: Package, current: location === "/bug-reports" },
    { name: "Contributors", href: "/contributors", icon: Users, current: location === "/contributors" },
    { name: "Settings", href: "/settings", icon: Settings, current: location === "/settings" },
  ];

  const DesktopSidebar = (
    <div className="hidden md:flex md:flex-shrink-0">
      <div className="flex flex-col w-64 bg-white border-r border-gray-200">
        <div className="flex items-center justify-center h-16 px-4 bg-blue-600">
          <h1 className="text-xl font-semibold text-white">SecureOrg</h1>
        </div>
        
        <div className="flex flex-col flex-grow overflow-y-auto">
          <nav className="flex-1 px-2 py-4 space-y-1">
            {navigation.map((item) => (
              <Link key={item.name} href={item.href}>
                <a
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                    item.current
                      ? "text-white bg-blue-500"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <item.icon
                    className={`w-5 h-5 mr-3 ${
                      item.current ? "text-white" : "text-gray-500"
                    }`}
                    aria-hidden="true"
                  />
                  {item.name}
                </a>
              </Link>
            ))}
          </nav>
          
          <div className="p-4 mt-6 border-t border-gray-200">
            <div className="flex items-center">
              <Avatar className="h-8 w-8">
                <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" alt="User avatar" />
                <AvatarFallback>AU</AvatarFallback>
              </Avatar>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-700">Admin User</p>
                <p className="text-xs font-medium text-gray-500">Security Admin</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const MobileSidebar = (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="left" className="p-0 w-64">
        <div className="flex flex-col h-full bg-white">
          <div className="flex items-center justify-center h-16 px-4 bg-blue-600">
            <h1 className="text-xl font-semibold text-white">SecureOrg</h1>
          </div>
          
          <div className="flex flex-col flex-grow overflow-y-auto">
            <nav className="flex-1 px-2 py-4 space-y-1">
              {navigation.map((item) => (
                <Link key={item.name} href={item.href}>
                  <a
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      item.current
                        ? "text-white bg-blue-500"
                        : "text-gray-600 hover:bg-gray-100"
                    }`}
                    onClick={() => setOpen(false)}
                  >
                    <item.icon
                      className={`w-5 h-5 mr-3 ${
                        item.current ? "text-white" : "text-gray-500"
                      }`}
                      aria-hidden="true"
                    />
                    {item.name}
                  </a>
                </Link>
              ))}
            </nav>
            
            <div className="p-4 mt-6 border-t border-gray-200">
              <div className="flex items-center">
                <Avatar className="h-8 w-8">
                  <AvatarImage src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" alt="User avatar" />
                  <AvatarFallback>AU</AvatarFallback>
                </Avatar>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-700">Admin User</p>
                  <p className="text-xs font-medium text-gray-500">Security Admin</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );

  return (
    <>
      {DesktopSidebar}
      {MobileSidebar}
    </>
  );
}
