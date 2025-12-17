---
name: agent-memory
description: Production-ready memory and persistence patterns for LangGraph agents. Covers checkpointers (InMemory, SQLite, PostgreSQL), cross-thread memory stores with semantic search, conversation history management, and memory cleanup strategies. Use when building agents that need conversation continuity, user-specific memories across sessions, or production-grade state persistence.
license: Complete terms in LICENSE.txt
---

# Agent Memory & Persistence Guide

## Overview

Implement memory and persistence for LangGraph agents to enable conversation continuity, user-specific memories, and production-grade state management.

**Memory Architecture:**
```
Checkpointer    → Thread-level state (conversation within a thread)
Memory Store    → Cross-thread state (memories shared across threads)
```

**Checkpointer Selection:**
```
MemorySaver     → Development (in-memory, lost on restart)
SqliteSaver     → Single-node (file-based, persists locally)
PostgresSaver   → Production (database, multi-node support)
```

## Quick Start

### Basic Persistence (Development)

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
checkpointer = MemorySaver()
agent = create_react_agent(llm, tools=[], checkpointer=checkpointer)

# Thread-based conversations
config = {"configurable": {"thread_id": "user-123"}}
response = agent.invoke({"messages": [{"role": "user", "content": "Hello!"}]}, config)
```

### Cross-Thread Memory

```python
from scripts.cross_thread_memory import MemoryEnabledAgent

agent = MemoryEnabledAgent()

# Thread 1: User provides info
agent.chat("user-123", "thread-1", "My favorite color is blue")

# Thread 2: Different conversation, agent remembers
response = agent.chat("user-123", "thread-2", "What's my favorite color?")
# Response: "Your favorite color is blue"
```

### Production (PostgreSQL)

```python
from scripts.postgres_persistence import ProductionAgent

agent = ProductionAgent(
    database_url="postgresql://user:pass@host:5432/dbname"
)
await agent.setup()  # Creates tables

response = await agent.chat("user-123", "Hello!")
```

## Checkpointers

### 1. MemorySaver (Development)

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke(inputs, config)
```

### 2. SqliteSaver (Local Persistence)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("conversations.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = graph.invoke(inputs, config)
```

### 3. PostgresSaver (Production)

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@host:5432/dbname"
)
await checkpointer.setup()

graph = builder.compile(checkpointer=checkpointer)
result = await graph.ainvoke(inputs, config)
```

## Memory Stores

### InMemoryStore with Semantic Search

```python
from langgraph.store.memory import InMemoryStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
store = InMemoryStore(
    index={"embed": embeddings, "dims": 768}
)

# Compile with both checkpointer + store
graph = builder.compile(checkpointer=checkpointer, store=store)
```

### Store Operations

```python
# Store memory
namespace = ("memories", user_id)
store.put(namespace, "memory-123", {"content": "User likes pizza"})

# Retrieve memory
item = store.get(namespace, "memory-123")
print(item.value)  # {"content": "User likes pizza"}

# Semantic search
results = store.search(namespace, query="What food does user like?", limit=5)
for result in results:
    print(f"{result.value['content']} (score: {result.score:.3f})")

# Delete memory
store.delete(namespace, "memory-123")
```

### Namespace Patterns

```python
# User-scoped
namespace = ("user", user_id, "memories")
namespace = ("user", user_id, "preferences")

# Organization-scoped
namespace = ("org", org_id, "knowledge")

# Global
namespace = ("global", "knowledge")
```

## Memory Management

### Message Trimming

```python
from langchain_core.messages import trim_messages

# Trim by token count
trimmed = trim_messages(
    messages,
    max_tokens=4000,
    strategy="last",
    include_system=True,
    start_on="human"
)

# Trim by message count
from scripts.memory_management import trim_by_message_count
trimmed = trim_by_message_count(messages, max_messages=20)
```

### Conversation Summarization

```python
from scripts.memory_management import ConversationSummarizer

summarizer = ConversationSummarizer()

# Generate summary
summary = summarizer.summarize(messages)

# Extract user facts
facts = summarizer.extract_user_facts(messages)
# ["User's name is Alice", "Works at tech startup", "Prefers Python"]
```

### Sliding Window Memory

```python
from scripts.memory_management import SlidingWindowMemory

window = SlidingWindowMemory(window_size=10)

# Automatically summarizes old messages
processed = window.process_messages(messages)
# Returns: [SystemMessage(summary)] + last 10 messages
```

### Memory Cleanup

```python
from scripts.memory_management import MemoryCleanupManager

manager = MemoryCleanupManager(store, checkpointer)

# Remove memories older than 30 days
removed = manager.cleanup_old_memories(namespace, max_age_days=30)

# Consolidate similar memories
consolidated = manager.consolidate_memories(namespace)

# Archive conversation with summary
archive = manager.archive_conversation(thread_id, user_id, messages)
```

## Thread Management

### Thread ID Strategies

```python
# User-based (one thread per user)
thread_id = f"user:{user_id}"

# Session-based (new thread each session)
thread_id = f"user:{user_id}:session:{session_id}"

# Conversation-based (explicit conversation IDs)
thread_id = f"conversation:{conversation_id}"
```

### Checkpoint Replay

```python
# Get state at specific checkpoint
config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_id": "abc123"
    }
}
state = graph.get_state(config)

# Continue from checkpoint
result = graph.invoke({"messages": [new_message]}, config)
```

### State History

```python
# Get all checkpoints for a thread
for checkpoint in checkpointer.list(config):
    print(f"ID: {checkpoint.config['configurable']['checkpoint_id']}")
    print(f"Metadata: {checkpoint.metadata}")
```

## Accessing Store in Nodes

```python
from langgraph.store.base import BaseStore

def agent_node(state: AgentState, store: BaseStore) -> dict:
    user_id = state["user_id"]
    namespace = ("memories", user_id)

    # Retrieve relevant memories
    memories = store.search(namespace, query=state["query"], limit=5)

    # Store new memory
    store.put(namespace, str(uuid.uuid4()), {
        "content": "New fact about user",
        "created_at": datetime.now().isoformat()
    })

    return {"context": [m.value for m in memories]}
```

## Production Considerations

### Connection Pooling

```python
checkpointer = AsyncPostgresSaver.from_conn_string(
    connection_string,
    pool_size=20,
    max_overflow=10
)
```

### Health Checks

```python
async def check_health():
    try:
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
```

### Cleanup Strategy

```python
async def cleanup_expired_checkpoints(pool, ttl_days: int = 30):
    cutoff = datetime.now() - timedelta(days=ttl_days)
    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM checkpoints WHERE created_at < %s",
            (cutoff,)
        )
```

## Environment Variables

```bash
GOOGLE_API_KEY=your-gemini-api-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

## Dependencies

```
langgraph>=0.2.0
langgraph-checkpoint>=0.2.0
langgraph-checkpoint-sqlite>=0.1.0
langgraph-checkpoint-postgres>=0.1.0
psycopg[binary]>=3.0.0
langchain-google-genai>=2.0.0
```

## Reference Files

- [references/checkpointers.md](references/checkpointers.md) - Checkpointer comparison, setup guides
- [references/memory_stores.md](references/memory_stores.md) - InMemoryStore, semantic search, namespaces
- [references/persistence_patterns.md](references/persistence_patterns.md) - Thread management, replay, cleanup

## Scripts

- `scripts/memory_checkpointer.py` - Basic checkpointer setup, thread management
- `scripts/postgres_persistence.py` - Production PostgreSQL setup
- `scripts/cross_thread_memory.py` - Cross-thread memory with semantic search
- `scripts/memory_management.py` - Trimming, summarization, cleanup
