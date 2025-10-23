export default function LoadingSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center" role="status" aria-label="Loading content">
      <div 
        className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"
        aria-hidden="true"
      ></div>
      <span className="sr-only">Loading...</span>
    </div>
  );
}