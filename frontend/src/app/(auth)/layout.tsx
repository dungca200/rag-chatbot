'use client';

import { ThemeToggle } from '@/components/ui/theme-toggle';
import { CursorGlow } from '@/components/ui/cursor-glow';
import { Zap } from 'lucide-react';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen flex flex-col overflow-hidden">
      {/* Cursor glow effect */}
      <CursorGlow />

      {/* Cosmic background */}
      <div className="cosmic-bg" />
      <div className="noise-overlay" />
      <div className="grid-pattern" />

      {/* Extra cosmic orbs for auth pages */}
      <div className="fixed top-1/4 left-1/4 w-96 h-96 rounded-full bg-accent/20 blur-[100px] -z-10 animate-float" />
      <div className="fixed bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-accent-secondary/20 blur-[80px] -z-10 animate-float" style={{ animationDelay: '1s' }} />

      {/* Theme toggle */}
      <div className="absolute top-6 right-6 z-50">
        <ThemeToggle />
      </div>

      {/* Logo */}
      <div className="absolute top-6 left-6 z-10">
        <div className="flex items-center gap-3 animate-fade-up">
          <div className="relative p-2.5 rounded-xl glass glow-sm">
            <Zap className="h-5 w-5 text-accent" />
          </div>
          <div>
            <span className="text-display font-bold text-gradient">RAG Chat</span>
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
              AI Assistant
            </p>
          </div>
        </div>
      </div>

      <main className="relative flex-1 flex items-center justify-center p-6 z-10">
        {children}
      </main>

      {/* Footer */}
      <footer className="relative z-10 pb-6 text-center">
        <p className="text-xs text-muted-foreground">
          Powered by advanced language models
        </p>
      </footer>
    </div>
  );
}
