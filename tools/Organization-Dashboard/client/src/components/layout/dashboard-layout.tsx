import { useState } from "react";
import Sidebar from "./sidebar";
import TopBar from "./topbar";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar component for desktop */}
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />

      {/* Main content container */}
      <div className="flex flex-col flex-1 w-0 overflow-hidden">
        <TopBar setOpen={setSidebarOpen} />
        {children}
      </div>
    </div>
  );
}
