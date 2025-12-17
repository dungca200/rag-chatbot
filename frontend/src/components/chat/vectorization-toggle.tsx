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
          'relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300',
          enabled
            ? 'bg-gradient-to-r from-accent to-accent-secondary'
            : 'glass',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        role="switch"
        aria-checked={enabled}
      >
        <span
          className={cn(
            'inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-all duration-300',
            enabled ? 'translate-x-6' : 'translate-x-1',
            enabled && 'shadow-lg shadow-accent/50'
          )}
        />
      </button>
      <div className="flex items-center gap-2 text-sm">
        {enabled ? (
          <>
            <div className="p-1.5 rounded-lg bg-accent/10">
              <Database className="h-4 w-4 text-accent" />
            </div>
            <span className="text-foreground">Store in database</span>
          </>
        ) : (
          <>
            <div className="p-1.5 rounded-lg glass">
              <Clock className="h-4 w-4 text-muted-foreground" />
            </div>
            <span className="text-muted-foreground">Session only</span>
          </>
        )}
      </div>
    </div>
  );
}
