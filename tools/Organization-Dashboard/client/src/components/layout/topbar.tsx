import { BellIcon, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useIsMobile } from "@/hooks/use-mobile";

interface TopBarProps {
  setOpen: (open: boolean) => void;
}

export default function TopBar({ setOpen }: TopBarProps) {
  const isMobile = useIsMobile();

  return (
    <div className="relative z-10 flex flex-shrink-0 h-16 bg-white shadow">
      <Button 
        variant="ghost" 
        size="icon"
        className="px-4 text-gray-500 border-r border-gray-200 md:hidden"
        onClick={() => setOpen(true)}
      >
        <Menu className="w-6 h-6" />
      </Button>
      
      <div className="flex justify-between flex-1 px-4 md:px-0">
        <div className="flex flex-1">
          <div className="flex items-center w-full md:ml-0">
            <div className="flex items-center w-full">
              <h1 className="text-xl font-semibold text-gray-800 md:hidden">SecureOrg</h1>
              <h2 className="hidden text-xl font-semibold text-gray-800 md:block">Organization Dashboard</h2>
            </div>
          </div>
        </div>
        <div className="flex items-center ml-4 md:ml-6">
          <Button variant="ghost" size="icon" className="p-1 text-gray-400 bg-white rounded-full hover:text-gray-500">
            <BellIcon className="w-6 h-6" />
          </Button>
        </div>
      </div>
    </div>
  );
}
