'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Send, Paperclip, Loader2, X, FileText, Image, FileSpreadsheet } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { VectorizationToggle } from './vectorization-toggle';

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        'border-t border-gray-200 dark:border-gray-800 p-4 transition-colors',
        isDragging && 'bg-blue-50 dark:bg-blue-900/20'
      )}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="max-w-3xl mx-auto">
        {/* File preview with vectorization toggle */}
        {file && (
          <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <FileIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatFileSize(file.size)}
                </p>
              </div>
              <button
                onClick={() => setFile(null)}
                disabled={isLoading}
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
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
          <div className="mb-3 p-4 border-2 border-dashed border-blue-500 rounded-lg text-center">
            <p className="text-sm text-blue-600 dark:text-blue-400">
              Drop file here to attach
            </p>
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* File upload button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || disabled}
            className={cn(
              'p-2.5 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors',
              (isLoading || disabled) && 'opacity-50 cursor-not-allowed'
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
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Type your message... (Shift+Enter for new line)"
              disabled={isLoading || disabled}
              rows={1}
              className={cn(
                'w-full resize-none rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-2.5 pr-12',
                'bg-white dark:bg-gray-900',
                'focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'text-sm'
              )}
            />
          </div>

          {/* Send button */}
          <Button
            onClick={handleSubmit}
            disabled={(!message.trim() && !file) || isLoading || disabled}
            className="h-10 w-10 p-0"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </div>

        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
          Drag & drop files or click the paperclip to attach
        </p>
      </div>
    </div>
  );
}
