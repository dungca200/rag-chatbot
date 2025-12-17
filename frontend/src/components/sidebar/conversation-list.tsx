'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/lib/stores/chat-store';
import { apiClient } from '@/lib/api/client';
import toast from 'react-hot-toast';
import type { Conversation } from '@/types';

export function ConversationList() {
  const pathname = usePathname();
  const { conversations, setConversations, removeConversation } = useChatStore();

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await apiClient.get<{ success: boolean; conversations: Conversation[] }>(
          '/api/chat/conversations/'
        );
        if (response.success) {
          setConversations(response.conversations);
        }
      } catch (error) {
        console.error('Failed to fetch conversations:', error);
      }
    };

    fetchConversations();
  }, [setConversations]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      await apiClient.delete(`/api/chat/conversations/${id}/delete/`);
      removeConversation(id);
      toast.success('Conversation deleted');
    } catch (error) {
      toast.error('Failed to delete conversation');
    }
  };

  if (conversations.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
        No conversations yet
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
      {conversations.map((conversation) => {
        const isActive = pathname === `/chat/${conversation.id}`;
        return (
          <Link
            key={conversation.id}
            href={`/chat/${conversation.id}`}
            className={cn(
              'group flex items-center gap-2 px-3 py-2 rounded-lg transition-colors',
              isActive
                ? 'bg-gray-200 dark:bg-gray-800'
                : 'hover:bg-gray-100 dark:hover:bg-gray-800/50'
            )}
          >
            <MessageSquare className="h-4 w-4 flex-shrink-0 text-gray-500" />
            <span className="flex-1 truncate text-sm">
              {conversation.title || 'New Conversation'}
            </span>
            <button
              onClick={(e) => handleDelete(e, conversation.id)}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-300 dark:hover:bg-gray-700 transition-opacity"
              aria-label="Delete conversation"
            >
              <Trash2 className="h-4 w-4 text-gray-500 hover:text-red-500" />
            </button>
          </Link>
        );
      })}
    </div>
  );
}
