from django.core.management.base import BaseCommand

from apps.chatbot.agents import orchestrator_node, route_to_agent


class Command(BaseCommand):
    help = 'Test the orchestrator agent routing'

    def handle(self, *args, **options):
        test_cases = [
            {"query": "Hello!", "user_id": "test", "thread_id": "t1"},
            {"query": "What documents do I have?", "user_id": "test", "thread_id": "t2", "document_key": "doc_123"},
            {"query": "Search for sales data", "user_id": "test", "thread_id": "t3"},
        ]

        self.stdout.write("\n=== Orchestrator Agent Test ===\n")

        for state in test_cases:
            # Ensure required fields
            state.setdefault("persist_embeddings", False)
            state.setdefault("retrieved_context", [])
            state.setdefault("responses", [])
            state.setdefault("sources", [])
            state.setdefault("logs", [])
            state.setdefault("target_agent", None)
            state.setdefault("document_key", None)

            self.stdout.write(f"\nQuery: '{state['query']}'")
            if state.get("document_key"):
                self.stdout.write(f"Document Key: {state['document_key']}")

            # Run orchestrator
            result = orchestrator_node(state)

            # Update state with result
            state.update(result)

            # Get next node
            next_node = route_to_agent(state)

            self.stdout.write(f"  Target Agent: {result['target_agent']}")
            self.stdout.write(f"  Next Node: {next_node}")
            self.stdout.write(f"  Logs: {len(state['logs'])} entries")
            self.stdout.write("-" * 40)

        self.stdout.write(self.style.SUCCESS("\n✓ Orchestrator test complete"))
