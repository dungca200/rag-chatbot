'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, Trash2, Sparkles } from 'lucide-react';
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
      <div className="p-6 text-center">
        <div className="inline-flex p-3 rounded-xl glass mb-3">
          <Sparkles className="h-5 w-5 text-accent" />
        </div>
        <p className="text-sm text-muted-foreground">
          No conversations yet
        </p>
        <p className="text-xs text-muted mt-1">
          Start a new chat to begin
        </p>
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1">
      {conversations.map((conversation, index) => {
        const isActive = pathname === `/chat/${conversation.id}`;
        return (
          <Link
            key={conversation.id}
            href={`/chat/${conversation.id}`}
            className={cn(
              'group relative flex items-center gap-3 px-3 py-3 rounded-xl',
              'transition-all duration-300 animate-fade-up',
              isActive
                ? 'glass glow-sm'
                : 'hover:bg-accent/5'
            )}
            style={{ animationDelay: `${index * 30}ms` }}
          >
            {/* Active indicator */}
            {isActive && (
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-r-full bg-gradient-to-b from-accent to-accent-secondary" />
            )}

            <div className={cn(
              'p-2 rounded-lg transition-all duration-300',
              isActive
                ? 'bg-accent/20'
                : 'bg-accent/5 group-hover:bg-accent/10'
            )}>
              <MessageSquare className={cn(
                'h-4 w-4 transition-colors',
                isActive ? 'text-accent' : 'text-muted-foreground group-hover:text-accent'
              )} />
            </div>

            <div className="flex-1 min-w-0">
              <span className={cn(
                'block text-sm truncate transition-colors',
                isActive ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'
              )}>
                {conversation.title || 'New Conversation'}
              </span>
            </div>

            <button
              onClick={(e) => handleDelete(e, conversation.id)}
              className={cn(
                'p-1.5 rounded-lg transition-all duration-300',
                'opacity-0 group-hover:opacity-100',
                'hover:bg-error/10 text-muted-foreground hover:text-error'
              )}
              aria-label="Delete conversation"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </Link>
        );
      })}
    </div>
  );
}
