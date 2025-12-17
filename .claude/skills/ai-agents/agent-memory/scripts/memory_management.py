#!/usr/bin/env python3
"""
Memory Management for LangGraph Agents.

Strategies for managing agent memory over time:
- Conversation summarization
- Memory cleanup and archival
- Memory consolidation
- Token budget management
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from langchain_core.messages import (
    HumanMessage, AIMessage, SystemMessage, BaseMessage,
    trim_messages, filter_messages
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, Field


# ============================================================================
# Message Trimming Strategies
# ============================================================================

def trim_by_token_count(
    messages: List[BaseMessage],
    max_tokens: int = 4000,
    model: str = "gemini-2.5-flash"
) -> List[BaseMessage]:
    """
    Trim messages to fit within token budget.

    Keeps system message and most recent messages.
    """
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",
        token_counter=len,  # Simplified; use actual tokenizer in production
        include_system=True,
        allow_partial=False,
        start_on="human"
    )


def trim_by_message_count(
    messages: List[BaseMessage],
    max_messages: int = 20
) -> List[BaseMessage]:
    """
    Keep only the most recent N messages.

    Always preserves system message if present.
    """
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep system + last N messages
    trimmed = other_messages[-max_messages:]

    return system_messages + trimmed


def filter_by_type(
    messages: List[BaseMessage],
    include_types: List[str] = None,
    exclude_types: List[str] = None
) -> List[BaseMessage]:
    """
    Filter messages by type.

    Args:
        messages: List of messages
        include_types: Only include these types (human, ai, system, tool)
        exclude_types: Exclude these types
    """
    return filter_messages(
        messages,
        include_types=include_types,
        exclude_types=exclude_types
    )


# ============================================================================
# Conversation Summarization
# ============================================================================

class ConversationSummarizer:
    """
    Summarize conversations for long-term memory.

    Use when:
    - Conversation exceeds token limit
    - Archiving old conversations
    - Creating user profiles from chat history
    """

    def __init__(self, llm=None):
        self.llm = llm or ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def summarize(self, messages: List[BaseMessage]) -> str:
        """Generate a summary of the conversation."""

        # Format messages for summarization
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted.append(f"Assistant: {msg.content}")

        conversation_text = "\n".join(formatted)

        prompt = f"""Summarize this conversation, capturing:
1. Key topics discussed
2. Important information shared by the user
3. Decisions or conclusions reached
4. Any action items or follow-ups

Conversation:
{conversation_text}

Summary:"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content

    def extract_user_facts(self, messages: List[BaseMessage]) -> List[str]:
        """Extract factual information about the user from conversation."""

        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted.append(f"Assistant: {msg.content}")

        conversation_text = "\n".join(formatted)

        prompt = f"""Extract specific facts about the user from this conversation.
Return only factual statements, one per line.
Examples: name, preferences, job, location, family, interests.

Conversation:
{conversation_text}

Facts about the user (one per line):"""

        response = self.llm.invoke([HumanMessage(content=prompt)])

        # Parse facts
        facts = [
            line.strip().lstrip("- ").lstrip("• ")
            for line in response.content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        return facts


# ============================================================================
# Memory Cleanup Manager
# ============================================================================

class MemoryCleanupManager:
    """
    Manage memory cleanup and archival.

    Strategies:
    - TTL-based expiration
    - Importance-based retention
    - Summarization before deletion
    """

    def __init__(self, store: InMemoryStore, checkpointer=None):
        self.store = store
        self.checkpointer = checkpointer
        self.summarizer = ConversationSummarizer()

    def cleanup_old_memories(
        self,
        namespace: tuple,
        max_age_days: int = 30,
        keep_important: bool = True
    ) -> int:
        """
        Remove memories older than max_age_days.

        Returns:
            Number of memories removed
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0

        # Get all memories in namespace
        memories = list(self.store.search(namespace, limit=10000))

        for memory in memories:
            created_at = memory.value.get("created_at")
            is_important = memory.value.get("important", False)

            if created_at:
                memory_date = datetime.fromisoformat(created_at)

                if memory_date < cutoff:
                    if not (keep_important and is_important):
                        self.store.delete(namespace, memory.key)
                        removed += 1

        return removed

    def consolidate_memories(
        self,
        namespace: tuple,
        similarity_threshold: float = 0.9
    ) -> int:
        """
        Consolidate similar memories into single entries.

        Returns:
            Number of memories consolidated
        """
        memories = list(self.store.search(namespace, limit=1000))
        consolidated = 0

        # Group similar memories
        groups = []
        used = set()

        for i, mem1 in enumerate(memories):
            if mem1.key in used:
                continue

            group = [mem1]
            used.add(mem1.key)

            for j, mem2 in enumerate(memories[i+1:], i+1):
                if mem2.key in used:
                    continue

                # Check similarity (if scores available)
                if hasattr(mem2, 'score') and mem2.score >= similarity_threshold:
                    group.append(mem2)
                    used.add(mem2.key)

            if len(group) > 1:
                groups.append(group)

        # Merge groups
        for group in groups:
            # Create merged memory
            contents = [m.value.get("content", "") for m in group]
            merged_content = " | ".join(set(contents))

            # Delete old memories
            for mem in group:
                self.store.delete(namespace, mem.key)
                consolidated += 1

            # Store merged memory
            self.store.put(
                namespace,
                str(uuid.uuid4()),
                {
                    "content": merged_content,
                    "merged_from": len(group),
                    "created_at": datetime.now().isoformat()
                }
            )
            consolidated -= 1  # Account for new memory

        return consolidated

    def archive_conversation(
        self,
        thread_id: str,
        user_id: str,
        messages: List[BaseMessage]
    ) -> dict:
        """
        Archive a conversation with summary.

        Returns:
            Archive record
        """
        # Generate summary
        summary = self.summarizer.summarize(messages)

        # Extract user facts
        facts = self.summarizer.extract_user_facts(messages)

        # Create archive record
        archive = {
            "thread_id": thread_id,
            "user_id": user_id,
            "message_count": len(messages),
            "summary": summary,
            "extracted_facts": facts,
            "archived_at": datetime.now().isoformat()
        }

        # Store in archive namespace
        namespace = ("archives", user_id)
        self.store.put(namespace, thread_id, archive)

        # Store extracted facts in user memory
        memory_namespace = ("memories", user_id)
        for fact in facts:
            self.store.put(
                memory_namespace,
                str(uuid.uuid4()),
                {
                    "content": fact,
                    "source": f"conversation:{thread_id}",
                    "created_at": datetime.now().isoformat()
                }
            )

        return archive


# ============================================================================
# Sliding Window Memory
# ============================================================================

class SlidingWindowMemory:
    """
    Maintain a sliding window of recent messages with summarization.

    As window fills:
    1. Summarize oldest messages
    2. Store summary as context
    3. Remove old messages from window
    """

    def __init__(
        self,
        window_size: int = 10,
        llm=None
    ):
        self.window_size = window_size
        self.llm = llm or ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.summarizer = ConversationSummarizer(self.llm)
        self.summaries: List[str] = []

    def process_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Process messages through sliding window.

        Returns messages within window + summary context.
        """
        if len(messages) <= self.window_size:
            return messages

        # Messages to summarize
        to_summarize = messages[:-self.window_size]

        # Generate summary
        if to_summarize:
            summary = self.summarizer.summarize(to_summarize)
            self.summaries.append(summary)

        # Create context message
        context = "\n\n".join(self.summaries)
        context_message = SystemMessage(
            content=f"Previous conversation summary:\n{context}"
        )

        # Return context + recent messages
        return [context_message] + messages[-self.window_size:]

    def get_full_context(self) -> str:
        """Get all summarized context."""
        return "\n\n".join(self.summaries)


# ============================================================================
# Memory Budget Manager
# ============================================================================

class MemoryBudgetManager:
    """
    Manage memory within token/cost budgets.

    Strategies:
    - Prioritize recent messages
    - Keep high-importance memories
    - Compress when over budget
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000  # Reserve for response
    ):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimate: 4 chars per token
        return len(text) // 4

    def fit_to_budget(
        self,
        messages: List[BaseMessage],
        memories: List[str] = None,
        system_prompt: str = None
    ) -> tuple:
        """
        Fit messages and memories within token budget.

        Returns:
            (fitted_messages, fitted_memories, tokens_used)
        """
        tokens_used = 0

        # System prompt (required)
        if system_prompt:
            tokens_used += self.estimate_tokens(system_prompt)

        # Prioritize recent messages
        fitted_messages = []
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens(msg.content)
            if tokens_used + msg_tokens <= self.available_tokens:
                fitted_messages.insert(0, msg)
                tokens_used += msg_tokens
            else:
                break

        # Add memories if space allows
        fitted_memories = []
        if memories:
            for mem in memories:
                mem_tokens = self.estimate_tokens(mem)
                if tokens_used + mem_tokens <= self.available_tokens:
                    fitted_memories.append(mem)
                    tokens_used += mem_tokens
                else:
                    break

        return fitted_messages, fitted_memories, tokens_used


# ============================================================================
# Demo Functions
# ============================================================================

def demo_message_trimming():
    """Demonstrate message trimming strategies."""

    print("=== Message Trimming Demo ===\n")

    # Create sample conversation
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello!"),
        AIMessage(content="Hi there! How can I help you today?"),
        HumanMessage(content="Tell me about Python."),
        AIMessage(content="Python is a versatile programming language..."),
        HumanMessage(content="What about JavaScript?"),
        AIMessage(content="JavaScript is primarily used for web development..."),
        HumanMessage(content="Which should I learn first?"),
        AIMessage(content="It depends on your goals..."),
        HumanMessage(content="I want to do web development."),
        AIMessage(content="Then I'd recommend starting with JavaScript..."),
    ]

    print(f"Original message count: {len(messages)}")

    # Trim by count
    trimmed = trim_by_message_count(messages, max_messages=4)
    print(f"After trimming to 4 messages: {len(trimmed)}")

    # Filter by type
    human_only = filter_by_type(messages, include_types=["human"])
    print(f"Human messages only: {len(human_only)}")


def demo_conversation_summarization():
    """Demonstrate conversation summarization."""

    print("=== Conversation Summarization Demo ===\n")

    messages = [
        HumanMessage(content="Hi, I'm looking for a new laptop."),
        AIMessage(content="I'd be happy to help! What will you primarily use it for?"),
        HumanMessage(content="Mainly software development and some gaming."),
        AIMessage(content="For development and gaming, I'd recommend at least 16GB RAM and a dedicated GPU."),
        HumanMessage(content="My budget is around $1500."),
        AIMessage(content="Great budget! You could get a Dell XPS 15 or Lenovo ThinkPad X1 Carbon."),
        HumanMessage(content="I think I'll go with the Dell. Thanks!"),
    ]

    summarizer = ConversationSummarizer()

    # Generate summary
    summary = summarizer.summarize(messages)
    print(f"Summary:\n{summary}\n")

    # Extract facts
    facts = summarizer.extract_user_facts(messages)
    print("Extracted facts:")
    for fact in facts:
        print(f"  - {fact}")


def demo_sliding_window():
    """Demonstrate sliding window memory."""

    print("=== Sliding Window Memory Demo ===\n")

    window = SlidingWindowMemory(window_size=4)

    # Simulate growing conversation
    messages = []
    for i in range(10):
        messages.append(HumanMessage(content=f"Message {i+1} from user"))
        messages.append(AIMessage(content=f"Response {i+1} from assistant"))

        processed = window.process_messages(messages)
        print(f"Turn {i+1}: {len(messages)} total, {len(processed)} in window")

    print(f"\nFull context:\n{window.get_full_context()}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Memory Management Demonstrations\n")
    print("=" * 50 + "\n")

    demo_message_trimming()

    print("\n" + "=" * 50 + "\n")

    demo_conversation_summarization()

    print("\n" + "=" * 50 + "\n")

    demo_sliding_window()
