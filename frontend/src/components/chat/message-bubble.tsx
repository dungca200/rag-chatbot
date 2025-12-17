'use client';

import { User, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Message } from '@/types';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 px-4 py-4',
        isUser ? 'bg-transparent' : 'bg-gray-50 dark:bg-gray-900/50'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
        )}
      >
        {isUser ? (
          <User className="h-5 w-5" />
        ) : (
          <Bot className="h-5 w-5" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm mb-1">
          {isUser ? 'You' : 'Assistant'}
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap">{message.content}</p>
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-gray-400 dark:bg-gray-500 animate-pulse ml-1" />
          )}
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
              Sources ({message.sources.length})
            </div>
            <div className="space-y-2">
              {message.sources.map((source, index) => (
                <div
                  key={index}
                  className="text-xs p-2 bg-gray-100 dark:bg-gray-800 rounded-lg"
                >
                  <p className="text-gray-600 dark:text-gray-400 line-clamp-2">
                    {typeof source === 'string' ? source : source.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
