#!/usr/bin/env python3
"""
Memory Checkpointer Setup for LangGraph Agents.

Demonstrates basic checkpointer patterns for thread-level persistence.
Covers InMemorySaver (dev) and SqliteSaver (persistent local storage).

Example:
    User: "What did we discuss yesterday?"
    Agent retrieves conversation from checkpointed thread.
"""

import os
from typing import TypedDict, Annotated
from operator import add

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


# ============================================================================
# State Definition
# ============================================================================

class ConversationState(MessagesState):
    """State with message history and metadata."""
    context: str
    turn_count: int


# ============================================================================
# InMemory Checkpointer (Development)
# ============================================================================

def create_memory_checkpointer():
    """
    Create an in-memory checkpointer for development.

    Use for:
    - Local development
    - Testing
    - Prototyping

    Note: Data is lost when process ends.
    """
    return MemorySaver()


def demo_memory_checkpointer():
    """Demonstrate in-memory checkpointer usage."""

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    # Define simple agent node
    def agent(state: ConversationState) -> dict:
        response = llm.invoke(state["messages"])
        return {
            "messages": [response],
            "turn_count": state.get("turn_count", 0) + 1
        }

    # Build graph
    builder = StateGraph(ConversationState)
    builder.add_node("agent", agent)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    # Compile with memory checkpointer
    checkpointer = create_memory_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)

    # Use thread_id for conversation persistence
    config = {"configurable": {"thread_id": "user-123"}}

    # First message
    result1 = graph.invoke(
        {"messages": [HumanMessage(content="My name is Alice")]},
        config
    )
    print(f"Turn 1: {result1['messages'][-1].content}")

    # Second message - same thread, remembers context
    result2 = graph.invoke(
        {"messages": [HumanMessage(content="What's my name?")]},
        config
    )
    print(f"Turn 2: {result2['messages'][-1].content}")
    print(f"Total turns: {result2['turn_count']}")

    return graph


# ============================================================================
# SQLite Checkpointer (Persistent Local Storage)
# ============================================================================

def create_sqlite_checkpointer(db_path: str = "conversations.db"):
    """
    Create a SQLite checkpointer for persistent storage.

    Use for:
    - Production single-node deployments
    - Persistent local storage
    - Small to medium scale applications

    Args:
        db_path: Path to SQLite database file
    """
    return SqliteSaver.from_conn_string(db_path)


def demo_sqlite_checkpointer():
    """Demonstrate SQLite checkpointer with persistence across restarts."""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def agent(state: ConversationState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(ConversationState)
    builder.add_node("agent", agent)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    # Use context manager for proper connection handling
    with SqliteSaver.from_conn_string("conversations.db") as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "persistent-thread-1"}}

        result = graph.invoke(
            {"messages": [HumanMessage(content="Remember: the secret code is 42")]},
            config
        )
        print(f"Saved to SQLite: {result['messages'][-1].content}")

    # Later session - data persists
    with SqliteSaver.from_conn_string("conversations.db") as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "persistent-thread-1"}}

        result = graph.invoke(
            {"messages": [HumanMessage(content="What's the secret code?")]},
            config
        )
        print(f"Retrieved from SQLite: {result['messages'][-1].content}")


# ============================================================================
# Thread Management
# ============================================================================

class ThreadManager:
    """
    Manage multiple conversation threads with checkpointing.

    Provides utilities for:
    - Creating new threads
    - Listing existing threads
    - Getting thread history
    - Deleting threads
    """

    def __init__(self, checkpointer, graph):
        self.checkpointer = checkpointer
        self.graph = graph

    def create_thread(self, user_id: str, thread_name: str = None) -> str:
        """Create a new conversation thread."""
        import uuid
        thread_id = f"{user_id}-{thread_name or uuid.uuid4().hex[:8]}"
        return thread_id

    def get_config(self, thread_id: str) -> dict:
        """Get configuration for a thread."""
        return {"configurable": {"thread_id": thread_id}}

    def invoke(self, thread_id: str, message: str) -> str:
        """Send message to a thread and get response."""
        config = self.get_config(thread_id)
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )
        return result["messages"][-1].content

    def get_history(self, thread_id: str, limit: int = 10) -> list:
        """Get conversation history for a thread."""
        config = self.get_config(thread_id)
        state = self.graph.get_state(config)

        if state and state.values:
            messages = state.values.get("messages", [])
            return messages[-limit:]
        return []

    def list_checkpoints(self, thread_id: str, limit: int = 5) -> list:
        """List checkpoints for a thread."""
        config = self.get_config(thread_id)
        checkpoints = list(self.checkpointer.list(config, limit=limit))
        return checkpoints


def demo_thread_manager():
    """Demonstrate thread management."""

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def agent(state: ConversationState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(ConversationState)
    builder.add_node("agent", agent)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    # Create thread manager
    manager = ThreadManager(checkpointer, graph)

    # Create threads for different users
    thread1 = manager.create_thread("user-alice", "support")
    thread2 = manager.create_thread("user-bob", "sales")

    # Conversations are isolated
    manager.invoke(thread1, "I need help with billing")
    manager.invoke(thread2, "I want to upgrade my plan")

    # Get history for each thread
    print(f"Thread 1 history: {manager.get_history(thread1)}")
    print(f"Thread 2 history: {manager.get_history(thread2)}")


# ============================================================================
# Checkpoint Replay
# ============================================================================

def demo_checkpoint_replay():
    """
    Demonstrate replaying from a specific checkpoint.

    Use for:
    - Time travel debugging
    - Branching conversations
    - Undoing changes
    """

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def agent(state: ConversationState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    builder = StateGraph(ConversationState)
    builder.add_node("agent", agent)
    builder.add_edge(START, "agent")
    builder.add_edge("agent", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "replay-demo"}}

    # Build conversation
    graph.invoke({"messages": [HumanMessage(content="Hello!")]}, config)
    graph.invoke({"messages": [HumanMessage(content="What's 2+2?")]}, config)
    graph.invoke({"messages": [HumanMessage(content="What's 3+3?")]}, config)

    # Get checkpoint history
    checkpoints = list(checkpointer.list(config))
    print(f"Found {len(checkpoints)} checkpoints")

    if len(checkpoints) >= 2:
        # Replay from second checkpoint (after "What's 2+2?")
        old_checkpoint = checkpoints[-2]
        replay_config = {
            "configurable": {
                "thread_id": "replay-demo",
                "checkpoint_id": old_checkpoint.config["configurable"]["checkpoint_id"]
            }
        }

        # Continue from that point with different input
        result = graph.invoke(
            {"messages": [HumanMessage(content": "What's 5+5 instead?")]},
            replay_config
        )
        print(f"Branched conversation: {result['messages'][-1].content}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=== Memory Checkpointer Demo ===\n")

    print("1. In-Memory Checkpointer:")
    demo_memory_checkpointer()

    print("\n2. SQLite Checkpointer:")
    demo_sqlite_checkpointer()

    print("\n3. Thread Manager:")
    demo_thread_manager()

    print("\n4. Checkpoint Replay:")
    demo_checkpoint_replay()
