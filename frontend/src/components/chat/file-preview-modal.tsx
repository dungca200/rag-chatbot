'use client';

import { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Download, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileUrl: string;
  fileName: string;
  fileType: string;
}

export function FilePreviewModal({
  isOpen,
  onClose,
  fileUrl,
  fileName,
  fileType,
}: FilePreviewModalProps) {
  // Close on escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen || typeof window === 'undefined') return null;

  const isImage = fileType.startsWith('image') ||
    ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].some(ext => fileName.toLowerCase().endsWith(ext));

  const isPdf = fileType === 'application/pdf' || fileName.toLowerCase().endsWith('.pdf');

  const modalContent = (
    <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 9999 }}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className={cn(
        'relative w-[90vw] h-[85vh] max-w-5xl',
        'bg-background rounded-2xl overflow-hidden',
        'border border-border shadow-2xl',
        'flex flex-col',
        'animate-fade-scale'
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-background">
          <h3 className="text-sm font-medium text-foreground truncate max-w-md">
            {fileName}
          </h3>
          <div className="flex items-center gap-2">
            {/* Download button */}
            <a
              href={fileUrl}
              download={fileName}
              className={cn(
                'p-2 rounded-lg transition-colors',
                'text-muted-foreground hover:text-foreground',
                'hover:bg-accent-subtle'
              )}
              title="Download"
            >
              <Download className="w-4 h-4" />
            </a>
            {/* Open in new tab */}
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'p-2 rounded-lg transition-colors',
                'text-muted-foreground hover:text-foreground',
                'hover:bg-accent-subtle'
              )}
              title="Open in new tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
            {/* Close button */}
            <button
              onClick={onClose}
              className={cn(
                'p-2 rounded-lg transition-colors',
                'text-muted-foreground hover:text-foreground',
                'hover:bg-accent-subtle'
              )}
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-background-secondary">
          {isPdf ? (
            <iframe
              src={`${fileUrl}#toolbar=0&navpanes=0`}
              className="w-full h-full border-0"
              title={fileName}
            />
          ) : isImage ? (
            <div className="w-full h-full flex items-center justify-center p-4">
              <img
                src={fileUrl}
                alt={fileName}
                className="max-w-full max-h-full object-contain rounded-lg"
              />
            </div>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center p-8">
                <p className="text-muted-foreground mb-4">
                  Preview not available for this file type
                </p>
                <a
                  href={fileUrl}
                  download={fileName}
                  className={cn(
                    'inline-flex items-center gap-2 px-4 py-2 rounded-lg',
                    'bg-accent text-accent-foreground',
                    'hover:opacity-90 transition-opacity'
                  )}
                >
                  <Download className="w-4 h-4" />
                  Download File
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
