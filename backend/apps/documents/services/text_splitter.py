import logging
from typing import List, Dict, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentSplitter:
    """Splits documents into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize the document splitter.

        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: Custom separators for splitting (optional)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len
        )

    def split_text(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: The text to split
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of dicts with content and metadata
        """
        if not text or not text.strip():
            return []

        try:
            chunks = self.splitter.split_text(text)

            result = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    **(metadata or {})
                }

                result.append({
                    "content": chunk,
                    "metadata": chunk_metadata
                })

            logger.info(f"Split text into {len(chunks)} chunks")
            return result

        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            return []

    def split_document(
        self,
        content: str,
        document_key: str,
        filename: str,
        file_type: str,
        additional_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Split a document and attach document-specific metadata.

        Args:
            content: Document content
            document_key: Unique key for the document
            filename: Original filename
            file_type: Type of file (pdf, docx, etc.)
            additional_metadata: Extra metadata to include

        Returns:
            List of chunks with full metadata
        """
        base_metadata = {
            "document_key": document_key,
            "filename": filename,
            "file_type": file_type,
            **(additional_metadata or {})
        }

        chunks = self.split_text(content, base_metadata)

        # Add parent_key for each chunk
        for i, chunk in enumerate(chunks):
            chunk["key"] = f"{document_key}_chunk_{i}"
            chunk["parent_key"] = document_key

        return chunks


def split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[Dict] = None
) -> List[Dict]:
    """Convenience function for text splitting."""
    splitter = DocumentSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text, metadata)


def split_document(
    content: str,
    document_key: str,
    filename: str,
    file_type: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict]:
    """Convenience function for document splitting."""
    splitter = DocumentSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_document(content, document_key, filename, file_type)
