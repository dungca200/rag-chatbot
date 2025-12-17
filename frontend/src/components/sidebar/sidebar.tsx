'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  MessageSquare,
  FileText,
  Settings,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
  PlusCircle,
  Shield,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/hooks/use-auth';
import { ThemeToggle } from '@/components/ui/theme-toggle';

interface SidebarProps {
  children?: React.ReactNode;
}

const navItems = [
  { href: '/chat', label: 'Chat', icon: MessageSquare },
  { href: '/documents', label: 'Documents', icon: FileText },
  { href: '/profile', label: 'Profile', icon: User },
  { href: '/settings', label: 'Settings', icon: Settings },
];

const adminItems = [
  { href: '/admin', label: 'Admin', icon: Shield },
];

export function Sidebar({ children }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { logout, user } = useAuth();

  return (
    <aside
      data-sidebar="true"
      className={cn(
        'relative flex flex-col h-screen glass-subtle transition-all duration-300',
        collapsed ? 'w-[72px]' : 'w-72'
      )}
    >
      {/* Accent line */}
      <div className="absolute top-0 right-0 w-px h-full bg-gradient-to-b from-accent/50 via-accent-secondary/30 to-transparent" />

      {/* Header */}
      <div className="flex items-center justify-between p-4">
        {!collapsed && (
          <div className="flex items-center gap-3 animate-fade-up">
            <div className="relative p-2.5 rounded-xl bg-accent/10 glow-sm">
              <Zap className="h-5 w-5 text-accent" />
              <div className="absolute inset-0 rounded-xl bg-accent/20 blur-md -z-10" />
            </div>
            <div>
              <h1 className="text-display text-lg font-bold text-gradient">
                RAG Chat
              </h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
                AI Assistant
              </p>
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'p-2 rounded-xl glass hover:glow-sm transition-all duration-300 text-muted-foreground hover:text-accent',
            collapsed && 'mx-auto'
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 pb-3">
        <Link
          href="/chat"
          className={cn(
            'group relative flex items-center gap-3 px-4 py-3 rounded-xl overflow-hidden',
            'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground',
            'hover:shadow-lg hover:shadow-accent/25 transition-all duration-300',
            'font-medium text-sm',
            collapsed && 'justify-center px-3'
          )}
        >
          {/* Shimmer effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
          <PlusCircle className="h-5 w-5 flex-shrink-0 relative z-10" />
          {!collapsed && <span className="relative z-10">New Chat</span>}
        </Link>
      </div>

      {/* Conversations slot */}
      {children && (
        <div className="flex-1 overflow-y-auto px-2">
          {children}
        </div>
      )}

      {/* Navigation */}
      <nav className="p-3 space-y-1 border-t border-border/50">
        {navItems.map((item, index) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300',
                'animate-fade-up',
                isActive
                  ? 'glass glow-sm text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/5',
                collapsed && 'justify-center px-2'
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <item.icon className={cn(
                'h-5 w-5 flex-shrink-0 transition-transform duration-300',
                'group-hover:scale-110',
                isActive && 'drop-shadow-[0_0_8px_var(--accent-glow)]'
              )} />
              {!collapsed && <span className="text-sm">{item.label}</span>}
              {isActive && !collapsed && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
              )}
            </Link>
          );
        })}

        {/* Admin link for staff users */}
        {user?.is_staff && adminItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300',
                isActive
                  ? 'glass glow-sm text-accent'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/5',
                collapsed && 'justify-center px-2'
              )}
            >
              <item.icon className="h-5 w-5 flex-shrink-0 group-hover:scale-110 transition-transform" />
              {!collapsed && <span className="text-sm">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border/50 space-y-2">
        <div className={cn('flex items-center', collapsed ? 'justify-center' : 'justify-between px-2')}>
          <ThemeToggle />
        </div>
        <button
          onClick={logout}
          className={cn(
            'group flex items-center gap-3 px-3 py-2.5 rounded-xl w-full',
            'text-muted-foreground hover:text-error transition-all duration-300',
            'hover:bg-error/5',
            collapsed && 'justify-center px-2'
          )}
        >
          <LogOut className="h-5 w-5 flex-shrink-0 group-hover:scale-110 transition-transform" />
          {!collapsed && <span className="text-sm">Logout</span>}
        </button>
      </div>
    </aside>
  );
}
