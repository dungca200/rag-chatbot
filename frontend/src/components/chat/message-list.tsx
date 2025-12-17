'use client';

import { useEffect, useRef } from 'react';
import { MessageBubble } from './message-bubble';
import { useChatStore } from '@/lib/stores/chat-store';
import { Sparkles, FileUp, Globe, MessageCircle, Zap, ArrowRight } from 'lucide-react';
import type { Message } from '@/types';

interface MessageListProps {
  messages: Message[];
}

const suggestions = [
  {
    icon: FileUp,
    title: 'Analyze Documents',
    description: 'Upload PDFs, DOCX, or images for intelligent analysis',
    gradient: 'from-accent to-cyan-400',
  },
  {
    icon: Globe,
    title: 'Search the Web',
    description: 'Get real-time information from across the internet',
    gradient: 'from-accent-secondary to-purple-400',
  },
  {
    icon: MessageCircle,
    title: 'Have a Conversation',
    description: 'Ask questions, brainstorm ideas, or get assistance',
    gradient: 'from-accent to-accent-secondary',
  },
];

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const { isStreaming, streamingContent } = useChatStore();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center p-8 overflow-y-auto">
        <div className="text-center max-w-xl animate-fade-up">
          {/* Animated logo */}
          <div className="relative inline-flex mb-8">
            <div className="relative p-6 rounded-3xl glass animate-float">
              <Zap className="h-12 w-12 text-accent" />
              {/* Orbiting particles */}
              <div className="absolute inset-0 animate-[spin_10s_linear_infinite]">
                <div className="absolute top-0 left-1/2 w-2 h-2 rounded-full bg-accent -translate-x-1/2 -translate-y-1/2" />
              </div>
              <div className="absolute inset-0 animate-[spin_15s_linear_infinite_reverse]">
                <div className="absolute bottom-0 left-1/2 w-1.5 h-1.5 rounded-full bg-accent-secondary -translate-x-1/2 translate-y-1/2" />
              </div>
            </div>
            {/* Large glow */}
            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-accent/30 to-accent-secondary/30 blur-2xl -z-10 scale-150" />
          </div>

          {/* Title with gradient */}
          <h2 className="text-display text-4xl font-bold mb-4">
            <span className="text-gradient">How can I help</span>
            <br />
            <span className="text-foreground">you today?</span>
          </h2>

          <p className="text-muted-foreground mb-10 max-w-md mx-auto">
            I&apos;m your AI assistant powered by advanced language models.
            Ask me anything, upload documents, or search the web.
          </p>

          {/* Suggestion cards */}
          <div className="grid gap-4">
            {suggestions.map((suggestion, index) => (
              <div
                key={index}
                className="group relative p-5 rounded-2xl glass-card text-left cursor-pointer overflow-hidden animate-fade-up"
                style={{ animationDelay: `${(index + 1) * 100}ms` }}
              >
                {/* Hover gradient overlay */}
                <div className={cn(
                  'absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500',
                  `bg-gradient-to-r ${suggestion.gradient}`
                )} />

                <div className="relative flex items-start gap-4">
                  {/* Icon with gradient background */}
                  <div className={cn(
                    'p-3 rounded-xl bg-gradient-to-br transition-transform duration-300 group-hover:scale-110',
                    suggestion.gradient
                  )}>
                    <suggestion.icon className="h-5 w-5 text-white" />
                  </div>

                  <div className="flex-1">
                    <h3 className="text-display font-semibold text-foreground mb-1 group-hover:text-accent transition-colors">
                      {suggestion.title}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {suggestion.description}
                    </p>
                  </div>

                  <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-accent group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            ))}
          </div>

          {/* Keyboard hint */}
          <div className="mt-8 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <kbd className="px-2 py-1 rounded glass text-[10px] font-mono">Enter</kbd>
            <span>to send</span>
            <span className="mx-2">•</span>
            <kbd className="px-2 py-1 rounded glass text-[10px] font-mono">Shift + Enter</kbd>
            <span>for new line</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-4xl mx-auto py-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isStreaming && (
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

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
