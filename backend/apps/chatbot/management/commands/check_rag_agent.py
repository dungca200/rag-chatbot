from django.core.management.base import BaseCommand

from apps.chatbot.agents import rag_agent_node


class Command(BaseCommand):
    help = 'Test the RAG agent'

    def handle(self, *args, **options):
        # Test state - will need actual documents in Supabase to fully test
        test_state = {
            "query": "What is machine learning?",
            "user_id": "test-user-123",
            "thread_id": "test-thread-123",
            "document_key": None,
            "persist_embeddings": False,
            "target_agent": "rag",
            "retrieved_context": [],
            "responses": [],
            "sources": [],
            "logs": []
        }

        self.stdout.write("\n=== RAG Agent Test ===\n")
        self.stdout.write(f"Query: '{test_state['query']}'")
        self.stdout.write(f"User ID: {test_state['user_id']}")

        result = rag_agent_node(test_state)

        self.stdout.write(f"\nDocuments Retrieved: {len(result.get('retrieved_context', []))}")
        self.stdout.write(f"Sources: {result.get('sources', [])}")

        responses = result.get("responses", [])
        if responses:
            self.stdout.write(f"\nResponse:")
            self.stdout.write(f"  Agent: {responses[-1].get('agent')}")
            self.stdout.write(f"  Content: {responses[-1].get('content', '')[:200]}...")

        self.stdout.write(f"\nLogs: {len(result.get('logs', []))} entries")
        self.stdout.write(self.style.SUCCESS("\n✓ RAG agent test complete"))
