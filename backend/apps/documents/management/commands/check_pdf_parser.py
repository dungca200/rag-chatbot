import tempfile
from django.core.management.base import BaseCommand

from apps.documents.parsers import parse_pdf


class Command(BaseCommand):
    help = 'Test the PDF parser'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to PDF file to parse (optional)'
        )

    def handle(self, *args, **options):
        self.stdout.write("\n=== PDF Parser Test ===\n")

        file_path = options.get('file')

        if file_path:
            # Test with provided file
            self.stdout.write(f"Parsing: {file_path}")
            result = parse_pdf(file_path)
        else:
            # Test with non-existent file (error handling)
            self.stdout.write("Testing error handling (no file provided)...")
            result = parse_pdf("/nonexistent/test.pdf")

        self.stdout.write(f"\nSuccess: {result.get('success')}")

        if result.get('success'):
            metadata = result.get('metadata', {})
            self.stdout.write(f"Filename: {metadata.get('filename')}")
            self.stdout.write(f"Pages: {metadata.get('page_count')}")
            self.stdout.write(f"Content length: {len(result.get('content', ''))} chars")
            self.stdout.write(f"\nFirst 500 chars:\n{result.get('content', '')[:500]}...")
        else:
            self.stdout.write(f"Error: {result.get('error')}")

        self.stdout.write(self.style.SUCCESS("\n✓ PDF parser test complete"))
        self.stdout.write("\nUsage: python manage.py check_pdf_parser --file /path/to/file.pdf")
