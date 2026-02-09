'use client';

import { DigestEntry as DigestEntryType } from '@/types';
import { formatDistanceToNow } from 'date-fns';
import {
  ArrowRight,
  ExternalLink,
  Clock,
  Tag,
  AlertCircle
} from 'lucide-react';
import { clsx } from 'clsx';

interface DigestEntryProps {
  entry: DigestEntryType;
  expanded?: boolean;
  onToggle?: () => void;
}

export function DigestEntry({ entry, expanded = false, onToggle }: DigestEntryProps) {
  return (
    <div className="card p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="font-semibold text-gray-900">
              {entry.title}
            </h3>
            <span className="badge badge-primary">
              {entry.decision_id}
            </span>
          </div>

          {/* Before/After Change */}
          {entry.before_after && (
            <div className="flex items-center space-x-2 mb-3 p-3 bg-primary-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">
                {entry.before_after.before}
              </span>
              <ArrowRight className="w-4 h-4 text-primary-600" />
              <span className="text-sm font-medium text-primary-700">
                {entry.before_after.after}
              </span>
            </div>
          )}
        </div>

        <div className="text-right">
          <p className="text-sm text-gray-500">
            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-4">
        <p className="text-gray-700 leading-relaxed">
          {entry.summary}
        </p>
      </div>

      {/* Impact Summary */}
      <div className="mb-4 p-4 bg-warning-50 border-l-4 border-warning-400">
        <div className="flex items-start space-x-2">
          <AlertCircle className="w-5 h-5 text-warning-600 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium text-warning-800 mb-1">
              Impact on Your Components:
            </p>
            <p className="text-warning-700 text-sm">
              {entry.impact_summary}
            </p>
          </div>
        </div>
      </div>

      {/* Affected Components */}
      {entry.affected_components.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <Tag className="w-4 h-4 text-gray-500" />
            <p className="text-sm font-medium text-gray-600">
              Affected Components:
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {entry.affected_components.map((component) => (
              <span
                key={component}
                className="badge badge-secondary"
              >
                {component}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Citations */}
      {entry.citations.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-medium text-gray-600 mb-2">
            Sources:
          </p>
          <div className="space-y-1">
            {entry.citations.map((citation, index) => (
              <div
                key={index}
                className="flex items-center space-x-2 text-sm text-primary-600 hover:text-primary-700"
              >
                <ExternalLink className="w-3 h-3" />
                <span className="font-mono text-xs">
                  {citation}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expand/Collapse Button */}
      {onToggle && (
        <div className="pt-4 border-t border-gray-100">
          <button
            onClick={onToggle}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            {expanded ? 'Show less' : 'Show more details'}
          </button>
        </div>
      )}
    </div>
  );
}