'use client';

import { Sidebar } from '@/components/sidebar/sidebar';
import { ConversationList } from '@/components/sidebar/conversation-list';
import { CursorGlow } from '@/components/ui/cursor-glow';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex h-screen overflow-hidden">
      {/* Cosmic background effects */}
      <div className="cosmic-bg" />
      <div className="noise-overlay" />
      <div className="grid-pattern" />

      {/* Cursor glow effect */}
      <CursorGlow />

      {/* Main content */}
      <Sidebar>
        <ConversationList />
      </Sidebar>
      <main className="relative flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
