#!/usr/bin/env python3
"""
Cross-Thread Memory for LangGraph Agents.

Enables agents to share memories across different conversation threads.
Useful for:
- User preferences that persist across sessions
- Long-term memory about users
- Shared knowledge bases

Uses InMemoryStore with semantic search capabilities.
"""

import os
import uuid
from typing import Optional, Any

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field


# ============================================================================
# Memory Store Setup
# ============================================================================

def create_memory_store(enable_semantic_search: bool = True):
    """
    Create a memory store for cross-thread persistence.

    Args:
        enable_semantic_search: Enable semantic similarity search

    Returns:
        InMemoryStore configured for agent use
    """
    if enable_semantic_search:
        # Use Gemini embeddings for semantic search
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )

        return InMemoryStore(
            index={
                "embed": embeddings,
                "dims": 768  # Gemini embedding dimensions
            }
        )
    else:
        return InMemoryStore()


# ============================================================================
# State Definition
# ============================================================================

class AgentState(MessagesState):
    """Agent state with user context."""
    user_id: str
    context: str


# ============================================================================
# Memory-Enabled Agent
# ============================================================================

class MemoryEnabledAgent:
    """
    Agent with cross-thread memory capabilities.

    Features:
    - Remembers user information across sessions
    - Semantic search for relevant memories
    - User-scoped memory namespaces

    Example:
        agent = MemoryEnabledAgent()

        # Thread 1: User provides info
        agent.chat("user-123", "thread-1", "My favorite color is blue")

        # Thread 2: New conversation, but remembers
        response = agent.chat("user-123", "thread-2", "What's my favorite color?")
        # Response: "Your favorite color is blue"
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.checkpointer = MemorySaver()
        self.store = create_memory_store(enable_semantic_search=True)
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the agent graph with memory access."""

        def call_model(state: AgentState, store: BaseStore) -> dict:
            """Agent node that accesses cross-thread memory."""
            user_id = state["user_id"]
            namespace = ("memories", user_id)

            # Get last user message
            last_message = state["messages"][-1]

            # Search for relevant memories
            memories = store.search(
                namespace,
                query=str(last_message.content),
                limit=5
            )

            # Format memory context
            memory_context = ""
            if memories:
                memory_items = [m.value.get("content", "") for m in memories]
                memory_context = "User memories:\n" + "\n".join(f"- {m}" for m in memory_items)

            # Check if user wants to remember something
            content_lower = last_message.content.lower()
            if any(word in content_lower for word in ["remember", "my name is", "i like", "i prefer", "my favorite"]):
                # Store new memory
                memory_id = str(uuid.uuid4())
                store.put(
                    namespace,
                    memory_id,
                    {"content": last_message.content, "type": "user_info"}
                )

            # Generate response with memory context
            system_msg = f"""You are a helpful assistant with access to user memories.

{memory_context}

Use this information to personalize your responses."""

            response = self.llm.invoke([
                {"role": "system", "content": system_msg},
                *state["messages"]
            ])

            return {"messages": [response]}

        # Build graph
        builder = StateGraph(AgentState)
        builder.add_node("agent", call_model)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

        return builder.compile(
            checkpointer=self.checkpointer,
            store=self.store
        )

    def chat(self, user_id: str, thread_id: str, message: str) -> str:
        """Send a message and get a response."""
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "context": ""
            },
            config
        )

        return result["messages"][-1].content

    def get_memories(self, user_id: str, query: str = None, limit: int = 10) -> list:
        """Get memories for a user."""
        namespace = ("memories", user_id)

        if query:
            memories = self.store.search(namespace, query=query, limit=limit)
        else:
            memories = list(self.store.search(namespace, limit=limit))

        return [m.value for m in memories]

    def add_memory(self, user_id: str, content: str, memory_type: str = "general"):
        """Manually add a memory for a user."""
        namespace = ("memories", user_id)
        memory_id = str(uuid.uuid4())

        self.store.put(
            namespace,
            memory_id,
            {"content": content, "type": memory_type}
        )

    def clear_memories(self, user_id: str):
        """Clear all memories for a user."""
        namespace = ("memories", user_id)

        # Get all memories and delete them
        memories = list(self.store.search(namespace, limit=1000))
        for memory in memories:
            self.store.delete(namespace, memory.key)


# ============================================================================
# Semantic Memory Search
# ============================================================================

def demo_semantic_search():
    """Demonstrate semantic memory search."""

    store = create_memory_store(enable_semantic_search=True)
    user_id = "demo-user"
    namespace = ("memories", user_id)

    # Store various memories
    memories = [
        "I love eating pizza, especially pepperoni",
        "My favorite programming language is Python",
        "I work as a software engineer at a tech startup",
        "I enjoy hiking on weekends",
        "My dog's name is Max and he's a golden retriever"
    ]

    for i, content in enumerate(memories):
        store.put(namespace, f"memory-{i}", {"content": content})

    # Semantic search for food-related memories
    print("Query: 'What food do I like?'")
    results = store.search(namespace, query="What food do I like?", limit=2)
    for r in results:
        print(f"  - {r.value['content']} (score: {r.score:.3f})")

    # Semantic search for work-related
    print("\nQuery: 'What do I do for work?'")
    results = store.search(namespace, query="What do I do for work?", limit=2)
    for r in results:
        print(f"  - {r.value['content']} (score: {r.score:.3f})")

    # Semantic search for pets
    print("\nQuery: 'Do I have any pets?'")
    results = store.search(namespace, query="Do I have any pets?", limit=2)
    for r in results:
        print(f"  - {r.value['content']} (score: {r.score:.3f})")


# ============================================================================
# Namespace Patterns
# ============================================================================

class NamespaceManager:
    """
    Manage different memory namespaces.

    Namespace patterns:
    - ("user", user_id) - User-specific memories
    - ("user", user_id, "preferences") - User preferences
    - ("user", user_id, "history") - Conversation summaries
    - ("global", "knowledge") - Shared knowledge base
    """

    def __init__(self, store: BaseStore):
        self.store = store

    def get_user_namespace(self, user_id: str, category: str = None) -> tuple:
        """Get namespace for user data."""
        if category:
            return ("user", user_id, category)
        return ("user", user_id)

    def get_global_namespace(self, category: str = "knowledge") -> tuple:
        """Get namespace for global/shared data."""
        return ("global", category)

    def store_user_preference(self, user_id: str, key: str, value: Any):
        """Store a user preference."""
        namespace = self.get_user_namespace(user_id, "preferences")
        self.store.put(namespace, key, {"value": value})

    def get_user_preference(self, user_id: str, key: str) -> Optional[Any]:
        """Get a user preference."""
        namespace = self.get_user_namespace(user_id, "preferences")
        item = self.store.get(namespace, key)
        return item.value.get("value") if item else None

    def store_conversation_summary(self, user_id: str, thread_id: str, summary: str):
        """Store a conversation summary for long-term memory."""
        namespace = self.get_user_namespace(user_id, "history")
        self.store.put(
            namespace,
            thread_id,
            {"summary": summary, "thread_id": thread_id}
        )

    def search_history(self, user_id: str, query: str, limit: int = 5) -> list:
        """Search conversation history."""
        namespace = self.get_user_namespace(user_id, "history")
        results = self.store.search(namespace, query=query, limit=limit)
        return [r.value for r in results]

    def store_global_knowledge(self, key: str, content: str, metadata: dict = None):
        """Store global knowledge."""
        namespace = self.get_global_namespace()
        self.store.put(
            namespace,
            key,
            {"content": content, "metadata": metadata or {}}
        )

    def search_global_knowledge(self, query: str, limit: int = 5) -> list:
        """Search global knowledge base."""
        namespace = self.get_global_namespace()
        results = self.store.search(namespace, query=query, limit=limit)
        return [r.value for r in results]


# ============================================================================
# Demo: Cross-Thread Memory
# ============================================================================

def demo_cross_thread_memory():
    """Demonstrate cross-thread memory persistence."""

    print("=== Cross-Thread Memory Demo ===\n")

    agent = MemoryEnabledAgent()
    user_id = "demo-user-123"

    # Thread 1: User provides information
    print("Thread 1 (Introduction):")
    response1 = agent.chat(user_id, "thread-1", "Hi! My name is Alice and I love Python programming.")
    print(f"User: Hi! My name is Alice and I love Python programming.")
    print(f"Agent: {response1}\n")

    response2 = agent.chat(user_id, "thread-1", "Please remember that my favorite food is sushi.")
    print(f"User: Please remember that my favorite food is sushi.")
    print(f"Agent: {response2}\n")

    # Thread 2: New conversation, different context
    print("Thread 2 (New Session - Days Later):")
    response3 = agent.chat(user_id, "thread-2", "Hey! Do you remember anything about me?")
    print(f"User: Hey! Do you remember anything about me?")
    print(f"Agent: {response3}\n")

    response4 = agent.chat(user_id, "thread-2", "What's my name and what food do I like?")
    print(f"User: What's my name and what food do I like?")
    print(f"Agent: {response4}\n")

    # Show stored memories
    print("Stored Memories:")
    memories = agent.get_memories(user_id)
    for mem in memories:
        print(f"  - {mem}")


def demo_multi_user_isolation():
    """Demonstrate memory isolation between users."""

    print("=== Multi-User Memory Isolation Demo ===\n")

    agent = MemoryEnabledAgent()

    # User 1 shares info
    agent.chat("user-alice", "thread-1", "Remember: my password hint is 'blue sky'")

    # User 2 tries to access
    response = agent.chat("user-bob", "thread-2", "What is Alice's password hint?")
    print(f"Bob asks about Alice's info: {response}")

    # Verify Alice's memories
    alice_memories = agent.get_memories("user-alice")
    bob_memories = agent.get_memories("user-bob")

    print(f"\nAlice's memories: {len(alice_memories)}")
    print(f"Bob's memories: {len(bob_memories)}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Cross-Thread Memory Demonstrations\n")
    print("=" * 50 + "\n")

    print("1. Semantic Search Demo:")
    demo_semantic_search()

    print("\n" + "=" * 50 + "\n")

    print("2. Cross-Thread Memory Demo:")
    demo_cross_thread_memory()

    print("\n" + "=" * 50 + "\n")

    print("3. Multi-User Isolation Demo:")
    demo_multi_user_isolation()
