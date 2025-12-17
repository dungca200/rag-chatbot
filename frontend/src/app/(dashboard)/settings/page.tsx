'use client';

import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';
import { cn } from '@/lib/utils';

const themes = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        <div className="animate-pulse bg-card h-48 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="glass-card rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4 text-foreground">Appearance</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Choose how the app looks to you.
        </p>

        <div className="grid grid-cols-3 gap-3">
          {themes.map((t) => {
            const Icon = t.icon;
            const isActive = theme === t.value;
            return (
              <button
                key={t.value}
                onClick={() => setTheme(t.value)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors',
                  isActive
                    ? 'border-accent bg-accent-subtle'
                    : 'border-border hover:border-accent/50'
                )}
              >
                <Icon className={cn(
                  'h-6 w-6',
                  isActive ? 'text-accent' : 'text-muted-foreground'
                )} />
                <span className={cn(
                  'text-sm font-medium',
                  isActive ? 'text-accent' : 'text-foreground'
                )}>
                  {t.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
