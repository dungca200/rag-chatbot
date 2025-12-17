# Checkpointers Guide

Checkpointers enable thread-level persistence in LangGraph agents, saving and restoring conversation state.

## Checkpointer Comparison

| Checkpointer | Use Case | Persistence | Multi-Node | Production |
|--------------|----------|-------------|------------|------------|
| `MemorySaver` | Development | In-memory | No | No |
| `InMemorySaver` | Development | In-memory | No | No |
| `SqliteSaver` | Single-node | File-based | No | Small scale |
| `AsyncSqliteSaver` | Async apps | File-based | No | Small scale |
| `PostgresSaver` | Production | Database | Yes | Yes |
| `AsyncPostgresSaver` | Async production | Database | Yes | Yes |

## Quick Start

### Development (In-Memory)

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Use with thread_id
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke(inputs, config)
```

### Local Persistence (SQLite)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Use context manager for proper cleanup
with SqliteSaver.from_conn_string("conversations.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = graph.invoke(inputs, config)
```

### Production (PostgreSQL)

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@host:5432/dbname"
)
await checkpointer.setup()  # Create tables

graph = builder.compile(checkpointer=checkpointer)
```

## Thread Configuration

```python
# Basic thread config
config = {
    "configurable": {
        "thread_id": "unique-thread-id"
    }
}

# With checkpoint namespace (for sub-graphs)
config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_ns": "support-workflow"
    }
}

# Resume from specific checkpoint
config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_id": "abc123-checkpoint-id"
    }
}
```

## Checkpoint Operations

### Get Current State

```python
state = graph.get_state(config)
print(state.values)  # Current state values
print(state.next)    # Next nodes to execute
```

### Get State History

```python
# Get all checkpoints for a thread
for checkpoint in checkpointer.list(config):
    print(f"ID: {checkpoint.config['configurable']['checkpoint_id']}")
    print(f"Metadata: {checkpoint.metadata}")
```

### Replay from Checkpoint

```python
# Get checkpoint history
checkpoints = list(checkpointer.list(config, limit=5))

# Replay from specific checkpoint
replay_config = {
    "configurable": {
        "thread_id": "user-123",
        "checkpoint_id": checkpoints[2].config["configurable"]["checkpoint_id"]
    }
}

result = graph.invoke(None, replay_config)
```

## SQLite Details

### Schema

```sql
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,
    metadata BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

### Async SQLite

```python
from langgraph.checkpoint.sqlite import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string("conversations.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    result = await graph.ainvoke(inputs, config)
```

## PostgreSQL Details

### Installation

```bash
pip install langgraph-checkpoint-postgres psycopg[binary]
```

### Connection String

```python
# Standard
"postgresql://user:password@host:5432/database"

# With SSL
"postgresql://user:password@host:5432/database?sslmode=require"

# Connection pool settings
"postgresql://user:password@host:5432/database?pool_size=10"
```

### Setup Tables

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(connection_string)
await checkpointer.setup()  # Creates tables if not exist
```

### Production Configuration

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# With connection pool
checkpointer = AsyncPostgresSaver.from_conn_string(
    connection_string,
    pool_size=20,
    max_overflow=10
)
```

## Best Practices

### Development

- Use `MemorySaver` for rapid iteration
- No setup required
- Data lost when process ends

### Testing

- Use `SqliteSaver` with `:memory:` for isolated tests
- Use temp files for integration tests

```python
import tempfile

with tempfile.NamedTemporaryFile(suffix=".db") as f:
    with SqliteSaver.from_conn_string(f.name) as checkpointer:
        # Test code
```

### Production

- Always use PostgreSQL
- Enable connection pooling
- Set up monitoring/alerting
- Implement cleanup/archival strategy

```python
# Health check
async def check_health():
    try:
        async with pool.connection() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
```

## Common Patterns

### User-Scoped Threads

```python
def get_thread_id(user_id: str, session_id: str = None) -> str:
    """Generate thread ID scoped to user."""
    if session_id:
        return f"{user_id}:{session_id}"
    return f"{user_id}:default"
```

### Thread Cleanup

```python
async def cleanup_old_threads(days: int = 30):
    """Delete threads older than N days."""
    cutoff = datetime.now() - timedelta(days=days)

    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM checkpoints WHERE created_at < %s",
            (cutoff,)
        )
```

### Thread Migration

```python
def migrate_thread(old_id: str, new_id: str):
    """Migrate conversation to new thread ID."""
    # Get state from old thread
    state = graph.get_state({"configurable": {"thread_id": old_id}})

    # Invoke on new thread with same state
    graph.invoke(state.values, {"configurable": {"thread_id": new_id}})
```
