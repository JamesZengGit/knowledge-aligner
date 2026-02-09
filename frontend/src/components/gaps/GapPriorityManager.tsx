'use client';

import { useState } from 'react';
import { Gap } from '@/types';
import { GripVertical, AlertTriangle, Clock, Flag } from 'lucide-react';
import { clsx } from 'clsx';

interface GapWithPriority extends Gap {
  priority: number;
}

interface GapPriorityManagerProps {
  gaps: Gap[];
  onPriorityChange: (gapId: number, priority: number) => void;
  onReorder?: (reorderedGaps: Gap[]) => void;
}

export function GapPriorityManager({ gaps, onPriorityChange, onReorder }: GapPriorityManagerProps) {
  // Use gaps directly from props - no internal state needed
  const gapPriorities = gaps.map((gap, index) => ({
    ...gap,
    priority: gap.priority || (index + 1),
  })).sort((a, b) => (a.priority || 0) - (b.priority || 0));

  const [draggedItem, setDraggedItem] = useState<number | null>(null);

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedItem(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();

    if (draggedItem === null || draggedItem === index) return;

    const newGaps = [...gapPriorities];
    const draggedGap = newGaps[draggedItem];

    // Remove dragged item and insert at new position
    newGaps.splice(draggedItem, 1);
    newGaps.splice(index, 0, draggedGap);

    // Update priorities and notify parent immediately
    const updatedGaps = newGaps.map((gap, i) => ({
      ...gap,
      priority: i + 1,
    }));

    if (onReorder) {
      onReorder(updatedGaps);
    }
    setDraggedItem(index);
  };

  const handleDragEnd = () => {
    setDraggedItem(null);
  };

  const getPriorityColor = (priority: number, severity: string) => {
    if (severity === 'critical') {
      if (priority === 1) return 'border-red-500 bg-red-50';
      if (priority <= 3) return 'border-red-300 bg-red-25';
      return 'border-red-200 bg-red-10';
    }

    if (priority === 1) return 'border-amber-500 bg-amber-50';
    if (priority <= 3) return 'border-amber-300 bg-amber-25';
    return 'border-amber-200 bg-amber-10';
  };

  const getPriorityIcon = (priority: number) => {
    if (priority === 1) return <Flag className="w-4 h-4 text-red-600" />;
    if (priority <= 3) return <AlertTriangle className="w-4 h-4 text-amber-600" />;
    return <Clock className="w-4 h-4 text-gray-500" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Gap Priority Management
          </h2>
          <p className="text-sm text-gray-600">
            Drag to reorder gaps by priority. Higher priority gaps will be surfaced first in chat.
          </p>
        </div>
        <div className="text-sm text-gray-500">
          {gapPriorities.length} gaps to prioritize
        </div>
      </div>

      {gapPriorities.length === 0 ? (
        <div className="text-center py-12 bg-green-50 rounded-lg">
          <div className="text-green-600 text-2xl mb-2">✅</div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">
            No Gaps Detected
          </h3>
          <p className="text-gray-500">
            All decisions have proper stakeholder involvement
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {gapPriorities.map((gap, index) => (
            <div
              key={`${gap.decision_id}-${index}`}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              className={clsx(
                'flex items-start gap-4 p-4 rounded-lg border-2 transition-all cursor-move',
                getPriorityColor(index + 1, gap.severity),
                draggedItem === index && 'opacity-50 scale-95',
                'hover:shadow-md'
              )}
            >
              {/* Drag Handle */}
              <div className="flex items-center gap-2">
                <GripVertical className="w-5 h-5 text-gray-400" />
                <div className="flex items-center gap-1 min-w-[60px]">
                  {getPriorityIcon(index + 1)}
                  <span className="text-sm font-medium text-gray-700">
                    #{index + 1}
                  </span>
                </div>
              </div>

              {/* Gap Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900 capitalize">
                      {gap.type.replace('_', ' ')}
                    </h3>
                    <span className={clsx(
                      'text-xs px-2 py-1 rounded-full font-medium',
                      gap.severity === 'critical'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-amber-100 text-amber-800'
                    )}>
                      {gap.severity}
                    </span>
                  </div>

                  {gap.decision_id && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      REQ-{gap.decision_id.toString().padStart(3, '0')}
                    </span>
                  )}
                </div>

                <p className="text-gray-700 text-sm mb-3 leading-relaxed">
                  {gap.description}
                </p>

                <div className="bg-white/50 p-3 rounded border-l-4 border-blue-400">
                  <p className="text-xs font-medium text-blue-800 mb-1">
                    RECOMMENDATION
                  </p>
                  <p className="text-sm text-blue-700">
                    {gap.recommendation}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Priority Legend */}
      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Priority Levels</h4>
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div className="flex items-center gap-2">
            <Flag className="w-3 h-3 text-red-600" />
            <span className="text-gray-600">High (#1)</span>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span className="text-gray-600">Medium (#2-3)</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="w-3 h-3 text-gray-500" />
            <span className="text-gray-600">Low (#4+)</span>
          </div>
        </div>
      </div>
    </div>
  );
}