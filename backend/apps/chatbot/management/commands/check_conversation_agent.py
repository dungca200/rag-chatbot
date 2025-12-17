from django.core.management.base import BaseCommand

from apps.chatbot.agents import conversation_agent_node


class Command(BaseCommand):
    help = 'Test the conversation agent'

    def handle(self, *args, **options):
        test_queries = [
            "Hello!",
            "How are you today?",
            "What can you help me with?",
        ]

        self.stdout.write("\n=== Conversation Agent Test ===\n")

        for query in test_queries:
            test_state = {
                "query": query,
                "user_id": "test-user",
                "thread_id": "test-thread",
                "document_key": None,
                "persist_embeddings": False,
                "target_agent": "conversation",
                "retrieved_context": [],
                "responses": [],
                "sources": [],
                "logs": []
            }

            self.stdout.write(f"\nQuery: '{query}'")

            result = conversation_agent_node(test_state)

            responses = result.get("responses", [])
            if responses:
                self.stdout.write(f"Response: {responses[-1].get('content', '')[:150]}...")

            self.stdout.write("-" * 40)

        self.stdout.write(self.style.SUCCESS("\n✓ Conversation agent test complete"))
