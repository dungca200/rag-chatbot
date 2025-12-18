'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, FileText, Image, FileSpreadsheet, Loader2, Send, Maximize2, Minimize2, User, Zap, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { apiClient } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import type { Document, Message, Source, AuthTokens } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getTokens(): AuthTokens | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem('tokens');
  return stored ? JSON.parse(stored) : null;
}

function getFileIcon(fileType: string) {
  if (fileType === 'image') return Image;
  if (fileType === 'xlsx') return FileSpreadsheet;
  return FileText;
}

export default function DocumentViewerPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchDocument();
  }, [documentId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load conversation when document is loaded
  useEffect(() => {
    if (document?.document_key) {
      loadConversation(document.document_key);
    }
  }, [document?.document_key]);

  const fetchDocument = async () => {
    try {
      const response = await apiClient.get<{ success: boolean; document: Document }>(
        `/api/documents/${documentId}/`
      );
      if (response.success) {
        setDocument(response.document);
      }
    } catch (error) {
      toast.error('Failed to load document');
      router.push('/documents');
    } finally {
      setIsLoading(false);
    }
  };

  const loadConversation = async (documentKey: string) => {
    const tokens = getTokens();
    if (!tokens?.access) return;

    console.log('[Document Chat] Loading conversation for document:', documentKey);
    setIsLoadingConversation(true);
    try {
      const response = await fetch(
        `${API_URL}/api/chat/conversations/document/${documentKey}/`,
        {
          headers: {
            'Authorization': `Bearer ${tokens.access}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        console.log('[Document Chat] Load response:', data);
        if (data.success && data.exists && data.conversation) {
          console.log('[Document Chat] Found existing conversation:', data.conversation.id);
          setConversationId(data.conversation.id);
          // Map messages to include proper id format
          const loadedMessages = (data.conversation.messages || []).map((msg: Message) => ({
            ...msg,
            id: msg.id || `${msg.role}-${Date.now()}-${Math.random()}`,
          }));
          setMessages(loadedMessages);
        } else {
          console.log('[Document Chat] No existing conversation found');
        }
      }
    } catch (error) {
      console.error('[Document Chat] Failed to load conversation:', error);
    } finally {
      setIsLoadingConversation(false);
    }
  };

  const handleDeleteConversation = async () => {
    if (!conversationId) {
      // No conversation to delete, just clear messages
      setMessages([]);
      return;
    }

    const tokens = getTokens();
    if (!tokens?.access) {
      toast.error('Please login first');
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/chat/conversations/${conversationId}/delete/`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${tokens.access}`,
          },
        }
      );

      if (response.ok) {
        setMessages([]);
        setConversationId(null);
        toast.success('Conversation deleted');
      } else {
        toast.error('Failed to delete conversation');
      }
    } catch (error) {
      toast.error('Failed to delete conversation');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isSending || !document) return;

    const tokens = getTokens();
    if (!tokens?.access) {
      toast.error('Please login first');
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      // Create a placeholder for the assistant message
      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          created_at: new Date().toISOString(),
        },
      ]);

      // Use SSE for streaming response
      const requestBody = {
        message: userMessage.content,
        document_key: document.document_key,
        conversation_id: conversationId,
      };
      console.log('[Document Chat] Sending message with:', requestBody);

      const response = await fetch(`${API_URL}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens.access}`,
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let sources: Source[] = [];
      let buffer = '';
      let newConversationId: string | null = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                // Conversation created event - has ONLY id, no role/content
                if (data.id && !data.role && !data.content && !conversationId && !newConversationId) {
                  newConversationId = data.id;
                  console.log('[Document Chat] New conversation created:', newConversationId);
                }

                // Done event - has conversation_id
                if (data.conversation_id && !conversationId && !newConversationId) {
                  newConversationId = data.conversation_id;
                  console.log('[Document Chat] Conversation ID from done event:', newConversationId);
                }

                // Token event - has content but no role
                if (data.content && data.role === undefined) {
                  fullContent += data.content;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId ? { ...m, content: fullContent } : m
                    )
                  );
                }

                // Full message event - has role: assistant
                if (data.role === 'assistant' && data.sources) {
                  sources = data.sources || [];
                }

                // Error event
                if (data.message && !data.content && !data.role) {
                  throw new Error(data.message);
                }
              } catch (e) {
                if (e instanceof Error && e.message !== 'Unexpected end of JSON input') {
                  throw e;
                }
              }
            }
          }
        }
      }

      // Update conversation ID if new conversation was created
      if (newConversationId && !conversationId) {
        setConversationId(newConversationId);
      }

      // Update final message with sources
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: fullContent, sources }
            : m
        )
      );
    } catch (error) {
      toast.error('Failed to get response');
      // Remove the empty assistant message on error
      setMessages((prev) => prev.filter((m) => m.content !== ''));
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize textarea
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  };

  // Reset textarea height when input is cleared (after sending)
  useEffect(() => {
    if (!input && inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  }, [input]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Document not found</p>
      </div>
    );
  }

  const FileIcon = getFileIcon(document.file_type);
  const canPreview = document.file_url && (document.file_type === 'pdf' || document.file_type === 'image');

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center gap-4 p-4 border-b border-border/30 glass-subtle">
        <button
          onClick={() => router.push('/documents')}
          className="p-2 rounded-xl glass hover:glow-sm transition-all text-muted-foreground hover:text-accent"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="p-2 rounded-xl bg-gradient-to-br from-accent to-accent-secondary">
            <FileIcon className="h-5 w-5 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">
              {document.original_filename}
            </h1>
            <p className="text-xs text-muted-foreground">
              {document.file_type.toUpperCase()} • {document.file_size_display} • {document.chunk_count} chunks
            </p>
          </div>
        </div>
        {canPreview && (
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-xl glass hover:glow-sm transition-all text-muted-foreground hover:text-accent"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen document'}
          >
            {isFullscreen ? <Minimize2 className="h-5 w-5" /> : <Maximize2 className="h-5 w-5" />}
          </button>
        )}
      </div>

      {/* Main content - split view */}
      <div className="flex-1 flex overflow-hidden">
        {/* Document Preview - Left side */}
        <div className={cn(
          'border-r border-border/30 overflow-hidden transition-all duration-300',
          isFullscreen ? 'flex-1' : 'w-2/3'
        )}>
          {canPreview ? (
            document.file_type === 'pdf' ? (
              <iframe
                src={`${document.file_url}#toolbar=1&navpanes=0`}
                className="w-full h-full bg-background-secondary"
                title={document.original_filename}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-background-secondary p-4">
                <img
                  src={document.file_url}
                  alt={document.original_filename}
                  className="max-w-full max-h-full object-contain rounded-lg"
                />
              </div>
            )
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center bg-background-secondary p-8">
              <div className="p-6 rounded-2xl glass mb-4">
                <FileIcon className="h-16 w-16 text-muted-foreground" />
              </div>
              <p className="text-muted-foreground text-center">
                Preview not available for this file type.
                <br />
                <span className="text-sm">You can still ask questions about this document.</span>
              </p>
            </div>
          )}
        </div>

        {/* Chat - Right side */}
        {!isFullscreen && (
          <div className="w-1/3 flex flex-col overflow-hidden">
            {/* Chat header with delete button */}
            {messages.length > 0 && (
              <div className="flex-shrink-0 flex items-center justify-between px-4 py-2 border-b border-border/30">
                <span className="text-xs text-muted-foreground">
                  {messages.length} message{messages.length !== 1 ? 's' : ''}
                </span>
                <button
                  onClick={handleDeleteConversation}
                  className="p-1.5 rounded-lg glass hover:bg-error/10 hover:text-error transition-all text-muted-foreground"
                  title="Delete conversation"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Chat messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {isLoadingConversation ? (
                <div className="h-full flex items-center justify-center">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Loading conversation...</span>
                  </div>
                </div>
              ) : messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <div className="p-4 rounded-2xl glass mb-4 glow-sm">
                    <FileText className="h-8 w-8 text-accent" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    Ask about this document
                  </h3>
                  <p className="text-sm text-muted-foreground max-w-xs">
                    Ask questions about the content of "{document.original_filename}" and get AI-powered answers.
                  </p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex gap-2',
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    {/* Assistant icon */}
                    {message.role === 'assistant' && (
                      <div className="flex-shrink-0 p-2 rounded-xl bg-accent/10 h-fit">
                        <Zap className="h-4 w-4 text-accent" />
                      </div>
                    )}

                    <div
                      className={cn(
                        'max-w-[80%] p-3 rounded-2xl text-sm',
                        message.role === 'user'
                          ? 'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground'
                          : 'glass-card'
                      )}
                    >
                      {message.content ? (
                        message.role === 'assistant' ? (
                          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                          </div>
                        ) : (
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        )
                      ) : (
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-muted-foreground">Thinking...</span>
                        </div>
                      )}
                    </div>

                    {/* User icon */}
                    {message.role === 'user' && (
                      <div className="flex-shrink-0 p-2 rounded-xl bg-accent-secondary/10 h-fit">
                        <User className="h-4 w-4 text-accent-secondary" />
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Chat input */}
            <div className="flex-shrink-0 p-4 border-t border-border/30">
              <div className="flex items-end gap-2 p-2 rounded-xl glass">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about this document..."
                  disabled={isSending}
                  rows={1}
                  className="flex-1 resize-none bg-transparent py-2 px-2 text-sm text-foreground placeholder-muted-foreground focus:outline-none disabled:opacity-50 max-h-[150px] overflow-y-auto"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isSending}
                  className={cn(
                    'p-2.5 rounded-xl transition-all',
                    'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground',
                    'hover:shadow-lg hover:shadow-accent/25',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {isSending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
