const Organizations = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">Organizations</h1>
        <p className="text-body">Browse organizations participating in BLT</p>
      </div>

      <div className="bg-white rounded-lg shadow-card p-12 text-center">
        <div className="text-6xl mb-4">🏢</div>
        <h2 className="text-2xl font-bold mb-4">Organizations Coming Soon</h2>
        <p className="text-body mb-6">
          This page will list all organizations using BLT for bug bounty programs.
        </p>
      </div>
    </div>
  );
};

export default Organizations;
