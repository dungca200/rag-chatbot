from django.core.management.base import BaseCommand

from apps.chatbot.tools import process_and_vectorize_file


class Command(BaseCommand):
    help = 'Test file upload and vectorization'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to file')
        parser.add_argument('--user', type=str, default='test-user-uuid', help='User ID')
        parser.add_argument('--persist', action='store_true', help='Persist embeddings')

    def handle(self, *args, **options):
        file_path = options['file']
        user_id = options['user']
        persist = options.get('persist', False)

        self.stdout.write("\n=== File Upload & Vectorization Test ===\n")
        self.stdout.write(f"File: {file_path}")
        self.stdout.write(f"User: {user_id}")
        self.stdout.write(f"Persist: {persist}")

        result = process_and_vectorize_file(
            file_path=file_path,
            user_id=user_id,
            persist_embeddings=persist
        )

        self.stdout.write(f"\nSuccess: {result.get('success')}")

        if result.get('success'):
            self.stdout.write(f"Document Key: {result.get('document_key')}")
            self.stdout.write(f"Chunks: {result.get('chunk_count')}")
            self.stdout.write(f"Stored: {result.get('stored_count')}")
            self.stdout.write(f"Vectorized: {result.get('vectorized')}")
            self.stdout.write(f"Persistent: {result.get('persistent')}")
        else:
            self.stdout.write(f"Error: {result.get('error')}")

        self.stdout.write(self.style.SUCCESS("\n✓ File upload test complete"))
