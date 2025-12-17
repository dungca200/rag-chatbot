'use client';

import { useEffect } from 'react';
import { ChatContainer } from '@/components/chat/chat-container';
import { useChatStore } from '@/lib/stores/chat-store';

export default function ChatPage() {
  const { setCurrentConversationId, setMessages } = useChatStore();

  // Reset to new chat state
  useEffect(() => {
    setCurrentConversationId(null);
    setMessages([]);
  }, [setCurrentConversationId, setMessages]);

  return <ChatContainer />;
}
