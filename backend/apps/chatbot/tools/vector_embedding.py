import logging
from typing import Dict, List, Optional

from core.clients.gemini_client import embed_documents
from core.clients.supabase_client import upsert_document

logger = logging.getLogger(__name__)


def embed_and_store_chunks(
    chunks: List[Dict],
    user_id: str,
    thread_id: Optional[str] = None,
    is_persistent: bool = True
) -> Dict:
    """
    Embed chunks and store them in Supabase.

    Args:
        chunks: List of chunk dicts with 'content', 'key', 'parent_key', 'metadata'
        user_id: Owner of the documents
        thread_id: Thread ID for session-scoped documents
        is_persistent: If True, documents persist; if False, session-only

    Returns:
        Dict with success status and stored document count
    """
    if not chunks:
        return {
            "success": False,
            "error": "No chunks provided",
            "stored_count": 0
        }

    try:
        # Extract texts for batch embedding
        texts = [chunk.get("content", "") for chunk in chunks]

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = embed_documents(texts)

        if len(embeddings) != len(chunks):
            return {
                "success": False,
                "error": "Embedding count mismatch",
                "stored_count": 0
            }

        # Store each chunk with its embedding
        stored_count = 0
        errors = []

        for chunk, embedding in zip(chunks, embeddings):
            try:
                result = upsert_document(
                    key=chunk.get("key"),
                    content=chunk.get("content", ""),
                    embedding=embedding,
                    user_id=user_id,
                    thread_id=thread_id,
                    is_persistent=is_persistent,
                    parent_key=chunk.get("parent_key"),
                    metadata=chunk.get("metadata", {})
                )

                if result:
                    stored_count += 1
                else:
                    errors.append(f"Failed to store chunk: {chunk.get('key')}")

            except Exception as e:
                errors.append(f"Error storing {chunk.get('key')}: {str(e)}")

        logger.info(f"Stored {stored_count}/{len(chunks)} chunks")

        return {
            "success": stored_count > 0,
            "stored_count": stored_count,
            "total_chunks": len(chunks),
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Error in embed_and_store_chunks: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "stored_count": 0
        }


def embed_single_document(
    content: str,
    key: str,
    user_id: str,
    thread_id: Optional[str] = None,
    is_persistent: bool = True,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Embed and store a single document.

    Args:
        content: Document content
        key: Unique document key
        user_id: Owner of the document
        thread_id: Thread ID for session-scoped documents
        is_persistent: If True, persists; if False, session-only
        metadata: Optional metadata

    Returns:
        Dict with success status
    """
    chunk = {
        "content": content,
        "key": key,
        "parent_key": key,
        "metadata": metadata or {}
    }

    return embed_and_store_chunks(
        chunks=[chunk],
        user_id=user_id,
        thread_id=thread_id,
        is_persistent=is_persistent
    )
