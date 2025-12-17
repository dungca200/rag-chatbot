'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/auth-store';

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { setLoading, tokens } = useAuthStore();

  useEffect(() => {
    // Hydration complete - mark loading as done
    const timeout = setTimeout(() => {
      setLoading(false);
    }, 0);

    return () => clearTimeout(timeout);
  }, [setLoading, tokens]);

  return <>{children}</>;
}
