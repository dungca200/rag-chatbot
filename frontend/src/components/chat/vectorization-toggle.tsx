'use client';

import { Database, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VectorizationToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
}

export function VectorizationToggle({ enabled, onChange, disabled }: VectorizationToggleProps) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => onChange(!enabled)}
        disabled={disabled}
        className={cn(
          'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
          enabled
            ? 'bg-blue-600'
            : 'bg-gray-300 dark:bg-gray-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        role="switch"
        aria-checked={enabled}
      >
        <span
          className={cn(
            'inline-block h-4 w-4 rounded-full bg-white transition-transform',
            enabled ? 'translate-x-6' : 'translate-x-1'
          )}
        />
      </button>
      <div className="flex items-center gap-1.5 text-sm">
        {enabled ? (
          <>
            <Database className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <span className="text-gray-700 dark:text-gray-300">Store in database</span>
          </>
        ) : (
          <>
            <Clock className="h-4 w-4 text-gray-500" />
            <span className="text-gray-500">Session only</span>
          </>
        )}
      </div>
    </div>
  );
}
