'use client';

import { useState } from 'react';
import { User, Bot, ChevronDown, ChevronUp, FileText, Sparkles, Image, FileSpreadsheet, File } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { FilePreviewModal } from './file-preview-modal';
import type { Message } from '@/types';

function getFileExtension(fileName: string): string {
  return fileName.toLowerCase().split('.').pop() || '';
}

function getFileTypeLabel(fileName: string): string {
  const ext = getFileExtension(fileName);
  const typeMap: Record<string, string> = {
    'pdf': 'PDF',
    'docx': 'Word',
    'doc': 'Word',
    'xlsx': 'Excel',
    'xlsm': 'Excel',
    'txt': 'Text',
    'png': 'Image',
    'jpg': 'Image',
    'jpeg': 'Image',
    'gif': 'Image',
    'bmp': 'Image',
    'tiff': 'Image',
  };
  return typeMap[ext] || ext.toUpperCase();
}

function getFileIconColor(fileName: string): string {
  const ext = getFileExtension(fileName);
  const colorMap: Record<string, string> = {
    'pdf': 'bg-red-500',
    'docx': 'bg-blue-500',
    'doc': 'bg-blue-500',
    'xlsx': 'bg-green-500',
    'xlsm': 'bg-green-500',
    'txt': 'bg-gray-500',
    'png': 'bg-purple-500',
    'jpg': 'bg-purple-500',
    'jpeg': 'bg-purple-500',
    'gif': 'bg-purple-500',
  };
  return colorMap[ext] || 'bg-gray-500';
}

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showSources, setShowSources] = useState(false);
  const [showFilePreview, setShowFilePreview] = useState(false);
  const hasSources = message.sources && message.sources.length > 0;
  const hasFile = isUser && message.file;

  return (
    <div
      className={cn(
        'flex gap-4 px-6 py-5',
        isUser ? 'flex-row-reverse animate-slide-right' : 'animate-slide-left'
      )}
    >
      {/* Avatar with glow effect */}
      <div className="relative flex-shrink-0">
        <div
          className={cn(
            'relative w-10 h-10 rounded-xl flex items-center justify-center overflow-hidden',
            'transition-all duration-300',
            isUser
              ? 'bg-gradient-to-br from-accent to-accent-secondary'
              : 'glass'
          )}
        >
          {isUser ? (
            <User className="h-5 w-5 text-accent-foreground" />
          ) : (
            <Bot className="h-5 w-5 text-accent" />
          )}
        </div>
        {/* Glow behind avatar */}
        <div
          className={cn(
            'absolute inset-0 rounded-xl blur-lg -z-10 opacity-50',
            isUser
              ? 'bg-gradient-to-br from-accent to-accent-secondary'
              : 'bg-accent/30'
          )}
        />
      </div>

      {/* Content */}
      <div className={cn('flex-1 min-w-0 max-w-2xl', isUser ? 'text-right' : 'text-left')}>
        {/* Role label */}
        <div className={cn(
          'flex items-center gap-2 mb-2',
          isUser ? 'justify-end' : 'justify-start'
        )}>
          {!isUser && <Sparkles className="h-3 w-3 text-accent" />}
          <span className="text-[11px] text-muted-foreground uppercase tracking-widest font-medium">
            {isUser ? 'You' : 'Assistant'}
          </span>
        </div>

        {/* File attachment card - appears above message for user */}
        {hasFile && message.file && (
          <div
            onClick={() => {
              if (message.file?.url) {
                setShowFilePreview(true);
              }
            }}
            className={cn(
              'mb-2 p-3 rounded-xl flex items-center gap-3',
              'glass-card',
              message.file?.url ? 'cursor-pointer' : 'cursor-default',
              'transition-colors',
              isUser ? 'ml-auto' : 'mr-auto'
            )}
            style={{ maxWidth: '280px' }}
          >
            {/* File type icon */}
            <div className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
              getFileIconColor(message.file.name)
            )}>
              {getFileTypeLabel(message.file.name) === 'Image' ? (
                <Image className="w-5 h-5 text-white" />
              ) : getFileTypeLabel(message.file.name) === 'PDF' ? (
                <FileText className="w-5 h-5 text-white" />
              ) : getFileTypeLabel(message.file.name) === 'Excel' ? (
                <FileSpreadsheet className="w-5 h-5 text-white" />
              ) : (
                <File className="w-5 h-5 text-white" />
              )}
            </div>
            {/* File info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {message.file.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {getFileTypeLabel(message.file.name)}
                {message.file.size && ` • ${(message.file.size / 1024).toFixed(1)} KB`}
              </p>
            </div>
          </div>
        )}

        {/* Message bubble */}
        <div
          className={cn(
            'inline-block rounded-2xl px-5 py-4 transition-all duration-300',
            isUser
              ? 'bg-gradient-to-br from-accent to-accent-secondary text-accent-foreground rounded-tr-sm'
              : 'glass-card rounded-tl-sm'
          )}
        >
          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
            {/* Thinking state - no content yet */}
            {isStreaming && !message.content && (
              <div className="flex items-center gap-1.5">
                <span className="text-sm text-muted-foreground">Thinking</span>
                <span className="inline-flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms', animationDuration: '0.6s' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '150ms', animationDuration: '0.6s' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms', animationDuration: '0.6s' }} />
                </span>
              </div>
            )}
            {/* Content with optional streaming indicator */}
            {message.content && (
              <>
                {isUser ? (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed m-0">
                    {message.content}
                  </p>
                ) : (
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                )}
                {isStreaming && (
                  <span className="inline-flex items-center gap-1 ml-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" style={{ animationDelay: '300ms' }} />
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        {/* Sources */}
        {hasSources && (
          <div className="mt-3 text-left">
            <button
              onClick={() => setShowSources(!showSources)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg',
                'text-xs text-muted-foreground hover:text-accent',
                'glass-subtle hover:glow-sm transition-all duration-300'
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>{message.sources!.length} source{message.sources!.length > 1 ? 's' : ''}</span>
              {showSources ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>

            {showSources && (
              <div className="mt-2 space-y-2 animate-fade-up">
                {message.sources!.map((source, index) => (
                  <div
                    key={index}
                    className="text-xs p-3 glass-card rounded-xl"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <p className="text-muted-foreground line-clamp-3 leading-relaxed">
                      {typeof source === 'string' ? source : source.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* File preview modal */}
      {hasFile && message.file?.url && (
        <FilePreviewModal
          isOpen={showFilePreview}
          onClose={() => setShowFilePreview(false)}
          fileUrl={message.file.url}
          fileName={message.file.name}
          fileType={message.file.type}
        />
      )}
    </div>
  );
}
