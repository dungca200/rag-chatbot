from django.core.management.base import BaseCommand

from apps.chatbot.graph.workflow import process_user_query


class Command(BaseCommand):
    help = 'Test the LangGraph workflow'

    def handle(self, *args, **options):
        test_cases = [
            {"query": "Hello!", "desc": "Greeting -> conversation"},
            {"query": "What is in my documents?", "desc": "Knowledge question -> rag"},
        ]

        self.stdout.write("\n=== LangGraph Workflow Test ===\n")

        for test in test_cases:
            self.stdout.write(f"\n{test['desc']}")
            self.stdout.write(f"Query: '{test['query']}'")

            result = process_user_query(
                query=test["query"],
                user_id="test-user-uuid-123",
                thread_id=None,  # Auto-generate
                document_key=None,
                persist_embeddings=False
            )

            self.stdout.write(f"  Success: {result.get('success')}")
            self.stdout.write(f"  Agent: {result.get('agent')}")
            self.stdout.write(f"  Thread ID: {result.get('thread_id', '')[:8]}...")
            self.stdout.write(f"  Response: {result.get('response', '')[:100]}...")
            self.stdout.write(f"  Sources: {result.get('sources', [])}")
            self.stdout.write("-" * 50)

        self.stdout.write(self.style.SUCCESS("\n✓ Workflow test complete"))
