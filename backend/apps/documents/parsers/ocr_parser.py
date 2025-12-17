import logging
from pathlib import Path
from typing import Dict

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


class OCRParser:
    """Parser for images using Tesseract OCR."""

    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']

    def __init__(self, tesseract_cmd: str = None):
        """
        Initialize OCR parser.

        Args:
            tesseract_cmd: Path to tesseract executable (optional)
        """
        if tesseract_cmd and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def parse(self, file_path: str, lang: str = 'eng') -> Dict:
        """
        Extract text from an image using OCR.

        Args:
            file_path: Path to the image file
            lang: Tesseract language code (default: 'eng')

        Returns:
            Dict with content, metadata, and status
        """
        if not TESSERACT_AVAILABLE:
            return {
                "success": False,
                "error": "Tesseract/PIL not installed. Install with: pip install pytesseract Pillow",
                "content": "",
                "metadata": {}
            }

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
            image = Image.open(file_path)

            # Extract text using Tesseract
            content = pytesseract.image_to_string(image, lang=lang)

            metadata = {
                "filename": path.name,
                "file_type": "image",
                "image_format": image.format,
                "image_size": image.size,
                "image_mode": image.mode,
                "file_size": path.stat().st_size,
                "ocr_language": lang
            }

            logger.info(f"OCR parsed: {path.name}, extracted {len(content)} chars")

            return {
                "success": True,
                "content": content.strip(),
                "metadata": metadata,
                "error": None
            }

        except pytesseract.TesseractNotFoundError:
            error_msg = "Tesseract not found. Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "content": "",
                "metadata": {"filename": path.name}
            }
        except Exception as e:
            logger.error(f"Error in OCR parsing {file_path}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {"filename": path.name}
            }


def parse_image(file_path: str, lang: str = 'eng') -> Dict:
    """Convenience function for OCR parsing."""
    parser = OCRParser()
    return parser.parse(file_path, lang)
