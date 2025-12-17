'use client';

import { useEffect } from 'react';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/stores/chat-store';

interface ChatContainerProps {
  conversationId?: string;
}

export function ChatContainer({ conversationId }: ChatContainerProps) {
  const { messages, isStreaming, sendMessage, loadConversation } = useChat();
  const { isLoading } = useChatStore();

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation]);

  const handleSend = (message: string, file?: File, persistEmbeddings?: boolean) => {
    sendMessage(message, file, conversationId, persistEmbeddings);
  };

  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} />
      <ChatInput
        onSend={handleSend}
        isLoading={isLoading || isStreaming}
      />
    </div>
  );
}
