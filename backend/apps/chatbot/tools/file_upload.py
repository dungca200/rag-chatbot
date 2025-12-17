import logging
from typing import Dict, Optional

from apps.chatbot.agents.document_agent import process_document
from apps.chatbot.tools.vector_embedding import embed_and_store_chunks

logger = logging.getLogger(__name__)


def process_and_vectorize_file(
    file_path: str,
    user_id: str,
    thread_id: Optional[str] = None,
    persist_embeddings: bool = True,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict:
    """
    Process a file and optionally vectorize it.

    Args:
        file_path: Path to the file
        user_id: Owner of the file
        thread_id: Thread ID for session-scoped documents
        persist_embeddings: If True, store permanently; if False, session-only
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        Dict with document_key, chunk_count, and status
    """
    # Step 1: Process document (parse + split)
    logger.info(f"Processing file: {file_path}")

    process_result = process_document(
        file_path=file_path,
        user_id=user_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    if not process_result.get("success"):
        return {
            "success": False,
            "error": process_result.get("error", "Processing failed"),
            "document_key": None,
            "chunk_count": 0,
            "vectorized": False
        }

    document_key = process_result.get("document_key")
    chunks = process_result.get("chunks", [])
    metadata = process_result.get("metadata", {})

    # Step 2: Vectorize (embed and store)
    logger.info(f"Vectorizing {len(chunks)} chunks...")

    embed_result = embed_and_store_chunks(
        chunks=chunks,
        user_id=user_id,
        thread_id=thread_id,
        is_persistent=persist_embeddings
    )

    if not embed_result.get("success"):
        return {
            "success": False,
            "error": embed_result.get("error", "Vectorization failed"),
            "document_key": document_key,
            "chunk_count": len(chunks),
            "vectorized": False
        }

    logger.info(f"File processed and vectorized: {document_key}")

    return {
        "success": True,
        "document_key": document_key,
        "chunk_count": len(chunks),
        "stored_count": embed_result.get("stored_count", 0),
        "vectorized": True,
        "persistent": persist_embeddings,
        "metadata": metadata
    }


def process_file_only(
    file_path: str,
    user_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict:
    """
    Process a file without vectorizing (parse + split only).

    Args:
        file_path: Path to the file
        user_id: Owner of the file
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        Dict with document_key, chunks, and metadata
    """
    return process_document(
        file_path=file_path,
        user_id=user_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
