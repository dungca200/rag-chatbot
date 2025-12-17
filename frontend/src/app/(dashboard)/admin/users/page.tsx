'use client';

import { useEffect, useState } from 'react';
import { User, Loader2, Shield, ShieldOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { AdminUser } from '@/types';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await apiClient.get<{ success: boolean; users: AdminUser[] }>(
          '/api/admin/users/'
        );
        if (response.success) {
          setUsers(response.users);
        }
      } catch {
        toast.error('Failed to load users');
      } finally {
        setIsLoading(false);
      }
    };

    fetchUsers();
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
      <h1 className="text-2xl font-bold mb-6">Users</h1>

      {users.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <User className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <h2 className="text-lg font-semibold mb-2">No users yet</h2>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800">
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  User
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Role
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Status
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Conversations
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Documents
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Joined
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-gray-100 dark:border-gray-800 last:border-0"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                        <User className="h-4 w-4 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{user.username}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {user.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {user.is_staff ? (
                        <>
                          <Shield className="h-4 w-4 text-blue-600" />
                          <span className="text-sm text-blue-600 font-medium">Admin</span>
                        </>
                      ) : (
                        <>
                          <ShieldOff className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-600 dark:text-gray-400">User</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        user.is_active
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      )}
                    >
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {user.conversation_count}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {user.document_count}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {new Date(user.date_joined).toLocaleDateString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
