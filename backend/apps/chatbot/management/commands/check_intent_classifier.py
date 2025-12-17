from django.core.management.base import BaseCommand

from apps.chatbot.tools import classify_intent


class Command(BaseCommand):
    help = 'Test the intent classifier with sample queries'

    def handle(self, *args, **options):
        test_queries = [
            ("Hello, how are you?", None),
            ("What is the capital of France?", None),
            ("Tell me about the uploaded document", "doc_123"),
            ("I need help with something", None),
            ("Search my documents for sales data", None),
            ("Hi", None),
            ("Upload a file", None),
        ]

        self.stdout.write("\n=== Intent Classifier Test ===\n")

        for query, doc_key in test_queries:
            self.stdout.write(f"\nQuery: '{query}'")
            if doc_key:
                self.stdout.write(f"Document Key: {doc_key}")

            result = classify_intent(query, doc_key)

            self.stdout.write(f"  Agent: {result['agent']}")
            self.stdout.write(f"  Rationale: {result['rationale']}")
            self.stdout.write("-" * 40)

        self.stdout.write(self.style.SUCCESS("\n✓ Intent classifier test complete"))
