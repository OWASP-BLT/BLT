import { ReactNode } from "react";
import { Link } from "wouter";
import { ExternalLink, Shield } from "lucide-react";

type MainLayoutProps = {
  children: ReactNode;
};

export default function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/">
              <div className="flex items-center cursor-pointer">
                <Shield className="h-8 w-8 text-primary-600" />
                <span className="ml-2 text-xl font-semibold text-neutral-900">OWASP Compliance Checker</span>
              </div>
            </Link>
            <div>
              <a 
                href="https://owasp.org" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700 font-medium flex items-center"
              >
                OWASP Foundation
                <ExternalLink className="ml-1 h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-grow">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="flex items-center space-x-4">
              <a 
                href="https://owasp.org" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-neutral-500 hover:text-neutral-700"
              >
                <span className="sr-only">OWASP</span>
                <Shield className="h-6 w-6" />
              </a>
              <a href="#" className="text-neutral-500 hover:text-neutral-700">About</a>
              <a href="#" className="text-neutral-500 hover:text-neutral-700">Contact</a>
            </div>
            <div className="text-neutral-500 text-sm">
              &copy; {new Date().getFullYear()} OWASP Foundation. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
