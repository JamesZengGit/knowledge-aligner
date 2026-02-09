'use client';

import { useState } from 'react';
import { Search, Filter, X, Calendar } from 'lucide-react';
import { Decision, SearchFilters } from '@/types';
import { DecisionCard } from '../decisions/DecisionCard';
import { mockUsers, mockDecisions } from '@/lib/mock-data';

interface SearchInterfaceProps {
  onDecisionSelect?: (decision: Decision) => void;
}

export function SearchInterface({ onDecisionSelect }: SearchInterfaceProps) {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    time_range_days: 30
  });
  const [showFilters, setShowFilters] = useState(false);
  const [results, setResults] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(false);

  const performSearch = async () => {
    setLoading(true);

    // Mock search with filtering
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate API delay

    let filteredResults = mockDecisions;

    // Filter by query
    if (query.trim()) {
      filteredResults = filteredResults.filter(decision =>
        decision.decision_text.toLowerCase().includes(query.toLowerCase()) ||
        decision.affected_components.some(component =>
          component.toLowerCase().includes(query.toLowerCase())
        ) ||
        decision.referenced_reqs.some(req =>
          req.toLowerCase().includes(query.toLowerCase())
        )
      );
    }

    // Filter by user components
    if (filters.user_id) {
      const user = mockUsers.find(u => u.user_id === filters.user_id);
      if (user) {
        filteredResults = filteredResults.filter(decision =>
          decision.affected_components.some(component =>
            user.owned_components.includes(component)
          )
        );
      }
    }

    // Filter by components
    if (filters.components && filters.components.length > 0) {
      filteredResults = filteredResults.filter(decision =>
        decision.affected_components.some(component =>
          filters.components!.includes(component)
        )
      );
    }

    // Filter by decision types
    if (filters.decision_types && filters.decision_types.length > 0) {
      filteredResults = filteredResults.filter(decision =>
        filters.decision_types!.includes(decision.decision_type)
      );
    }

    // Filter by time range
    if (filters.time_range_days) {
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - filters.time_range_days);
      filteredResults = filteredResults.filter(decision =>
        new Date(decision.timestamp) >= cutoff
      );
    }

    setResults(filteredResults);
    setLoading(false);
  };

  const clearFilters = () => {
    setFilters({ time_range_days: 30 });
    setQuery('');
    setResults([]);
  };

  const allComponents = Array.from(new Set(
    mockDecisions.flatMap(d => d.affected_components)
  )).sort();

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Decision Search
        </h1>
        <p className="text-gray-600">
          Search through decision history with AI-powered semantic matching
        </p>
      </div>

      {/* Search Input */}
      <div className="flex space-x-4">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search decisions, components, or requirements..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                performSearch();
              }
            }}
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`btn px-6 py-3 ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </button>
        <button
          onClick={performSearch}
          disabled={loading}
          className="btn btn-primary px-6 py-3"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Search Filters</h3>
            <button
              onClick={clearFilters}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              <X className="w-4 h-4 inline mr-1" />
              Clear all
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* User Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by User
              </label>
              <select
                value={filters.user_id || ''}
                onChange={(e) => setFilters({
                  ...filters,
                  user_id: e.target.value || undefined
                })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All users</option>
                {mockUsers.map(user => (
                  <option key={user.user_id} value={user.user_id}>
                    {user.user_name} ({user.role})
                  </option>
                ))}
              </select>
            </div>

            {/* Decision Type Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Decision Type
              </label>
              <select
                value={filters.decision_types?.[0] || ''}
                onChange={(e) => setFilters({
                  ...filters,
                  decision_types: e.target.value ? [e.target.value] : undefined
                })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All types</option>
                <option value="requirement_change">Requirement Change</option>
                <option value="design_decision">Design Decision</option>
                <option value="approval">Approval</option>
              </select>
            </div>

            {/* Component Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Component
              </label>
              <select
                value={filters.components?.[0] || ''}
                onChange={(e) => setFilters({
                  ...filters,
                  components: e.target.value ? [e.target.value] : undefined
                })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All components</option>
                {allComponents.map(component => (
                  <option key={component} value={component}>
                    {component}
                  </option>
                ))}
              </select>
            </div>

            {/* Time Range Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range
              </label>
              <select
                value={filters.time_range_days || 30}
                onChange={(e) => setFilters({
                  ...filters,
                  time_range_days: parseInt(e.target.value)
                })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      <div>
        {results.length > 0 && (
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Found {results.length} decision{results.length !== 1 ? 's' : ''}
            </h3>
          </div>
        )}

        <div className="space-y-4">
          {results.map((decision) => (
            <DecisionCard
              key={decision.decision_id}
              decision={decision}
              onClick={() => onDecisionSelect?.(decision)}
            />
          ))}
        </div>

        {results.length === 0 && query && !loading && (
          <div className="text-center py-12">
            <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No results found
            </h3>
            <p className="text-gray-500">
              Try adjusting your search terms or filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
}