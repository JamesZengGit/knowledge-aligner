'use client';

import { Gap } from '@/types';
import { AlertTriangle, AlertCircle, Info, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';

interface GapAlertProps {
  gap: Gap;
  onDismiss?: () => void;
  compact?: boolean;
}

export function GapAlert({ gap, onDismiss, compact = false }: GapAlertProps) {
  const severityConfig = {
    critical: {
      icon: AlertTriangle,
      bgColor: 'bg-danger-50',
      borderColor: 'border-danger-200',
      textColor: 'text-danger-800',
      iconColor: 'text-danger-600',
    },
    warning: {
      icon: AlertCircle,
      bgColor: 'bg-warning-50',
      borderColor: 'border-warning-200',
      textColor: 'text-warning-800',
      iconColor: 'text-warning-600',
    },
  };

  const typeLabels = {
    missing_stakeholder: 'Missing Stakeholder',
    conflict: 'Decision Conflict',
    broken_dependency: 'Broken Dependency',
  };

  const config = severityConfig[gap.severity];
  const Icon = config.icon;

  if (compact) {
    return (
      <div className={clsx(
        'flex items-center space-x-3 p-3 rounded-lg border',
        config.bgColor,
        config.borderColor
      )}>
        <Icon className={clsx('w-5 h-5 flex-shrink-0', config.iconColor)} />
        <div className="flex-1 min-w-0">
          <p className={clsx('text-sm font-medium', config.textColor)}>
            {typeLabels[gap.type]}
          </p>
          <p className={clsx('text-sm', config.textColor)}>
            {gap.description}
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={clsx('flex-shrink-0 p-1 rounded hover:bg-white/50', config.iconColor)}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={clsx(
      'p-6 rounded-lg border',
      config.bgColor,
      config.borderColor
    )}>
      <div className="flex items-start space-x-4">
        <Icon className={clsx('w-6 h-6 flex-shrink-0 mt-1', config.iconColor)} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <h3 className={clsx('font-semibold', config.textColor)}>
                {typeLabels[gap.type]}
              </h3>
              <span className={clsx(
                'px-2 py-1 text-xs font-medium rounded-full',
                gap.severity === 'critical'
                  ? 'bg-danger-100 text-danger-700'
                  : 'bg-warning-100 text-warning-700'
              )}>
                {gap.severity}
              </span>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className={clsx('p-1 rounded hover:bg-white/50', config.iconColor)}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <p className={clsx('mb-4 leading-relaxed', config.textColor)}>
            {gap.description}
          </p>

          {/* Decision Reference */}
          {gap.decision_id && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-1">
                Related Decision:
              </p>
              <span className="inline-flex items-center px-2 py-1 bg-white rounded text-sm font-medium text-gray-900">
                REQ-{gap.decision_id.toString().padStart(3, '0')}
              </span>
            </div>
          )}

          {/* Recommendation */}
          <div className="p-3 bg-white/70 rounded-lg">
            <div className="flex items-start space-x-2">
              <Info className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900 mb-1">
                  Recommendation:
                </p>
                <p className="text-sm text-gray-700">
                  {gap.recommendation}
                </p>
              </div>
            </div>
          </div>

          {/* Timestamp */}
          <div className="mt-3 text-xs text-gray-500">
            Detected {formatDistanceToNow(new Date(gap.timestamp), { addSuffix: true })}
          </div>
        </div>
      </div>
    </div>
  );
}