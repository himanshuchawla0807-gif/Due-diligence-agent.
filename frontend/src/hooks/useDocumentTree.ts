import { useState, useEffect, useCallback } from 'react';
import type { DocumentTree } from '../types';
import { API_BASE_URL } from '@/config';

export function useDocumentTree(sessionId: string | null, userId?: string | null) {
  const [documentTree, setDocumentTree] = useState<DocumentTree | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDocumentTree = useCallback(async () => {
    console.log('📁 [DOC_TREE] Fetching document tree, sessionId:', sessionId, 'userId:', userId);
    if (!sessionId) {
      console.log('📁 [DOC_TREE] No sessionId, setting documentTree to null');
      setDocumentTree(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // ✅ AUTH: Pass user_id query param so backend can query Firestore
      const url = userId
        ? `${API_BASE_URL}/api/session/${sessionId}/documents?user_id=${userId}`
        : `${API_BASE_URL}/api/session/${sessionId}/documents`;

      const response = await fetch(url);
      console.log('📁 [DOC_TREE] Response status:', response.status);

      if (!response.ok) {
        throw new Error(`Failed to fetch document tree: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📁 [DOC_TREE] Received data:', data);
      console.log('📁 [DOC_TREE] Documents count:', data.documents?.length);

      setDocumentTree({
        session_id: data.session_id,
        documents: data.documents,
        total_files: data.total_files,
        total_size: data.total_size
      });
      console.log('📁 [DOC_TREE] Set documentTree with', data.documents?.length, 'documents');
    } catch (err) {
      console.error('📁 [DOC_TREE] Error fetching document tree:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      setDocumentTree(null);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, userId]);

  useEffect(() => {
    fetchDocumentTree();
  }, [fetchDocumentTree]);

  return {
    documentTree,
    isLoading,
    error,
    refetch: fetchDocumentTree
  };
}
