'use client';

import { useState, createContext, useContext } from 'react';
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

// Context to share collapsed state with children
const SidebarContext = createContext<{ collapsed: boolean }>({ collapsed: false });
export const useSidebar = () => useContext(SidebarContext);

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
    <SidebarContext.Provider value={{ collapsed }}>
      <aside
        data-sidebar="true"
        className={cn(
          'relative flex flex-col h-screen glass-subtle transition-all duration-300 ease-out',
          collapsed ? 'w-[72px]' : 'w-72'
        )}
      >
        {/* Accent border */}
        <div className="absolute top-0 right-0 w-px h-full bg-gradient-to-b from-accent/50 via-accent-secondary/30 to-transparent" />

        {/* Header */}
        <div className={cn(
          'flex items-center p-4 border-b border-border/30',
          collapsed ? 'justify-center' : 'justify-between'
        )}>
          {!collapsed && (
            <div className="flex items-center gap-3 animate-fade-up">
              <div className="relative p-2 rounded-xl bg-accent/10 glow-sm">
                <Zap className="h-5 w-5 text-accent" />
              </div>
              <div>
                <h1 className="text-display text-base font-bold text-gradient">
                  RAG Chat
                </h1>
                <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
                  AI Assistant
                </p>
              </div>
            </div>
          )}

          {collapsed && (
            <div className="relative p-2 rounded-xl bg-accent/10 glow-sm">
              <Zap className="h-5 w-5 text-accent" />
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'absolute -right-3 top-20 z-10',
            'p-1.5 rounded-full glass border border-border/50',
            'hover:glow-sm transition-all duration-300',
            'text-muted-foreground hover:text-accent'
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronLeft className="h-3 w-3" />
          )}
        </button>

        {/* New Chat Button */}
        <div className={cn('p-3', collapsed && 'px-2')}>
          <Link
            href="/chat"
            className={cn(
              'group relative flex items-center gap-2 rounded-xl overflow-hidden',
              'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground',
              'hover:shadow-lg hover:shadow-accent/25 transition-all duration-300',
              'font-medium text-sm',
              collapsed ? 'justify-center p-3' : 'px-4 py-2.5'
            )}
            title={collapsed ? 'New Chat' : undefined}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
            <PlusCircle className="h-5 w-5 flex-shrink-0 relative z-10" />
            {!collapsed && <span className="relative z-10">New Chat</span>}
          </Link>
        </div>

        {/* Conversations slot */}
        <div className={cn(
          'flex-1 overflow-y-auto overflow-x-hidden',
          collapsed ? 'px-1' : 'px-2'
        )}>
          {children}
        </div>

        {/* Navigation */}
        <nav className={cn(
          'p-2 space-y-1 border-t border-border/30',
          collapsed && 'px-1.5'
        )}>
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
                  collapsed && 'justify-center px-0'
                )}
                style={{ animationDelay: `${index * 50}ms` }}
                title={collapsed ? item.label : undefined}
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
                  collapsed && 'justify-center px-0'
                )}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="h-5 w-5 flex-shrink-0 group-hover:scale-110 transition-transform" />
                {!collapsed && <span className="text-sm">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className={cn(
          'p-3 border-t border-border/30',
          collapsed ? 'space-y-2' : ''
        )}>
          {collapsed ? (
            // Collapsed: stack vertically, centered
            <>
              <button
                onClick={logout}
                className="group flex justify-center p-2.5 rounded-xl w-full text-muted-foreground hover:text-error hover:bg-error/5 transition-all duration-300"
                title="Logout"
              >
                <LogOut className="h-5 w-5 group-hover:scale-110 transition-transform" />
              </button>
              <div className="flex justify-center">
                <ThemeToggle />
              </div>
            </>
          ) : (
            // Expanded: single row with logout and theme toggle
            <div className="flex items-center justify-between px-1">
              <button
                onClick={logout}
                className="group flex items-center gap-2 px-3 py-2 rounded-xl text-muted-foreground hover:text-error hover:bg-error/5 transition-all duration-300"
              >
                <LogOut className="h-4 w-4 group-hover:scale-110 transition-transform" />
                <span className="text-sm">Logout</span>
              </button>
              <ThemeToggle />
            </div>
          )}
        </div>
      </aside>
    </SidebarContext.Provider>
  );
}
