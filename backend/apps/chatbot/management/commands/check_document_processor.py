from django.core.management.base import BaseCommand

from apps.chatbot.agents import process_document


class Command(BaseCommand):
    help = 'Test the document processor'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to document file')
        parser.add_argument('--user', type=str, default='test-user', help='User ID')

    def handle(self, *args, **options):
        file_path = options['file']
        user_id = options['user']

        self.stdout.write("\n=== Document Processor Test ===\n")
        self.stdout.write(f"File: {file_path}")
        self.stdout.write(f"User: {user_id}")

        result = process_document(
            file_path=file_path,
            user_id=user_id,
            chunk_size=500,
            chunk_overlap=100
        )

        self.stdout.write(f"\nSuccess: {result.get('success')}")

        if result.get('success'):
            self.stdout.write(f"Document Key: {result.get('document_key')}")
            self.stdout.write(f"Chunks: {len(result.get('chunks', []))}")

            metadata = result.get('metadata', {})
            self.stdout.write(f"Filename: {metadata.get('filename')}")
            self.stdout.write(f"File Type: {metadata.get('file_type')}")

            chunks = result.get('chunks', [])
            if chunks:
                self.stdout.write("\n--- First Chunk ---")
                self.stdout.write(f"Key: {chunks[0].get('key')}")
                self.stdout.write(f"Parent Key: {chunks[0].get('parent_key')}")
                self.stdout.write(f"Content: {chunks[0].get('content', '')[:150]}...")
        else:
            self.stdout.write(f"Error: {result.get('error')}")

        self.stdout.write(self.style.SUCCESS("\n✓ Document processor test complete"))
