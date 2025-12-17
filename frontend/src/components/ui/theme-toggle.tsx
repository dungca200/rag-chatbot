'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <button className={cn('p-2.5 rounded-xl glass', className)}>
        <Sun className="h-5 w-5 text-muted-foreground" />
      </button>
    );
  }

  const isDark = resolvedTheme === 'dark';

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className={cn(
        'relative p-2.5 rounded-xl glass',
        'hover:glow-sm transition-all duration-300',
        'text-muted-foreground hover:text-accent',
        className
      )}
      aria-label="Toggle theme"
    >
      <div className="relative">
        {isDark ? (
          <Sun className="h-5 w-5 transition-transform hover:rotate-45 duration-300" />
        ) : (
          <Moon className="h-5 w-5 transition-transform hover:-rotate-12 duration-300" />
        )}
      </div>
    </button>
  );
}
