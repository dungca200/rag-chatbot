'use client';

import { useEffect, useRef } from 'react';
import { MessageBubble } from './message-bubble';
import { useChatStore } from '@/lib/stores/chat-store';
import type { Message } from '@/types';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const { isStreaming, streamingContent } = useChatStore();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
          <p className="text-gray-600 dark:text-gray-400">
            Ask a question or upload a document to get started
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <MessageBubble
            message={{
              id: 'streaming',
              role: 'assistant',
              content: streamingContent,
              created_at: new Date().toISOString(),
            }}
            isStreaming
          />
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
