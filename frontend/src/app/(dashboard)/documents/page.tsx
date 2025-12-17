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
        <div className="text-center py-12 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <h2 className="text-lg font-semibold mb-2">No documents yet</h2>
          <p className="text-gray-500 dark:text-gray-400">
            Upload documents in the chat to see them here.
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-800">
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Name
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Type
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Size
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
                  Chunks
                </th>
                <th className="text-left text-sm font-medium text-gray-500 dark:text-gray-400 px-4 py-3">
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
                    className="border-b border-gray-100 dark:border-gray-800 last:border-0"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                          <FileIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                        </div>
                        <span className="text-sm font-medium truncate max-w-[200px]">
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600 dark:text-gray-400 uppercase">
                        {doc.file_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {doc.file_size_display}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {doc.chunk_count}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                          doc.is_vectorized
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
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
