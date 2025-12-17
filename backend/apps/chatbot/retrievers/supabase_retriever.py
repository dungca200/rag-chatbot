import logging
from typing import List, Dict, Optional

from core.clients.supabase_client import get_supabase_client, match_documents
from core.clients.gemini_client import embed_query

logger = logging.getLogger(__name__)


class SupabaseRetriever:
    """Retriever class for semantic search on documents stored in Supabase."""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.user_id: Optional[str] = None
        self.thread_id: Optional[str] = None

    def set_user_id(self, user_id: str):
        """Set the user ID for filtering documents."""
        self.user_id = user_id

    def set_thread_id(self, thread_id: str):
        """Set the thread ID for session-specific filtering."""
        self.thread_id = thread_id

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        match_threshold: float = 0.1  # Lowered from 0.15 for better recall
    ) -> List[Dict]:
        """
        Perform semantic search and return relevant documents.

        Args:
            query: The search query
            top_k: Number of documents to return
            match_threshold: Minimum similarity threshold

        Returns:
            List of documents with content, similarity score, and metadata
        """
        if not self.user_id:
            logger.warning("No user_id set for retriever")
            return []

        try:
            # Generate embedding for query
            logger.info(f"Generating embedding for query: {query[:50]}...")
            query_embedding = embed_query(query)

            # Perform semantic search - pass None for thread_id to search all user docs
            logger.info(f"Searching documents for user {self.user_id}, thread_id={self.thread_id}")
            results = match_documents(
                query_embedding=query_embedding,
                user_id=self.user_id,
                thread_id=None,  # Always search ALL user documents, not just thread-specific
                match_threshold=match_threshold,
                match_count=top_k
            )

            if not results:
                logger.info(f"No matching documents found for user {self.user_id}")
                return []

            # Format results
            documents = []
            for doc in results:
                documents.append({
                    'id': doc.get('id'),
                    'key': doc.get('key'),
                    'content': doc.get('content'),
                    'similarity': doc.get('similarity'),
                    'metadata': doc.get('metadata', {})
                })
                logger.info(f"Found doc: {doc.get('key')} with similarity {doc.get('similarity')}")

            logger.info(f"Retrieved {len(documents)} documents for query")
            return documents

        except Exception as e:
            logger.error(f"Error in retrieve: {str(e)}")
            return []

    def get_document_by_key(self, document_key: str) -> Optional[Dict]:
        """Fetch a specific document by its key."""
        try:
            result = self.supabase.rpc(
                'get_document_by_parent_key',
                {'search_parent_key': document_key}
            ).execute()

            if result.data and len(result.data) > 0:
                doc = result.data[0]
                return {
                    'key': doc.get('key'),
                    'content': doc.get('content'),
                    'metadata': doc.get('metadata', {}),
                    'similarity': 1.0  # Direct match
                }

            logger.warning(f"No document found with key: {document_key}")
            return None

        except Exception as e:
            logger.error(f"Error fetching document by key: {str(e)}")
            return None
