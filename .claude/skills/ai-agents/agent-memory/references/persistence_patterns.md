# Persistence Patterns

Common patterns for managing persistence in LangGraph agents.

## Thread Management

### Thread ID Strategies

```python
# User-based (one thread per user)
thread_id = f"user:{user_id}"

# Session-based (new thread each session)
thread_id = f"user:{user_id}:session:{session_id}"

# Conversation-based (explicit conversation IDs)
thread_id = f"conversation:{conversation_id}"

# Hybrid (user + purpose)
thread_id = f"user:{user_id}:support:{ticket_id}"
```

### Thread Lifecycle

```python
class ThreadManager:
    """Manage conversation thread lifecycle."""

    def __init__(self, graph, checkpointer):
        self.graph = graph
        self.checkpointer = checkpointer

    def create_thread(self, user_id: str) -> str:
        """Create a new thread for a user."""
        thread_id = f"{user_id}:{uuid.uuid4().hex[:8]}"
        return thread_id

    def get_active_threads(self, user_id: str) -> list:
        """Get all active threads for a user."""
        threads = []
        # Iterate checkpoints (implementation depends on checkpointer)
        for cp in self.checkpointer.list(
            {"configurable": {"thread_id": f"{user_id}:*"}}
        ):
            threads.append(cp.config["configurable"]["thread_id"])
        return list(set(threads))

    def archive_thread(self, thread_id: str):
        """Archive a thread (mark as inactive)."""
        # Implementation depends on your archival strategy
        pass

    def delete_thread(self, thread_id: str):
        """Permanently delete a thread."""
        # Delete all checkpoints for thread
        pass
```

## Checkpoint Replay

### Time Travel Debugging

```python
def replay_from_checkpoint(graph, checkpointer, thread_id: str, checkpoint_id: str):
    """Replay conversation from a specific checkpoint."""

    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }

    # Get state at checkpoint
    state = graph.get_state(config)
    print(f"State at checkpoint: {state.values}")

    # Continue from checkpoint with new input
    result = graph.invoke(
        {"messages": [HumanMessage(content="New message")]},
        config
    )

    return result
```

### Conversation Branching

```python
def branch_conversation(
    graph,
    checkpointer,
    source_thread_id: str,
    checkpoint_id: str,
    new_thread_id: str
):
    """Create a new branch from a checkpoint."""

    # Get state at branch point
    source_config = {
        "configurable": {
            "thread_id": source_thread_id,
            "checkpoint_id": checkpoint_id
        }
    }
    state = graph.get_state(source_config)

    # Start new thread with same state
    new_config = {
        "configurable": {"thread_id": new_thread_id}
    }

    # Initialize new thread with state
    # Implementation depends on graph structure
    return new_thread_id
```

## State Recovery

### Handling Interruptions

```python
def recover_interrupted_conversation(graph, checkpointer, thread_id: str):
    """Recover from an interrupted conversation."""

    config = {"configurable": {"thread_id": thread_id}}

    # Get current state
    state = graph.get_state(config)

    if state.next:
        # Conversation was interrupted
        print(f"Resuming from: {state.next}")

        # Check for pending interrupts
        if state.tasks:
            for task in state.tasks:
                if task.interrupts:
                    print(f"Pending interrupt: {task.interrupts[0].value}")

                    # Resume with approval
                    from langgraph.types import Command
                    result = graph.invoke(
                        Command(resume={"approved": True}),
                        config
                    )
                    return result

    return state.values
```

### State Validation

```python
def validate_state(state: dict) -> bool:
    """Validate state before resuming."""
    required_keys = ["messages", "user_id"]

    for key in required_keys:
        if key not in state:
            return False

    # Validate message format
    messages = state.get("messages", [])
    if not isinstance(messages, list):
        return False

    return True
```

## Memory Cleanup

### TTL-Based Cleanup

```python
async def cleanup_expired_checkpoints(pool, ttl_days: int = 30):
    """Delete checkpoints older than TTL."""

    cutoff = datetime.now() - timedelta(days=ttl_days)

    async with pool.connection() as conn:
        # Delete old checkpoints
        result = await conn.execute(
            """
            DELETE FROM checkpoints
            WHERE created_at < %s
            RETURNING thread_id, checkpoint_id
            """,
            (cutoff,)
        )

        deleted = await result.fetchall()
        print(f"Deleted {len(deleted)} checkpoints")

        # Delete orphaned writes
        await conn.execute(
            """
            DELETE FROM writes w
            WHERE NOT EXISTS (
                SELECT 1 FROM checkpoints c
                WHERE c.thread_id = w.thread_id
                AND c.checkpoint_id = w.checkpoint_id
            )
            """
        )
```

### Size-Based Cleanup

```python
async def cleanup_by_size(pool, max_checkpoints_per_thread: int = 100):
    """Keep only N most recent checkpoints per thread."""

    async with pool.connection() as conn:
        # Get threads with too many checkpoints
        result = await conn.execute(
            """
            SELECT thread_id, COUNT(*) as count
            FROM checkpoints
            GROUP BY thread_id
            HAVING COUNT(*) > %s
            """,
            (max_checkpoints_per_thread,)
        )

        threads = await result.fetchall()

        for thread_id, count in threads:
            # Delete oldest checkpoints
            to_delete = count - max_checkpoints_per_thread
            await conn.execute(
                """
                DELETE FROM checkpoints
                WHERE thread_id = %s
                AND checkpoint_id IN (
                    SELECT checkpoint_id
                    FROM checkpoints
                    WHERE thread_id = %s
                    ORDER BY checkpoint_id ASC
                    LIMIT %s
                )
                """,
                (thread_id, thread_id, to_delete)
            )
```

### Summarize Before Delete

```python
async def archive_and_cleanup(
    graph,
    checkpointer,
    store,
    thread_id: str,
    summarizer
):
    """Archive conversation summary before cleanup."""

    config = {"configurable": {"thread_id": thread_id}}

    # Get full conversation
    state = graph.get_state(config)
    messages = state.values.get("messages", [])

    if messages:
        # Generate summary
        summary = summarizer.summarize(messages)

        # Extract facts
        facts = summarizer.extract_user_facts(messages)

        # Store in memory store
        user_id = state.values.get("user_id")
        if user_id:
            # Store summary
            store.put(
                ("archives", user_id),
                thread_id,
                {
                    "summary": summary,
                    "facts": facts,
                    "message_count": len(messages),
                    "archived_at": datetime.now().isoformat()
                }
            )

            # Store facts in user memories
            for fact in facts:
                store.put(
                    ("memories", user_id),
                    str(uuid.uuid4()),
                    {"content": fact, "source": f"archived:{thread_id}"}
                )

    # Delete checkpoints
    # (Implementation depends on checkpointer)
```

## Multi-Node Patterns

### Distributed Locking

```python
import asyncio
from contextlib import asynccontextmanager

class DistributedLock:
    """Distributed lock for concurrent access."""

    def __init__(self, pool):
        self.pool = pool

    @asynccontextmanager
    async def acquire(self, thread_id: str, timeout: int = 30):
        """Acquire lock for a thread."""
        async with self.pool.connection() as conn:
            try:
                # Try to acquire advisory lock
                await conn.execute(
                    "SELECT pg_advisory_lock(hashtext(%s))",
                    (thread_id,)
                )
                yield
            finally:
                # Release lock
                await conn.execute(
                    "SELECT pg_advisory_unlock(hashtext(%s))",
                    (thread_id,)
                )
```

### Optimistic Concurrency

```python
async def update_with_version(
    pool,
    thread_id: str,
    checkpoint_id: str,
    expected_version: int,
    new_data: dict
):
    """Update checkpoint with optimistic locking."""

    async with pool.connection() as conn:
        result = await conn.execute(
            """
            UPDATE checkpoints
            SET checkpoint = %s, version = version + 1
            WHERE thread_id = %s
            AND checkpoint_id = %s
            AND version = %s
            RETURNING version
            """,
            (new_data, thread_id, checkpoint_id, expected_version)
        )

        updated = await result.fetchone()
        if not updated:
            raise ConcurrencyError("Checkpoint was modified by another process")

        return updated[0]
```

## Migration Patterns

### Schema Migration

```python
MIGRATIONS = [
    ("001_initial", """
        CREATE TABLE checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            type TEXT,
            checkpoint BYTEA,
            metadata JSONB,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        );
    """),
    ("002_add_timestamps", """
        ALTER TABLE checkpoints
        ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """),
    ("003_add_indexes", """
        CREATE INDEX idx_checkpoints_created
        ON checkpoints(created_at DESC);
    """),
]

async def run_migrations(pool):
    """Run pending migrations."""
    async with pool.connection() as conn:
        # Create migrations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Get applied migrations
        result = await conn.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in await result.fetchall()}

        # Apply pending
        for version, sql in MIGRATIONS:
            if version not in applied:
                print(f"Applying migration: {version}")
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,)
                )
```

### Data Migration

```python
async def migrate_to_new_format(pool):
    """Migrate checkpoint data to new format."""

    async with pool.connection() as conn:
        # Get all checkpoints
        result = await conn.execute("SELECT * FROM checkpoints")

        async for row in result:
            # Transform data
            old_data = row["checkpoint"]
            new_data = transform_checkpoint(old_data)

            # Update
            await conn.execute(
                """
                UPDATE checkpoints
                SET checkpoint = %s
                WHERE thread_id = %s AND checkpoint_id = %s
                """,
                (new_data, row["thread_id"], row["checkpoint_id"])
            )
```
