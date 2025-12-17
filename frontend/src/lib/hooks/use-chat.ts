'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { useChatStore } from '@/lib/stores/chat-store';
import type { Message, Conversation, AuthTokens } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Helper to get fresh tokens from localStorage (synced by apiClient)
function getFreshTokens(): AuthTokens | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem('tokens');
  return stored ? JSON.parse(stored) : null;
}

// Helper to refresh token
async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  try {
    const response = await fetch(`${API_URL}/api/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    // Update localStorage
    localStorage.setItem('tokens', JSON.stringify({ access: data.access, refresh: refreshToken }));
    return data.access;
  } catch {
    return null;
  }
}

interface SSEData {
  id?: string;
  role?: string;
  content?: string;
  message?: string;
  conversation_id?: string;
  title?: string;
  sources?: unknown[];
  agent?: string;
  file?: {
    name: string;
    size: number;
    type: string;
    url?: string;
  };
}

export function useChat() {
  const router = useRouter();
  const {
    messages,
    setMessages,
    addMessage,
    updateMessage,
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
    // Get fresh tokens from localStorage
    let currentTokens = getFreshTokens();
    if (!currentTokens?.access) {
      toast.error('Please login first');
      return;
    }

    const targetConversationId = conversationId || currentConversationId;

    // Use default message if only file is provided
    const messageContent = content || (file ? `Analyze this file: ${file.name}` : '');

    // File info to be updated after upload
    let fileInfo: { name: string; size: number; type: string; url?: string } | undefined;
    if (file) {
      fileInfo = { name: file.name, size: file.size, type: file.type };
    }

    // Add user message optimistically with file info
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: messageContent,
      created_at: new Date().toISOString(),
      file: fileInfo,
    };
    addMessage(userMessage);

    setLoading(true);
    setStreaming(true);
    setStreamingContent('');

    try {
      // Prepare request body
      const body: Record<string, unknown> = {
        message: messageContent,
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
            'Authorization': `Bearer ${currentTokens.access}`,
          },
          body: formData,
        });

        if (uploadResponse.ok) {
          const uploadData = await uploadResponse.json();
          if (uploadData.document_key) {
            body.document_key = uploadData.document_key;
          }
          // Update file info with data from upload (including URL if available)
          fileInfo = {
            name: uploadData.filename || file.name,
            size: uploadData.file_size || file.size,
            type: uploadData.file_type || file.type,
            url: uploadData.file_url || undefined,
          };
          // Update the optimistic message with the file URL
          updateMessage(userMessage.id, { file: fileInfo });
        }
        // Always include file info for message storage (even without URL)
        body.file_info = fileInfo;
      }

      // Send SSE request with retry on 401
      let response = await fetch(`${API_URL}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentTokens.access}`,
        },
        body: JSON.stringify(body),
      });

      // Handle 401 - try refresh token
      if (response.status === 401 && currentTokens.refresh) {
        const newAccessToken = await refreshAccessToken(currentTokens.refresh);
        if (newAccessToken) {
          response = await fetch(`${API_URL}/api/chat/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${newAccessToken}`,
            },
            body: JSON.stringify(body),
          });
        }
      }

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
    currentConversationId,
    addMessage,
    updateMessage,
    setLoading,
    setStreaming,
    setStreamingContent,
    appendStreamingContent,
    setCurrentConversationId,
    addConversation,
    router,
  ]);

  const loadConversation = useCallback(async (conversationId: string) => {
    const currentTokens = getFreshTokens();
    if (!currentTokens?.access) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/`, {
        headers: {
          'Authorization': `Bearer ${currentTokens.access}`,
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
  }, [setLoading, setCurrentConversationId, setMessages]);

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
