'use client';

import { useEffect, useState } from 'react';
import { FileText, Trash2, FileSpreadsheet, Image, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { Document } from '@/types';

function getFileIcon(fileType: string) {
  if (fileType === 'image') return Image;
  if (fileType === 'xlsx') return FileSpreadsheet;
  return FileText;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await apiClient.get<{ success: boolean; documents: Document[] }>(
        '/api/documents/'
      );
      if (response.success) {
        setDocuments(response.documents);
      }
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await apiClient.delete(`/api/documents/${id}/delete/`);
      setDocuments(documents.filter((d) => d.id !== id));
      toast.success('Document deleted');
    } catch {
      toast.error('Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Documents</h1>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-xl">
          <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-lg font-semibold mb-2 text-foreground">No documents yet</h2>
          <p className="text-muted-foreground">
            Upload documents in the chat to see them here.
          </p>
        </div>
      ) : (
        <div className="glass-card rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr className="border-b border-border">
                <th className="text-left text-sm font-medium text-foreground-secondary px-4 py-3">
                  Name
                </th>
                <th className="text-left text-sm font-medium text-foreground-secondary px-4 py-3">
                  Type
                </th>
                <th className="text-left text-sm font-medium text-foreground-secondary px-4 py-3">
                  Size
                </th>
                <th className="text-left text-sm font-medium text-foreground-secondary px-4 py-3">
                  Chunks
                </th>
                <th className="text-left text-sm font-medium text-foreground-secondary px-4 py-3">
                  Status
                </th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const FileIcon = getFileIcon(doc.file_type);
                return (
                  <tr
                    key={doc.id}
                    className="border-b border-border last:border-0 hover:bg-card-hover transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-background-secondary rounded-lg">
                          <FileIcon className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <span className="text-sm font-medium text-foreground truncate max-w-[200px]">
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-muted-foreground uppercase">
                        {doc.file_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-muted-foreground">
                        {doc.file_size_display}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-muted-foreground">
                        {doc.chunk_count}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium',
                          doc.is_vectorized
                            ? 'bg-emerald-500 text-white'
                            : 'bg-amber-500 text-white'
                        )}
                      >
                        {doc.is_vectorized ? 'Indexed' : 'Pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        disabled={deletingId === doc.id}
                        className="p-2 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                        aria-label="Delete document"
                      >
                        {deletingId === doc.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
