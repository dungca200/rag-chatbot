# Memory Stores Guide

Memory stores enable cross-thread persistence in LangGraph, allowing agents to share memories across different conversations.

## Overview

```
Checkpointer: Thread-level state (conversation within a thread)
Memory Store: Cross-thread state (memories shared across threads)
```

## InMemoryStore

### Basic Setup

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
```

### With Semantic Search

```python
from langgraph.store.memory import InMemoryStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Gemini embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

store = InMemoryStore(
    index={
        "embed": embeddings,
        "dims": 768  # Gemini embedding dimensions
    }
)
```

### Compile with Store

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
store = InMemoryStore()

graph = builder.compile(
    checkpointer=checkpointer,
    store=store
)
```

## Store Operations

### Put (Store)

```python
# Namespace: tuple of strings
namespace = ("memories", "user-123")

# Key: unique identifier
key = "memory-uuid-123"

# Value: dictionary
value = {"content": "User likes pizza", "type": "preference"}

store.put(namespace, key, value)
```

### Get

```python
item = store.get(namespace, key)
if item:
    print(item.value)  # {"content": "...", "type": "..."}
    print(item.key)    # "memory-uuid-123"
```

### Search

```python
# Basic search
results = store.search(namespace, limit=10)

# Semantic search (requires index)
results = store.search(
    namespace,
    query="What food does the user like?",
    limit=5
)

for result in results:
    print(result.value)
    print(result.score)  # Similarity score
```

### Delete

```python
store.delete(namespace, key)
```

## Namespace Patterns

### User-Scoped

```python
# User memories
namespace = ("user", user_id, "memories")

# User preferences
namespace = ("user", user_id, "preferences")

# User history
namespace = ("user", user_id, "history")
```

### Organization-Scoped

```python
# Organization knowledge base
namespace = ("org", org_id, "knowledge")

# Team-specific data
namespace = ("org", org_id, "team", team_id)
```

### Global

```python
# Shared knowledge
namespace = ("global", "knowledge")

# System settings
namespace = ("global", "settings")
```

## Accessing Store in Nodes

### Function Signature

```python
from langgraph.store.base import BaseStore

def my_node(state: MyState, store: BaseStore) -> dict:
    """Node with store access."""
    # Access store
    memories = store.search(("memories", state["user_id"]))
    return {"context": memories}
```

### With Config

```python
from langchain_core.runnables import RunnableConfig

def my_node(
    state: MyState,
    config: RunnableConfig,
    store: BaseStore
) -> dict:
    """Node with config and store."""
    user_id = config["configurable"]["user_id"]
    namespace = ("memories", user_id)

    memories = store.search(namespace, query=state["query"])
    return {"memories": [m.value for m in memories]}
```

## Semantic Search

### How It Works

1. Store embeds content on `put()` using configured embeddings
2. Search embeds query and finds similar vectors
3. Returns results sorted by similarity score

### Configuration

```python
from langchain.embeddings import init_embeddings

# OpenAI embeddings
embeddings = init_embeddings("openai:text-embedding-3-small")
store = InMemoryStore(index={"embed": embeddings, "dims": 1536})

# Gemini embeddings
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
store = InMemoryStore(index={"embed": embeddings, "dims": 768})
```

### Search with Filters

```python
# Search with metadata filter (if supported)
results = store.search(
    namespace,
    query="programming languages",
    filter={"type": "preference"},
    limit=5
)
```

## Memory Agent Pattern

```python
import uuid
from langgraph.store.base import BaseStore

def agent_with_memory(state: AgentState, store: BaseStore) -> dict:
    user_id = state["user_id"]
    namespace = ("memories", user_id)

    # 1. Retrieve relevant memories
    last_message = state["messages"][-1].content
    memories = store.search(namespace, query=last_message, limit=5)

    memory_context = "\n".join([m.value["content"] for m in memories])

    # 2. Check if user wants to remember something
    if "remember" in last_message.lower():
        store.put(
            namespace,
            str(uuid.uuid4()),
            {
                "content": last_message,
                "type": "user_stated",
                "created_at": datetime.now().isoformat()
            }
        )

    # 3. Generate response with memory context
    response = llm.invoke([
        {"role": "system", "content": f"User memories:\n{memory_context}"},
        *state["messages"]
    ])

    return {"messages": [response]}
```

## Cross-Thread Example

```python
# Thread 1: User provides info
config1 = {"configurable": {"thread_id": "thread-1", "user_id": "alice"}}
graph.invoke(
    {"messages": [HumanMessage("My name is Alice")]},
    config1
)

# Thread 2: Different conversation, same user
config2 = {"configurable": {"thread_id": "thread-2", "user_id": "alice"}}
graph.invoke(
    {"messages": [HumanMessage("What's my name?")]},
    config2
)
# Agent retrieves "Alice" from memory store
```

## Best Practices

### Memory Structure

```python
# Good: Structured with metadata
{
    "content": "User prefers Python",
    "type": "preference",
    "source": "conversation:thread-123",
    "confidence": 0.9,
    "created_at": "2024-01-15T10:30:00Z"
}

# Bad: Unstructured
{
    "data": "Python preference"
}
```

### Namespace Design

```python
# Good: Hierarchical, scoped
("user", user_id, "preferences")
("org", org_id, "knowledge", "products")

# Bad: Flat, ambiguous
("data",)
("stuff", user_id)
```

### Memory Lifecycle

```python
# Add timestamp for cleanup
store.put(namespace, key, {
    "content": content,
    "created_at": datetime.now().isoformat(),
    "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
})

# Periodic cleanup
for item in store.search(namespace, limit=10000):
    if item.value.get("expires_at"):
        if datetime.fromisoformat(item.value["expires_at"]) < datetime.now():
            store.delete(namespace, item.key)
```

## Production Considerations

### Limitations of InMemoryStore

- Data lost on restart
- Not suitable for multi-node deployments
- Memory usage grows with data

### Alternatives

For production, consider:
- Redis-based stores
- PostgreSQL with pgvector
- Cloud-native vector databases (Pinecone, Weaviate)

### Custom Store Implementation

```python
from langgraph.store.base import BaseStore

class RedisStore(BaseStore):
    """Custom Redis-based store."""

    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url)

    def put(self, namespace: tuple, key: str, value: dict):
        ns_key = ":".join(namespace)
        self.client.hset(ns_key, key, json.dumps(value))

    def get(self, namespace: tuple, key: str):
        ns_key = ":".join(namespace)
        data = self.client.hget(ns_key, key)
        return json.loads(data) if data else None

    def search(self, namespace: tuple, query: str = None, limit: int = 10):
        # Implement search logic
        pass

    def delete(self, namespace: tuple, key: str):
        ns_key = ":".join(namespace)
        self.client.hdel(ns_key, key)
```
