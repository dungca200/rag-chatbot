'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Users, MessageSquare, FileText, Database, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '@/lib/api/client';
import type { AdminStats } from '@/types';

interface StatsCardProps {
  title: string;
  value: number;
  icon: React.ElementType;
  href?: string;
}

function StatsCard({ title, value, icon: Icon, href }: StatsCardProps) {
  const content = (
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-3xl font-bold mt-1 text-foreground">{value.toLocaleString()}</p>
        </div>
        <div className="p-3 bg-accent-subtle rounded-lg">
          <Icon className="h-6 w-6 text-accent" />
        </div>
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block hover:opacity-90 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiClient.get<{ success: boolean; stats: AdminStats }>(
          '/api/admin/stats/'
        );
        if (response.success) {
          setStats(response.stats);
        }
      } catch {
        toast.error('Failed to load admin stats');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Users"
          value={stats?.total_users || 0}
          icon={Users}
          href="/admin/users"
        />
        <StatsCard
          title="Conversations"
          value={stats?.total_conversations || 0}
          icon={MessageSquare}
        />
        <StatsCard
          title="Messages"
          value={stats?.total_messages || 0}
          icon={MessageSquare}
        />
        <StatsCard
          title="Documents"
          value={stats?.total_documents || 0}
          icon={FileText}
        />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4 text-foreground">Quick Links</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/admin/users"
            className="flex items-center gap-3 p-4 glass-card rounded-xl hover:border-accent transition-colors"
          >
            <Users className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="font-medium text-foreground">Manage Users</p>
              <p className="text-sm text-muted-foreground">
                View and manage user accounts
              </p>
            </div>
          </Link>
          <Link
            href="/documents"
            className="flex items-center gap-3 p-4 glass-card rounded-xl hover:border-accent transition-colors"
          >
            <Database className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="font-medium text-foreground">Vector Database</p>
              <p className="text-sm text-muted-foreground">
                View indexed documents
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
