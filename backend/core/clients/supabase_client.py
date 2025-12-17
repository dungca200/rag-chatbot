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
    match_threshold: float = 0.1,  # Lowered default threshold
    match_count: int = 10
) -> List[Dict]:
    """Perform semantic search on documents."""
    try:
        client = get_supabase_client()

        # Use match_documents_by_user which doesn't filter by thread_id
        # This ensures all user documents are searched
        logger.info(f"Searching documents for user_id={user_id}")

        result = client.rpc(
            'match_documents_by_user',
            {
                'query_embedding': query_embedding,
                'filter_user_id': user_id,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
        ).execute()

        if result.data:
            logger.info(f"match_documents_by_user returned {len(result.data)} results")
            return result.data

        # Fallback to original match_documents with thread_id
        logger.info("Trying match_documents with thread_id filter")
        fallback_result = client.rpc(
            'match_documents',
            {
                'query_embedding': query_embedding,
                'filter_user_id': user_id,
                'filter_thread_id': thread_id,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
        ).execute()

        if fallback_result.data:
            logger.info(f"match_documents returned {len(fallback_result.data)} results")
            return fallback_result.data

        logger.info("No documents found in either search method")
        return []
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


def delete_documents_by_key(document_key: str, user_id: str) -> Dict:
    """
    Delete all document chunks associated with a document key.

    Args:
        document_key: The parent document key
        user_id: Owner's user ID (for security)

    Returns:
        Dict with success status and deleted count
    """
    try:
        client = get_supabase_client()

        # Delete all chunks where parent_key matches the document_key
        result = client.table('documents').delete().match({
            'parent_key': document_key,
            'user_id': user_id
        }).execute()

        deleted_count = len(result.data) if result.data else 0
        logger.info(f"Deleted {deleted_count} chunks for document: {document_key}")

        return {
            "success": True,
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting documents for {document_key}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "deleted_count": 0
        }


# ============= File Storage Functions =============

STORAGE_BUCKET = "chat-files"


def upload_file_to_storage(
    file_path: str,
    file_name: str,
    user_id: str,
    content_type: str = "application/octet-stream"
) -> Optional[Dict]:
    """
    Upload a file to Supabase Storage.

    Args:
        file_path: Local path to the file
        file_name: Original filename
        user_id: Owner's user ID
        content_type: MIME type of the file

    Returns:
        Dict with file_url and file_path, or None on error
    """
    try:
        client = get_supabase_client()

        # Create unique path: user_id/timestamp_filename
        import time
        timestamp = int(time.time())
        storage_path = f"{user_id}/{timestamp}_{file_name}"

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        logger.info(f"Uploading to bucket '{STORAGE_BUCKET}', path: {storage_path}")

        # Upload to storage
        result = client.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": content_type}
        )

        logger.info(f"Upload result: {result}")

        # Get public URL
        file_url = client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        logger.info(f"Uploaded file to storage: {storage_path}, URL: {file_url}")

        return {
            "file_url": file_url,
            "storage_path": storage_path,
            "file_name": file_name
        }

    except Exception as e:
        logger.error(f"Error uploading file to storage: {str(e)}", exc_info=True)
        return None


def delete_file_from_storage(storage_path: str) -> bool:
    """Delete a file from Supabase Storage."""
    try:
        client = get_supabase_client()
        client.storage.from_(STORAGE_BUCKET).remove([storage_path])
        logger.info(f"Deleted file from storage: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file from storage: {str(e)}")
        return False


# Global client instance
supabase_client = get_supabase_client()
