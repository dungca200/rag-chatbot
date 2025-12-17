from django.core.management.base import BaseCommand

from apps.documents.parsers import parse_pdf, parse_docx, parse_xlsx, parse_image


class Command(BaseCommand):
    help = 'Test all document parsers'

    def add_arguments(self, parser):
        parser.add_argument('--pdf', type=str, help='Path to PDF file')
        parser.add_argument('--docx', type=str, help='Path to DOCX file')
        parser.add_argument('--xlsx', type=str, help='Path to XLSX file')
        parser.add_argument('--image', type=str, help='Path to image file for OCR')

    def handle(self, *args, **options):
        self.stdout.write("\n=== Document Parsers Test ===\n")

        parsers = [
            ('PDF', options.get('pdf'), parse_pdf),
            ('DOCX', options.get('docx'), parse_docx),
            ('XLSX', options.get('xlsx'), parse_xlsx),
            ('Image/OCR', options.get('image'), parse_image),
        ]

        for name, file_path, parser_func in parsers:
            self.stdout.write(f"\n--- {name} Parser ---")

            if file_path:
                self.stdout.write(f"File: {file_path}")
                result = parser_func(file_path)

                self.stdout.write(f"Success: {result.get('success')}")

                if result.get('success'):
                    metadata = result.get('metadata', {})
                    self.stdout.write(f"Metadata: {metadata}")
                    content = result.get('content', '')
                    self.stdout.write(f"Content length: {len(content)} chars")
                    self.stdout.write(f"Preview: {content[:200]}...")
                else:
                    self.stdout.write(f"Error: {result.get('error')}")
            else:
                self.stdout.write(f"No file provided (use --{name.lower().split('/')[0]})")

        self.stdout.write(self.style.SUCCESS("\n✓ Parser tests complete"))
        self.stdout.write("\nUsage examples:")
        self.stdout.write("  python manage.py check_parsers --pdf file.pdf")
        self.stdout.write("  python manage.py check_parsers --docx file.docx")
        self.stdout.write("  python manage.py check_parsers --xlsx file.xlsx")
        self.stdout.write("  python manage.py check_parsers --image file.png")
