'use client';

import { useState, useEffect } from 'react';
import { Search, Filter, Calendar } from 'lucide-react';
import { Decision, UserPreferences } from '@/types';
import { DecisionCard } from './DecisionCard';
import api from '@/lib/api';
import { mockDecisions } from '@/lib/mock-data';

interface DecisionsDatabaseProps {
  userPreferences: UserPreferences;
  gaps?: Gap[];
}

export function DecisionsDatabase({ userPreferences, gaps = [] }: DecisionsDatabaseProps) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [filteredDecisions, setFilteredDecisions] = useState<Decision[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedComponent, setSelectedComponent] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDecisions();
  }, []);

  useEffect(() => {
    filterDecisions();
  }, [decisions, searchTerm, selectedComponent, selectedType]);

  const loadDecisions = async () => {
    try {
      const data = await api.getDecisions();
      setDecisions(data);
    } catch (error) {
      console.error('Failed to load decisions from API, using mock data:', error);
      // Fallback to mock data
      setDecisions(mockDecisions);
    } finally {
      setLoading(false);
    }
  };

  const filterDecisions = () => {
    let filtered = decisions;

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(d =>
        d.decision_text.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.referenced_reqs.some(req => req.toLowerCase().includes(searchTerm.toLowerCase())) ||
        d.affected_components.some(comp => comp.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Component filter
    if (selectedComponent) {
      filtered = filtered.filter(d =>
        d.affected_components.includes(selectedComponent)
      );
    }

    // Type filter
    if (selectedType) {
      filtered = filtered.filter(d => d.decision_type === selectedType);
    }

    setFilteredDecisions(filtered);
  };

  const allComponents = Array.from(
    new Set(decisions.flatMap(d => d.affected_components))
  ).sort();

  const decisionTypes = [
    'requirement_change',
    'design_decision',
    'approval'
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Decisions Database</h1>
          <p className="text-gray-600">
            {filteredDecisions.length} of {decisions.length} decisions
          </p>
        </div>

        {/* Density Control */}
        <select
          className="text-sm border rounded px-3 py-2"
          value={userPreferences.density}
          onChange={(e) => {
            // This would update user preferences in parent component
            console.log('Density changed to:', e.target.value);
          }}
        >
          <option value="compact">Compact</option>
          <option value="comfortable">Comfortable</option>
          <option value="spacious">Spacious</option>
        </select>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-6 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search decisions, requirements, or components..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={selectedComponent}
              onChange={(e) => setSelectedComponent(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1 text-sm"
            >
              <option value="">All Components</option>
              {allComponents.map(component => (
                <option key={component} value={component}>
                  {component}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1 text-sm"
            >
              <option value="">All Types</option>
              {decisionTypes.map(type => (
                <option key={type} value={type}>
                  {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {(searchTerm || selectedComponent || selectedType) && (
            <button
              onClick={() => {
                setSearchTerm('');
                setSelectedComponent('');
                setSelectedType('');
              }}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Quick Filters */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm font-medium text-gray-700">Quick filters:</span>
          <button
            onClick={() => setSelectedComponent('Motor-XYZ')}
            className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 rounded-full px-3 py-1"
          >
            Motor-XYZ
          </button>
          <button
            onClick={() => setSearchTerm('REQ-245')}
            className="text-xs bg-green-100 hover:bg-green-200 text-green-800 rounded-full px-3 py-1"
          >
            REQ-245
          </button>
          <button
            onClick={() => setSelectedType('requirement_change')}
            className="text-xs bg-amber-100 hover:bg-amber-200 text-amber-800 rounded-full px-3 py-1"
          >
            Requirements
          </button>
        </div>
      </div>

      {/* Decision Cards */}
      <div className="space-y-4">
        {filteredDecisions.length > 0 ? (
          filteredDecisions.map((decision) => {
            // Find gap priority for this decision
            const relatedGap = gaps.find(gap => gap.decision_id === decision.decision_id);
            const gapPriority = relatedGap?.priority;

            return (
              <DecisionCard
                key={decision.decision_id}
                decision={decision}
                userRole={userPreferences.role}
                userComponents={userPreferences.priorityComponents}
                density={userPreferences.density}
                showDetails={userPreferences.density === 'spacious'}
                gapPriority={gapPriority}
              />
            );
          })
        ) : (
          <div className="bg-gray-50 rounded-lg p-12 text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No decisions found
            </h3>
            <p className="text-gray-500 mb-4">
              Try adjusting your search criteria or filters
            </p>
            <button
              onClick={() => {
                setSearchTerm('');
                setSelectedComponent('');
                setSelectedType('');
              }}
              className="text-blue-600 hover:text-blue-800"
            >
              Clear all filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}