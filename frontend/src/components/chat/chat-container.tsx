'use client';

import { useEffect, useRef } from 'react';
import { MessageList } from './message-list';
import { ChatInput } from './chat-input';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/stores/chat-store';

interface ChatContainerProps {
  conversationId?: string;
}

export function ChatContainer({ conversationId }: ChatContainerProps) {
  const { messages, isStreaming, sendMessage, loadConversation } = useChat();
  const { isLoading, currentConversationId } = useChatStore();
  const justNavigatedRef = useRef(false);

  useEffect(() => {
    if (conversationId) {
      // Skip loading if we just navigated here from sending a message
      // (messages already exist and current conversation matches)
      if (currentConversationId === conversationId && messages.length > 0) {
        justNavigatedRef.current = false;
        return;
      }
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation, currentConversationId, messages.length]);

  const handleSend = (message: string, file?: File, persistEmbeddings?: boolean) => {
    sendMessage(message, file, conversationId, persistEmbeddings);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <MessageList messages={messages} />
      <ChatInput
        onSend={handleSend}
        isLoading={isLoading || isStreaming}
      />
    </div>
  );
}
