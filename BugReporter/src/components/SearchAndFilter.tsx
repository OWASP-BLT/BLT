import { useState, useRef } from 'react';
import { Search, Filter, X } from 'lucide-react';

interface FilterOption {
  label: string;
  value: string;
}

interface SearchAndFilterProps {
  searchPlaceholder?: string;
  onSearchChange: (search: string) => void;
  onFilterChange: (filters: Record<string, string>) => void;
  filters?: {
    [key: string]: {
      label: string;
      options: FilterOption[];
    };
  };
  initialSearch?: string;
  initialFilters?: Record<string, string>;
}

export default function SearchAndFilter({
  searchPlaceholder = "Search...",
  onSearchChange,
  onFilterChange,
  filters = {},
  initialSearch = "",
  initialFilters = {}
}: SearchAndFilterProps) {
  const [search, setSearch] = useState(initialSearch);
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>(initialFilters);
  const [showFilters, setShowFilters] = useState(false);

  // debounce search to avoid frequent reloads/requests
  const debounceRef = useRef<number | null>(null);
  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current);
    }
    debounceRef.current = window.setTimeout(() => {
      onSearchChange(value);
    }, 300);
  };

  const handleFilterChange = (key: string, value: string) => {
    const newFilters = { ...activeFilters };
    if (value === '') {
      delete newFilters[key];
    } else {
      newFilters[key] = value;
    }
    setActiveFilters(newFilters);
    onFilterChange(newFilters);
  };

  const clearAllFilters = () => {
    setSearch('');
    setActiveFilters({});
    onSearchChange('');
    onFilterChange({});
  };

  const activeFilterCount = Object.keys(activeFilters).length + (search ? 1 : 0);

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="relative" onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); } }}>
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); } }}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      {/* Filter Toggle and Clear */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <Filter className="w-4 h-4" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="bg-primary-100 text-primary-800 px-2 py-1 rounded-full text-xs font-medium">
              {activeFilterCount}
            </span>
          )}
        </button>

        {activeFilterCount > 0 && (
          <button
            onClick={clearAllFilters}
            className="flex items-center space-x-1 px-3 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg"
          >
            <X className="w-4 h-4" />
            <span>Clear all</span>
          </button>
        )}
      </div>

      {/* Filter Options */}
      {showFilters && Object.keys(filters).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
          {Object.entries(filters).map(([key, filter]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {filter.label}
              </label>
              <select
                value={activeFilters[key] || ''}
                onChange={(e) => handleFilterChange(key, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              >
                <option value="">All {filter.label}</option>
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2">
          {search && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
              Search: "{search}"
              <button
                onClick={() => handleSearchChange('')}
                className="ml-2 hover:text-primary-900"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {Object.entries(activeFilters).map(([key, value]) => {
            const filter = filters[key];
            const option = filter?.options.find(opt => opt.value === value);
            return (
              <span
                key={key}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {filter?.label}: {option?.label || value}
                <button
                  onClick={() => handleFilterChange(key, '')}
                  className="ml-2 hover:text-blue-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
} 