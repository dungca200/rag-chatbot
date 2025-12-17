'use client';

import { use } from 'react';
import { ChatContainer } from '@/components/chat/chat-container';

interface ChatDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function ChatDetailPage({ params }: ChatDetailPageProps) {
  const { id } = use(params);
  return <ChatContainer conversationId={id} />;
}
