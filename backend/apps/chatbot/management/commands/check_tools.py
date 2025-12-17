from django.core.management.base import BaseCommand

from apps.chatbot.tools import (
    execute_read_query,
    quick_validate
)


class Command(BaseCommand):
    help = 'Test Phase 6 tools'

    def handle(self, *args, **options):
        self.stdout.write("\n=== Phase 6 Tools Test ===\n")

        # Test DB Query tool (safe query check)
        self.stdout.write("--- DB Query Tool ---")

        # Test safe query
        result = execute_read_query("SELECT 1 as test")
        self.stdout.write(f"Safe SELECT query: {result.get('success')}")
        if result.get('success'):
            self.stdout.write(f"  Result: {result.get('results')}")

        # Test unsafe query rejection
        result = execute_read_query("DELETE FROM users")
        self.stdout.write(f"Unsafe DELETE blocked: {not result.get('success')}")
        self.stdout.write(f"  Error: {result.get('error', 'N/A')}")

        # Test Response Validator (quick validate)
        self.stdout.write("\n--- Response Validator Tool ---")

        result = quick_validate(
            response="This is a test response",
            sources=["doc_1", "doc_2"]
        )
        self.stdout.write(f"Quick validate with sources: {result}")

        result = quick_validate(
            response="This is a test response",
            sources=[]
        )
        self.stdout.write(f"Quick validate without sources: {result}")

        self.stdout.write(self.style.SUCCESS("\n✓ Tools test complete"))
        self.stdout.write("\nNote: Vector Embedding & Web Search require API calls")
        self.stdout.write("Test with: python manage.py check_file_upload --file <path>")
