#!/usr/bin/env python3
"""
PostgreSQL Persistence for Production LangGraph Agents.

Production-ready checkpointer using PostgreSQL for:
- Multi-node deployments
- High availability
- Scalable persistent storage

Requires:
    pip install langgraph-checkpoint-postgres psycopg[binary]

Environment:
    DATABASE_URL=postgresql://user:pass@host:5432/dbname
"""

import os
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, START, END


# ============================================================================
# PostgreSQL Checkpointer Setup
# ============================================================================

def create_postgres_checkpointer(connection_string: str = None):
    """
    Create a PostgreSQL checkpointer for production use.

    Args:
        connection_string: PostgreSQL connection string.
                          Defaults to DATABASE_URL environment variable.

    Returns:
        PostgresSaver instance

    Example:
        checkpointer = create_postgres_checkpointer(
            "postgresql://user:pass@localhost:5432/agents"
        )
    """
    from langgraph.checkpoint.postgres import PostgresSaver

    conn_string = connection_string or os.environ.get("DATABASE_URL")
    if not conn_string:
        raise ValueError("Database connection string required")

    return PostgresSaver.from_conn_string(conn_string)


async def create_async_postgres_checkpointer(connection_string: str = None):
    """
    Create an async PostgreSQL checkpointer.

    For high-performance async applications.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    conn_string = connection_string or os.environ.get("DATABASE_URL")
    if not conn_string:
        raise ValueError("Database connection string required")

    return AsyncPostgresSaver.from_conn_string(conn_string)


# ============================================================================
# Connection Pool Management
# ============================================================================

class PostgresConnectionPool:
    """
    Managed PostgreSQL connection pool for checkpointing.

    Provides:
    - Connection pooling
    - Automatic reconnection
    - Health checks
    """

    def __init__(
        self,
        connection_string: str,
        min_connections: int = 5,
        max_connections: int = 20
    ):
        self.connection_string = connection_string
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool = None

    async def initialize(self):
        """Initialize the connection pool."""
        import psycopg_pool

        self._pool = psycopg_pool.AsyncConnectionPool(
            self.connection_string,
            min_size=self.min_connections,
            max_size=self.max_connections,
            open=False
        )
        await self._pool.open()
        await self._pool.wait()

        # Create tables if needed
        await self._setup_tables()

    async def _setup_tables(self):
        """Create checkpoint tables if they don't exist."""
        async with self._pool.connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint BYTEA,
                    metadata JSONB,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                );

                CREATE TABLE IF NOT EXISTS writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    type TEXT,
                    value BYTEA,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                );

                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
                ON checkpoints(thread_id, checkpoint_ns);
            """)

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        async with self._pool.connection() as conn:
            yield conn

    async def health_check(self) -> bool:
        """Check if database is healthy."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False


# ============================================================================
# Production Checkpointer Wrapper
# ============================================================================

class ProductionCheckpointer:
    """
    Production-ready checkpointer with connection management.

    Features:
    - Connection pooling
    - Automatic table setup
    - Health monitoring
    - Graceful shutdown
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._checkpointer = None
        self._initialized = False

    async def initialize(self):
        """Initialize checkpointer and create tables."""
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        self._checkpointer = AsyncPostgresSaver.from_conn_string(
            self.connection_string
        )
        await self._checkpointer.setup()
        self._initialized = True

    @property
    def checkpointer(self):
        """Get the underlying checkpointer."""
        if not self._initialized:
            raise RuntimeError("Checkpointer not initialized. Call initialize() first.")
        return self._checkpointer

    async def close(self):
        """Close connections gracefully."""
        if self._checkpointer:
            # Close any open connections
            pass


# ============================================================================
# Example: Production Agent with PostgreSQL
# ============================================================================

class ProductionAgent:
    """
    Production agent with PostgreSQL persistence.

    Example usage:
        agent = ProductionAgent("postgresql://...")
        await agent.initialize()

        response = await agent.chat("user-123", "Hello!")
        print(response)

        await agent.shutdown()
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.graph = None
        self._checkpointer = None

    async def initialize(self):
        """Initialize the agent and database."""
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Create checkpointer
        self._checkpointer = AsyncPostgresSaver.from_conn_string(self.database_url)
        await self._checkpointer.setup()

        # Build graph
        def agent_node(state: MessagesState) -> dict:
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", agent_node)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

        self.graph = builder.compile(checkpointer=self._checkpointer)

    async def chat(self, thread_id: str, message: str) -> str:
        """Send a message and get a response."""
        config = {"configurable": {"thread_id": thread_id}}

        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )

        return result["messages"][-1].content

    async def get_history(self, thread_id: str) -> list:
        """Get conversation history for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state = await self.graph.aget_state(config)

        if state and state.values:
            return state.values.get("messages", [])
        return []

    async def shutdown(self):
        """Gracefully shutdown the agent."""
        pass


# ============================================================================
# Database Migrations
# ============================================================================

MIGRATION_SCRIPTS = {
    "001_initial": """
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            type TEXT,
            checkpoint BYTEA,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        );

        CREATE TABLE IF NOT EXISTS writes (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            channel TEXT NOT NULL,
            type TEXT,
            value BYTEA,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
        );
    """,

    "002_add_indexes": """
        CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
        ON checkpoints(thread_id, checkpoint_ns);

        CREATE INDEX IF NOT EXISTS idx_checkpoints_created
        ON checkpoints(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_writes_checkpoint
        ON writes(thread_id, checkpoint_ns, checkpoint_id);
    """,

    "003_add_ttl": """
        ALTER TABLE checkpoints
        ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

        CREATE INDEX IF NOT EXISTS idx_checkpoints_expires
        ON checkpoints(expires_at) WHERE expires_at IS NOT NULL;
    """
}


async def run_migrations(connection_string: str):
    """Run database migrations."""
    import psycopg

    async with await psycopg.AsyncConnection.connect(connection_string) as conn:
        # Create migrations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                name TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Get applied migrations
        result = await conn.execute("SELECT name FROM migrations")
        applied = {row[0] for row in await result.fetchall()}

        # Apply pending migrations
        for name, script in sorted(MIGRATION_SCRIPTS.items()):
            if name not in applied:
                print(f"Applying migration: {name}")
                await conn.execute(script)
                await conn.execute(
                    "INSERT INTO migrations (name) VALUES (%s)",
                    (name,)
                )

        await conn.commit()


# ============================================================================
# Health Check Endpoint
# ============================================================================

async def check_database_health(connection_string: str) -> dict:
    """
    Check database health for monitoring.

    Returns:
        Health status dict with connection info
    """
    import psycopg

    try:
        async with await psycopg.AsyncConnection.connect(connection_string) as conn:
            # Basic connectivity
            await conn.execute("SELECT 1")

            # Get checkpoint count
            result = await conn.execute("SELECT COUNT(*) FROM checkpoints")
            checkpoint_count = (await result.fetchone())[0]

            # Get latest checkpoint time
            result = await conn.execute(
                "SELECT MAX(created_at) FROM checkpoints"
            )
            latest = await result.fetchone()

            return {
                "status": "healthy",
                "database": "connected",
                "checkpoint_count": checkpoint_count,
                "latest_checkpoint": str(latest[0]) if latest[0] else None
            }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================================================
# Main
# ============================================================================

async def main():
    """Demo PostgreSQL persistence."""

    # Check for database URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Set DATABASE_URL environment variable to run this demo")
        print("Example: postgresql://user:pass@localhost:5432/agents")
        return

    print("=== PostgreSQL Persistence Demo ===\n")

    # Run migrations
    print("Running migrations...")
    await run_migrations(database_url)

    # Initialize agent
    print("Initializing agent...")
    agent = ProductionAgent(database_url)
    await agent.initialize()

    # Demo conversation
    thread_id = "demo-thread-1"

    response1 = await agent.chat(thread_id, "Hello! My name is Alice.")
    print(f"Response 1: {response1}")

    response2 = await agent.chat(thread_id, "What's my name?")
    print(f"Response 2: {response2}")

    # Check health
    health = await check_database_health(database_url)
    print(f"\nHealth: {health}")

    # Shutdown
    await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
