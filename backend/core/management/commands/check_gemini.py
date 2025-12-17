"""Management command to verify Gemini API connection."""
from django.core.management.base import BaseCommand

from core.clients.gemini_client import embed_query, generate_response, EMBEDDING_DIMENSION


class Command(BaseCommand):
    help = "Verify Gemini API connection and embeddings"

    def handle(self, *args, **options):
        self.stdout.write("Checking Gemini API connection...\n")

        # Test embeddings
        self.stdout.write("Testing embed_query...")
        try:
            test_text = "Hello, this is a test query for embeddings."
            embedding = embed_query(test_text)

            if len(embedding) == EMBEDDING_DIMENSION:
                self.stdout.write(self.style.SUCCESS(
                    f"  embed_query works! Returned {len(embedding)}-dim vector"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  Unexpected dimension: {len(embedding)} (expected {EMBEDDING_DIMENSION})"
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  embed_query failed: {str(e)}"))
            return

        # Test chat model
        self.stdout.write("\nTesting generate_response...")
        try:
            response = generate_response("Say 'Hello' in one word.", temperature=0)
            self.stdout.write(self.style.SUCCESS(f"  generate_response works!"))
            self.stdout.write(f"  Response: {response[:100]}...")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  generate_response failed: {str(e)}"))
            return

        self.stdout.write(self.style.SUCCESS("\nGemini API connection successful!"))
