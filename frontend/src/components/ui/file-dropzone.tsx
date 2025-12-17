'use client';

import { useCallback, useState } from 'react';
import { Upload, X, FileText, Image, FileSpreadsheet } from 'lucide-react';
import { cn } from '@/lib/utils';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.xlsm', '.txt', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

interface FileDropzoneProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  disabled?: boolean;
  className?: string;
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

export function FileDropzone({ onFileSelect, selectedFile, disabled, className }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + file.name.toLowerCase().split('.').pop();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `File type not allowed. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size: ${formatFileSize(MAX_FILE_SIZE)}`;
    }
    return null;
  }, []);

  const handleFile = useCallback((file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    onFileSelect(file);
  }, [validateFile, onFileSelect]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [disabled, handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
    e.target.value = '';
  }, [handleFile]);

  const handleRemove = useCallback(() => {
    setError(null);
    onFileSelect(null);
  }, [onFileSelect]);

  if (selectedFile) {
    const FileIcon = getFileIcon(selectedFile.name);
    return (
      <div className={cn('p-3 bg-gray-50 dark:bg-gray-800 rounded-lg', className)}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <FileIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{selectedFile.name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {formatFileSize(selectedFile.size)}
            </p>
          </div>
          <button
            onClick={handleRemove}
            disabled={disabled}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          'relative border-2 border-dashed rounded-lg p-6 transition-colors',
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input
          type="file"
          onChange={handleInputChange}
          accept={ALLOWED_EXTENSIONS.join(',')}
          disabled={disabled}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        <div className="text-center">
          <Upload className="mx-auto h-8 w-8 text-gray-400" />
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium text-blue-600 dark:text-blue-400">Click to upload</span>
            {' '}or drag and drop
          </p>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
            PDF, DOCX, XLSX, TXT, or images up to 10MB
          </p>
        </div>
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
