import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from apps.chatbot.graph.state import AgentState
from apps.documents.parsers import parse_pdf, parse_docx, parse_xlsx, parse_image
from apps.documents.services import split_document

logger = logging.getLogger(__name__)


# File type to parser mapping
PARSER_MAP = {
    '.pdf': parse_pdf,
    '.docx': parse_docx,
    '.xlsx': parse_xlsx,
    '.xlsm': parse_xlsx,
    '.png': parse_image,
    '.jpg': parse_image,
    '.jpeg': parse_image,
    '.tiff': parse_image,
    '.bmp': parse_image,
    '.gif': parse_image,
}


def get_parser_for_file(file_path: str):
    """Get the appropriate parser for a file based on extension."""
    ext = Path(file_path).suffix.lower()
    return PARSER_MAP.get(ext)


def process_document(
    file_path: str,
    user_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict:
    """
    Process a document: parse and split into chunks.

    Args:
        file_path: Path to the document
        user_id: Owner of the document
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks

    Returns:
        Dict with chunks, metadata, and status
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "chunks": [],
            "metadata": {}
        }

    # Get parser
    parser = get_parser_for_file(file_path)
    if not parser:
        return {
            "success": False,
            "error": f"Unsupported file type: {path.suffix}",
            "chunks": [],
            "metadata": {"filename": path.name}
        }

    # Parse document
    parse_result = parser(file_path)

    if not parse_result.get("success"):
        return {
            "success": False,
            "error": parse_result.get("error", "Parse failed"),
            "chunks": [],
            "metadata": parse_result.get("metadata", {})
        }

    # Generate document key
    document_key = f"doc_{user_id}_{uuid.uuid4().hex[:8]}"

    # Split into chunks
    chunks = split_document(
        content=parse_result["content"],
        document_key=document_key,
        filename=path.name,
        file_type=path.suffix.lstrip('.'),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    metadata = {
        **parse_result.get("metadata", {}),
        "document_key": document_key,
        "chunk_count": len(chunks),
        "user_id": user_id
    }

    logger.info(f"Processed document: {path.name}, {len(chunks)} chunks")

    return {
        "success": True,
        "document_key": document_key,
        "chunks": chunks,
        "metadata": metadata,
        "error": None
    }


def document_agent_node(state: AgentState) -> Dict:
    """
    LangGraph node for document processing.

    Note: This node handles document processing requests.
    Actual file upload handling is done via the API endpoint.

    Returns:
        Dict with responses and logs
    """
    query = state.get("query", "")
    document_key = state.get("document_key")

    logger.info(f"Document Agent processing: {query[:50]}...")

    # Generate response based on whether document is provided
    if document_key:
        content = f"Document '{document_key}' is ready. You can now ask questions about it."
    else:
        content = "To process a document, please upload a file using the upload feature. I support PDF, Word documents (DOCX), Excel spreadsheets (XLSX), and images with text."

    response_entry = {
        "agent": "document",
        "content": content,
        "sources": []
    }

    log_entry = {
        "node": "document_agent",
        "action": "process_request",
        "document_key": document_key
    }

    existing_responses = state.get("responses", [])
    existing_logs = state.get("logs", [])

    return {
        "responses": existing_responses + [response_entry],
        "sources": [],
        "logs": existing_logs + [log_entry]
    }
