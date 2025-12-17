'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Paperclip, Loader2, X, FileText, Image, FileSpreadsheet, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { VectorizationToggle } from './vectorization-toggle';
import { useChatStore } from '@/lib/stores/chat-store';

interface ChatInputProps {
  onSend: (message: string, file?: File, persistEmbeddings?: boolean) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

function getFileIcon(fileName: string) {
  const ext = fileName.toLowerCase().split('.').pop();
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'].includes(ext || '')) {
    return Image;
  }
  if (['xlsx', 'xlsm'].includes(ext || '')) {
    return FileSpreadsheet;
  }
  return FileText;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [persistEmbeddings, setPersistEmbeddings] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { suggestedPrompt, focusInput, setSuggestedPrompt, setFocusInput } = useChatStore();

  // Handle suggested prompt from store
  useEffect(() => {
    if (suggestedPrompt) {
      setMessage(suggestedPrompt);
      setSuggestedPrompt(null);
      // Focus and move cursor to end
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.selectionStart = textareaRef.current.value.length;
          textareaRef.current.selectionEnd = textareaRef.current.value.length;
        }
      }, 0);
    }
  }, [suggestedPrompt, setSuggestedPrompt]);

  // Handle focus request from store
  useEffect(() => {
    if (focusInput) {
      textareaRef.current?.focus();
      setFocusInput(false);
    }
  }, [focusInput, setFocusInput]);

  const handleSubmit = () => {
    if ((!message.trim() && !file) || isLoading || disabled) return;
    onSend(message.trim(), file || undefined, persistEmbeddings);
    setMessage('');
    setFile(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || isLoading) return;
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled && !isLoading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const FileIcon = file ? getFileIcon(file.name) : FileText;

  return (
    <div
      className={cn(
        'flex-shrink-0 p-6 transition-all duration-300',
        isDragging && 'bg-accent/5'
      )}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="max-w-4xl mx-auto">
        {/* File preview with vectorization toggle */}
        {file && (
          <div className="mb-4 p-4 glass-card rounded-2xl animate-fade-up">
            <div className="flex items-center gap-4 mb-3">
              <div className="p-3 rounded-xl bg-gradient-to-br from-accent to-accent-secondary">
                <FileIcon className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </p>
              </div>
              <button
                onClick={() => setFile(null)}
                disabled={isLoading}
                className="p-2 rounded-xl glass hover:bg-error/10 hover:text-error transition-all duration-300"
                aria-label="Remove file"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <VectorizationToggle
              enabled={persistEmbeddings}
              onChange={setPersistEmbeddings}
              disabled={isLoading}
            />
          </div>
        )}

        {/* Drag hint */}
        {isDragging && (
          <div className="mb-4 p-8 border-2 border-dashed border-accent rounded-2xl text-center animate-fade-up glow">
            <Sparkles className="h-8 w-8 text-accent mx-auto mb-2" />
            <p className="text-sm text-accent font-medium">
              Drop file here to attach
            </p>
          </div>
        )}

        {/* Main input area */}
        <div
          className={cn(
            'relative flex items-end gap-3 p-3 rounded-2xl transition-all duration-300',
            'glass',
            isFocused && 'glow-border',
            (isLoading || disabled) && 'opacity-70'
          )}
        >
          {/* Animated border gradient when focused */}
          {isFocused && (
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-accent via-accent-secondary to-accent opacity-20 blur-sm -z-10 animate-pulse-glow" />
          )}

          {/* File upload button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || disabled}
            className={cn(
              'p-3 rounded-xl glass hover:glow-sm transition-all duration-300',
              'text-muted-foreground hover:text-accent',
              (isLoading || disabled) && 'cursor-not-allowed opacity-50'
            )}
            aria-label="Attach file"
          >
            <Paperclip className="h-5 w-5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.docx,.xlsx,.xlsm,.txt,.png,.jpg,.jpeg,.tiff,.bmp,.gif"
            className="hidden"
          />

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ask me anything..."
            disabled={isLoading || disabled}
            rows={1}
            className={cn(
              'flex-1 resize-none bg-transparent py-3 px-2',
              'text-foreground placeholder-muted-foreground',
              'focus:outline-none',
              'disabled:cursor-not-allowed',
              'text-sm leading-relaxed'
            )}
          />

          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={(!message.trim() && !file) || isLoading || disabled}
            className={cn(
              'relative p-3 rounded-xl transition-all duration-300 overflow-hidden',
              'bg-gradient-to-r from-accent to-accent-secondary text-accent-foreground',
              'hover:shadow-lg hover:shadow-accent/25',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none',
              !isLoading && 'hover:scale-105 active:scale-95'
            )}
          >
            {/* Shimmer effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full hover:translate-x-full transition-transform duration-700" />
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin relative z-10" />
            ) : (
              <Send className="h-5 w-5 relative z-10" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
