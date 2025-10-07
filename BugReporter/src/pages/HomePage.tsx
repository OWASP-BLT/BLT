import { Link } from 'react-router-dom';
import { ArrowRight, Github, BookOpen, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function HomePage() {
  const { user } = useAuth();

  if (user) {
    // If already authenticated, send to the main app
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center space-y-6">
          <div className="mx-auto w-16 h-16 bg-primary-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-xl">BLT</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold">You're signed in</h1>
            <p className="text-gray-600 mt-1">Proceed to your dashboard.</p>
          </div>
          <Link to="/app/bugs" className="inline-flex items-center btn-primary">
            Go to Bugs
            <ArrowRight className="w-4 h-4 ml-2" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header / Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-50 via-white to-white" />
        <div className="pointer-events-none absolute -top-24 -right-24 w-72 h-72 rounded-full bg-primary-100 blur-3xl opacity-40" />
        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 sm:py-28">
          <div className="grid lg:grid-cols-2 gap-10 items-center">
            <div>
              <div className="flex items-center space-x-2 text-xs font-medium text-primary-700 bg-primary-50 border border-primary-100 rounded-full px-3 py-1 w-max">
                <Shield className="w-3.5 h-3.5" />
                <span>OWASP Bug Logging Tool</span>
              </div>
              <h1 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-gray-900">
                Streamlined bug reporting for your projects
              </h1>
              <p className="mt-4 text-base sm:text-lg text-gray-600 max-w-prose">
                Capture, track, and manage issues with a clean, modern interface. BLT helps teams report bugs quickly, organize by projects and repositories, and collaborate efficiently.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row sm:items-center gap-3">
                <Link to="/login" className="inline-flex items-center justify-center btn-primary">
                  Sign in / Create account
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
                <a
                  href="https://github.com/OWASP-BLT/BLT/pull/4600"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center btn-secondary"
                >
                  <Github className="w-4 h-4 mr-2" />
                  View on GitHub
                </a>
              </div>
            </div>

            <div className="lg:pl-8">
              <div className="relative bg-white border border-gray-200 rounded-2xl shadow-sm p-4 sm:p-6">
                <div className="grid grid-cols-2 gap-3 sm:gap-4">
                  <div className="card p-4 sm:p-5">
                    <p className="text-sm font-semibold text-gray-900">Log Bugs</p>
                    <p className="mt-1 text-sm text-gray-600">Quickly capture issues with titles, descriptions, and status.</p>
                  </div>
                  <div className="card p-4 sm:p-5">
                    <p className="text-sm font-semibold text-gray-900">Projects</p>
                    <p className="mt-1 text-sm text-gray-600">Organize bugs by projects for better tracking.</p>
                  </div>
                  <div className="card p-4 sm:p-5">
                    <p className="text-sm font-semibold text-gray-900">Repositories</p>
                    <p className="mt-1 text-sm text-gray-600">Associate issues with code repositories.</p>
                  </div>
                  <div className="card p-4 sm:p-5">
                    <p className="text-sm font-semibold text-gray-900">Roles</p>
                    <p className="mt-1 text-sm text-gray-600">Admin-only user management and access control.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Getting started</h2>
        <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="card p-5">
            <p className="text-sm font-semibold text-gray-900">1. Sign in or create an account</p>
            <p className="mt-1 text-sm text-gray-600">Use the demo credentials or register a new account.</p>
          </div>
          <div className="card p-5">
            <p className="text-sm font-semibold text-gray-900">2. Create a project</p>
            <p className="mt-1 text-sm text-gray-600">Add your project to group related bugs and repositories.</p>
          </div>
          <div className="card p-5">
            <p className="text-sm font-semibold text-gray-900">3. Start logging bugs</p>
            <p className="mt-1 text-sm text-gray-600">Provide clear titles and descriptions so your team can act.</p>
          </div>
        </div>

        <div className="mt-8">
          <a
            href="https://github.com/sidd190/Bug-Reporting-App"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center text-primary-700 hover:text-primary-800"
          >
            <BookOpen className="w-4 h-4 mr-2" />
            Read the documentation
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-sm text-gray-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <span>© {new Date().getFullYear()} OWASP BLT</span>
          <div className="flex items-center gap-4">
            <a href="https://github.com/OWASP-BLT/BLT/pull/4600" target="_blank" rel="noreferrer" className="hover:text-gray-700">GitHub</a>
            <a href="https://owasp.org/" target="_blank" rel="noreferrer" className="hover:text-gray-700">OWASP</a>
          </div>
        </div>
      </footer>
    </div>
  );
}


