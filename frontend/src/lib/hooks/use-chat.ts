'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { useChatStore } from '@/lib/stores/chat-store';
import { useAuthStore } from '@/lib/stores/auth-store';
import type { Message, Conversation } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SSEData {
  id?: string;
  role?: string;
  content?: string;
  message?: string;
  conversation_id?: string;
  title?: string;
  sources?: unknown[];
  agent?: string;
}

export function useChat() {
  const router = useRouter();
  const { tokens } = useAuthStore();
  const {
    messages,
    setMessages,
    addMessage,
    currentConversationId,
    setCurrentConversationId,
    addConversation,
    isStreaming,
    setStreaming,
    setStreamingContent,
    appendStreamingContent,
    setLoading,
  } = useChatStore();

  const sendMessage = useCallback(async (
    content: string,
    file?: File,
    conversationId?: string,
    persistEmbeddings: boolean = true
  ) => {
    if (!tokens?.access) {
      toast.error('Please login first');
      return;
    }

    const targetConversationId = conversationId || currentConversationId;

    // Add user message optimistically
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    addMessage(userMessage);

    setLoading(true);
    setStreaming(true);
    setStreamingContent('');

    try {
      // Prepare request body
      const body: Record<string, unknown> = {
        message: content,
        persist_embeddings: persistEmbeddings,
      };

      if (targetConversationId) {
        body.conversation_id = targetConversationId;
      }

      // If file is attached, upload it first
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('persist_embeddings', String(persistEmbeddings));

        const uploadResponse = await fetch(`${API_URL}/api/documents/upload/`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${tokens.access}`,
          },
          body: formData,
        });

        if (uploadResponse.ok) {
          const uploadData = await uploadResponse.json();
          if (uploadData.document_key) {
            body.document_key = uploadData.document_key;
          }
        }
      }

      // Send SSE request
      const response = await fetch(`${API_URL}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens.access}`,
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Process SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';
      let newConversationId: string | null = null;
      let assistantContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete events
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            continue;
          }

          if (line.startsWith('data: ')) {
            try {
              const data: SSEData = JSON.parse(line.slice(6));

              // Handle different event types based on data
              if (data.conversation_id && !newConversationId) {
                newConversationId = data.conversation_id;
                setCurrentConversationId(newConversationId);
              }

              if (data.content && data.role === undefined) {
                // Token event
                assistantContent += data.content;
                appendStreamingContent(data.content);
              }

              if (data.role === 'assistant' && data.content) {
                // Full message event
                assistantContent = data.content;
              }

              if (data.title && newConversationId) {
                // Update conversation title
                const newConv: Conversation = {
                  id: newConversationId,
                  title: data.title,
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                };
                addConversation(newConv);
              }

              if (data.message && !data.content) {
                // Error event
                toast.error(data.message);
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }

      // Add final assistant message
      if (assistantContent) {
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: assistantContent,
          created_at: new Date().toISOString(),
        };
        addMessage(assistantMessage);
      }

      // Navigate to conversation if new
      if (newConversationId && newConversationId !== targetConversationId) {
        router.push(`/chat/${newConversationId}`);
      }

    } catch (error) {
      console.error('Chat error:', error);
      toast.error('Failed to send message');
    } finally {
      setLoading(false);
      setStreaming(false);
      setStreamingContent('');
    }
  }, [
    tokens,
    currentConversationId,
    addMessage,
    setLoading,
    setStreaming,
    setStreamingContent,
    appendStreamingContent,
    setCurrentConversationId,
    addConversation,
    router,
  ]);

  const loadConversation = useCallback(async (conversationId: string) => {
    if (!tokens?.access) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/`, {
        headers: {
          'Authorization': `Bearer ${tokens.access}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load conversation');
      }

      const data = await response.json();
      if (data.success && data.conversation) {
        setCurrentConversationId(conversationId);
        setMessages(data.conversation.messages || []);
      }
    } catch (error) {
      toast.error('Failed to load conversation');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [tokens, setLoading, setCurrentConversationId, setMessages]);

  const startNewChat = useCallback(() => {
    setCurrentConversationId(null);
    setMessages([]);
    router.push('/chat');
  }, [setCurrentConversationId, setMessages, router]);

  return {
    messages,
    isStreaming,
    sendMessage,
    loadConversation,
    startNewChat,
  };
}
