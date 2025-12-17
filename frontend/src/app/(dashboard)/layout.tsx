'use client';

import { Sidebar } from '@/components/sidebar/sidebar';
import { ConversationList } from '@/components/sidebar/conversation-list';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar>
        <ConversationList />
      </Sidebar>
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
