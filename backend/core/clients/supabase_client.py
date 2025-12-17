import logging
from functools import lru_cache
from typing import List, Dict, Optional

from supabase import create_client, Client

from settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client() -> Client:
    """Get cached Supabase client instance."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def health_check() -> bool:
    """Verify Supabase connection is working."""
    try:
        client = get_supabase_client()
        client.table('documents').select('id').limit(1).execute()
        logger.info("Supabase health check passed")
        return True
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        return False


def match_documents(
    query_embedding: List[float],
    user_id: str,
    thread_id: Optional[str] = None,
    match_threshold: float = 0.15,
    match_count: int = 10
) -> List[Dict]:
    """Perform semantic search on documents."""
    try:
        client = get_supabase_client()
        result = client.rpc(
            'match_documents',
            {
                'query_embedding': query_embedding,
                'filter_user_id': user_id,
                'filter_thread_id': thread_id,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error in match_documents: {str(e)}")
        return []


def upsert_document(
    user_id: str,
    content: str,
    embedding: List[float],
    key: str,
    thread_id: Optional[str] = None,
    document_id: Optional[str] = None,
    parent_key: Optional[str] = None,
    is_persistent: bool = True,
    metadata: Optional[Dict] = None
) -> bool:
    """Upsert a document with embedding to Supabase."""
    try:
        client = get_supabase_client()
        data = {
            'user_id': user_id,
            'content': content,
            'embedding': embedding,
            'key': key,
            'thread_id': thread_id,
            'document_id': document_id,
            'parent_key': parent_key,
            'is_persistent': is_persistent,
            'metadata': metadata or {}
        }
        client.table('documents').upsert(data).execute()
        logger.info(f"Successfully upserted document: {key}")
        return True
    except Exception as e:
        logger.error(f"Error upserting document {key}: {str(e)}")
        return False


# Global client instance
supabase_client = get_supabase_client()
