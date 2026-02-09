'use client';

import { Decision } from '@/types';
import { formatDistanceToNow } from 'date-fns';
import {
  FileText,
  User,
  Clock,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Settings,
  AlertTriangle
} from 'lucide-react';
import { clsx } from 'clsx';

interface DecisionCardProps {
  decision: Decision;
  userRole?: string;
  userComponents?: string[];
  density?: 'compact' | 'comfortable' | 'spacious';
  showDetails?: boolean;
  onClick?: () => void;
  gapPriority?: number;
}

export function DecisionCard({
  decision,
  userRole,
  userComponents = [],
  density = 'comfortable',
  showDetails = false,
  onClick,
  gapPriority
}: DecisionCardProps) {

  const isHighPriority = decision.affected_components.some(
    component => userComponents.includes(component)
  );

  const hasGaps = decision.gaps_detected && decision.gaps_detected.length > 0;

  const getBadgeNumber = (id: number) => {
    const badges = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];
    return badges[id % 10] || `${id}`;
  };

  const cardStyle = clsx(
    'transition-all duration-200 rounded-lg border',
    {
      // EverCurrent style background
      'bg-[#F5F1E8]': !isHighPriority && !hasGaps,
      'bg-blue-50 border-blue-200': isHighPriority,
      'bg-red-50 border-red-300 border-2': hasGaps,

      // Density variations
      'p-3': density === 'compact',
      'p-4': density === 'comfortable',
      'p-6': density === 'spacious',

      'mb-2': density === 'compact',
      'mb-4': density !== 'compact',

      // Interactive
      'cursor-pointer hover:shadow-lg': onClick,
    }
  );

  return (
    <div className={cardStyle} onClick={onClick}>
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        {/* EverCurrent Style Badge */}
        <div className="flex-shrink-0 w-8 h-8 bg-gray-800 text-white rounded-full flex items-center justify-center text-sm font-medium">
          {getBadgeNumber(decision.decision_id)}
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900">
              {decision.referenced_reqs.length > 0 ? decision.referenced_reqs[0] : `REQ-${decision.decision_id.toString().padStart(3, '0')}`}
            </h3>
            <span className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded-full capitalize">
              {decision.decision_type.replace('_', ' ')}
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>{decision.author_name}</span>
            <span>•</span>
            <span>{decision.author_role}</span>
            <span>•</span>
            <span>{formatDistanceToNow(new Date(decision.timestamp), { addSuffix: true })}</span>
          </div>
        </div>

        {hasGaps && (
          <div className="flex-shrink-0 flex items-center gap-2">
            {gapPriority && (
              <span className={clsx(
                'text-xs font-bold px-2 py-1 rounded-full',
                gapPriority === 1 ? 'bg-red-600 text-white' :
                gapPriority <= 3 ? 'bg-amber-500 text-white' :
                'bg-gray-500 text-white'
              )}>
                P{gapPriority}
              </span>
            )}
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
        )}
      </div>

      {/* Before/After Change - EverCurrent Style */}
      {decision.before_after && (
        <div className="mb-3 p-3 bg-amber-50 rounded-md border-l-4 border-amber-400">
          <div className="text-xs font-medium text-amber-800 uppercase tracking-wide mb-2">
            Requirement Change
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div>
              <span className="text-gray-600">Before:</span>
              <span className="ml-1 font-mono bg-red-100 text-red-800 px-2 py-1 rounded">
                {decision.before_after.before}
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-400" />
            <div>
              <span className="text-gray-600">After:</span>
              <span className="ml-1 font-mono bg-green-100 text-green-800 px-2 py-1 rounded">
                {decision.before_after.after}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Decision Text */}
      <div className="text-gray-700 mb-3 leading-relaxed">
        {density === 'compact' ? (
          <p className="text-sm">{decision.decision_text.slice(0, 100)}...</p>
        ) : showDetails ? (
          <p>{decision.decision_text}</p>
        ) : (
          <p>{decision.decision_text.slice(0, 150)}{decision.decision_text.length > 150 ? '...' : ''}</p>
        )}
      </div>

      {/* Components */}
      {decision.affected_components.length > 0 && (
        <div className="mb-3">
          <div className="flex flex-wrap gap-1">
            {decision.affected_components.map((component) => {
              const isOwned = userComponents.includes(component);
              return (
                <span
                  key={component}
                  className={clsx(
                    'text-xs px-2 py-1 rounded-full',
                    isOwned
                      ? 'bg-blue-100 text-blue-800 font-medium'
                      : 'bg-gray-100 text-gray-700'
                  )}
                >
                  {component}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Gap Detection Alert */}
      {hasGaps && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-red-800 flex-1">
              <span className="font-medium">Stakeholder Gap:</span>
              <span className="ml-1">You should be included in this decision</span>
              {gapPriority && (
                <span className="ml-2 text-xs text-red-600 font-bold">
                  (Priority: #{gapPriority})
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Citations */}
      {decision.thread_id && density !== 'compact' && (
        <div className="mt-3 pt-2 border-t border-gray-200">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <FileText className="w-3 h-3" />
            <span>#{decision.thread_id}</span>
            {decision.similarity_score && (
              <>
                <span>•</span>
                <span>{Math.round(decision.similarity_score * 100)}% relevance</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}