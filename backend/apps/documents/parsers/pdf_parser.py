import logging
from pathlib import Path
from typing import Dict, Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFParser:
    """Parser for PDF documents using PyPDF."""

    SUPPORTED_EXTENSIONS = ['.pdf']

    def parse(self, file_path: str) -> Dict:
        """
        Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dict with content, metadata, and status
        """
        path = Path(file_path)

        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "content": "",
                "metadata": {}
            }

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Unsupported file type: {path.suffix}",
                "content": "",
                "metadata": {}
            }

        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num}]\n{page_text}")

            content = "\n\n".join(text_parts)

            metadata = {
                "filename": path.name,
                "file_type": "pdf",
                "page_count": len(reader.pages),
                "file_size": path.stat().st_size
            }

            # Extract PDF metadata if available
            if reader.metadata:
                if reader.metadata.title:
                    metadata["title"] = reader.metadata.title
                if reader.metadata.author:
                    metadata["author"] = reader.metadata.author

            logger.info(f"Parsed PDF: {path.name}, {len(reader.pages)} pages")

            return {
                "success": True,
                "content": content,
                "metadata": metadata,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {"filename": path.name}
            }


def parse_pdf(file_path: str) -> Dict:
    """Convenience function for PDF parsing."""
    parser = PDFParser()
    return parser.parse(file_path)
