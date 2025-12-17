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
      className={cn(
        'flex flex-col h-screen border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
          {!collapsed && (
            <h1 className="text-lg font-semibold">RAG Chat</h1>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <ChevronLeft className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Link
            href="/chat"
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors',
              collapsed && 'justify-center px-2'
            )}
          >
            <PlusCircle className="h-5 w-5 flex-shrink-0" />
            {!collapsed && <span>New Chat</span>}
          </Link>
        </div>

        {/* Conversations slot */}
        {children && (
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        )}

        {/* Navigation */}
        <nav className="p-3 space-y-1 border-t border-gray-200 dark:border-gray-800">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                  isActive
                    ? 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800',
                  collapsed && 'justify-center px-2'
                )}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
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
                  'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                  isActive
                    ? 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800',
                  collapsed && 'justify-center px-2'
                )}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-gray-200 dark:border-gray-800 space-y-1">
          <div className={cn('flex items-center', collapsed ? 'justify-center' : 'justify-between px-3')}>
            <ThemeToggle />
          </div>
        <button
          onClick={logout}
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors w-full',
            collapsed && 'justify-center px-2'
          )}
        >
          <LogOut className="h-5 w-5 flex-shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}
