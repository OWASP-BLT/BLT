import { Card, CardContent } from "@/components/ui/card";

export default function InfoCards() {
  return (
    <div className="px-4 sm:px-0">
      <Card className="mb-6">
        <CardContent className="pt-6">
          <h2 className="text-lg font-medium text-neutral-900 mb-4">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-lg bg-primary-50 p-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-primary-500 text-white mb-4">
                <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-neutral-900 mb-2">100-Point Checklist</h3>
              <p className="text-sm text-neutral-600">We analyze your repository against 100 criteria across 10 categories based on OWASP standards and best practices.</p>
            </div>
            <div className="rounded-lg bg-cyan-50 p-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-cyan-600 text-white mb-4">
                <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-neutral-900 mb-2">Security Assessment</h3>
              <p className="text-sm text-neutral-600">We evaluate your project's security practices, including dependency checks, input validation, and secure coding principles.</p>
            </div>
            <div className="rounded-lg bg-neutral-100 p-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-md bg-neutral-700 text-white mb-4">
                <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-neutral-900 mb-2">Actionable Recommendations</h3>
              <p className="text-sm text-neutral-600">Get specific recommendations to improve your project's compliance, quality, and security practices.</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-6">
          <h2 className="text-lg font-medium text-neutral-900 mb-4">OWASP Compliance Categories</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border rounded-lg p-4">
                <h3 className="font-medium text-primary-700 mb-2">General Compliance & Governance (10 points)</h3>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>• Project goals and scope</li>
                  <li>• Open-source licensing</li>
                  <li>• Documentation standards</li>
                  <li>• Contribution guidelines</li>
                  <li>• Project governance</li>
                </ul>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium text-primary-700 mb-2">Documentation & Usability (10 points)</h3>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>• README quality</li>
                  <li>• Installation & usage guides</li>
                  <li>• API documentation</li>
                  <li>• Code comments</li>
                  <li>• Versioning strategy</li>
                </ul>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium text-primary-700 mb-2">Code Quality & Best Practices (10 points)</h3>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>• Coding standards</li>
                  <li>• Code modularity</li>
                  <li>• Secure coding principles</li>
                  <li>• Input validation</li>
                  <li>• Output encoding</li>
                </ul>
              </div>
              <div className="border rounded-lg p-4">
                <h3 className="font-medium text-primary-700 mb-2">Security & OWASP Compliance (15 points)</h3>
                <ul className="text-sm text-neutral-600 space-y-1">
                  <li>• Dependency vulnerabilities</li>
                  <li>• Authentication mechanisms</li>
                  <li>• Access control implementation</li>
                  <li>• OWASP Top 10 compliance</li>
                  <li>• Secure communications</li>
                </ul>
              </div>
            </div>
            <p className="text-sm text-neutral-500 italic">And 6 more categories covering CI/CD, Testing, Performance, Logging, Community, and Legal compliance.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
