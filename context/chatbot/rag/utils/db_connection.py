"""
Database connection management utilities.

This module provides centralized connection pool management for PostgreSQL
to prevent connection leakage and ensure efficient connection use.
"""
import logging
from typing import Optional, Union
from urllib.parse import quote_plus, urlparse, urlunparse
from psycopg_pool import ConnectionPool
from settings import settings

logger = logging.getLogger(__name__)

# Global connection pool
_GLOBAL_PG_POOL: Optional[ConnectionPool] = None

def prepare_database_uri(db_uri: str) -> str:
    """
    Prepare the database URI by properly encoding special characters in the password.
    
    Args:
        db_uri: The original database URI string
        
    Returns:
        str: A properly encoded database URI
    """
    # Handle PostgreSQL URL format
    if db_uri.startswith('postgresql://'):
        try:
            # Parse the URL into components
            parsed = urlparse(db_uri)
            
            # Extract username and password
            auth_parts = parsed.netloc.split('@')[0].split(':')
            if len(auth_parts) >= 2:
                username = auth_parts[0]
                # The password may contain the : character, so join remaining parts
                password = ':'.join(auth_parts[1:])
                host_part = parsed.netloc.split('@')[1]
                
                # URL encode the password
                encoded_password = quote_plus(password)
                
                # Reconstruct the URL with encoded password
                new_netloc = f"{username}:{encoded_password}@{host_part}"
                parsed = parsed._replace(netloc=new_netloc)
                
                return urlunparse(parsed)
        except Exception as e:
            logger.warning(f"Error encoding database URI: {str(e)}. Using original URI.")
    
    # If anything fails or if it's not a PostgreSQL URL, return original
    return db_uri

def get_connection_pool() -> Union[ConnectionPool, str]:
    """
    Get or create the global connection pool with optimized settings.
    
    Ensures that a single connection pool is used across the application
    to prevent connection leaks and optimize resource usage.
    
    Only initializes the pool if ENABLE_LANGGRAPH_CHECKPOINT is set to TRUE in environment.
    This allows selectively enabling the pool in specific containers (e.g., API only).
    
    Returns:
        ConnectionPool: The global database connection pool
        str: Database URI string if pooling is disabled
    """
    global _GLOBAL_PG_POOL
    
    # Check if LangGraph checkpointing (and thus pooling) is enabled for this container
    enable_checkpointing = settings.ENABLE_LANGGRAPH_CHECKPOINT
    
    if not enable_checkpointing:
        logger.info("LangGraph checkpointing disabled - returning raw database URI")
        return prepare_database_uri(settings.DES_DB_URL)
    
    if _GLOBAL_PG_POOL is None:
        db_uri = prepare_database_uri(settings.DES_DB_URL)
        
        logger.info("Initializing global database connection pool for LangGraph checkpointing")
        
        # Create pool with optimized settings
        _GLOBAL_PG_POOL = ConnectionPool(
            conninfo=db_uri,
            # Use settings from environment or defaults
            max_size=getattr(settings, 'DB_POOL_MAX_SIZE', 5),
            min_size=getattr(settings, 'DB_POOL_MIN_SIZE', 1),
            # Configure connection parameters
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        )    
    return _GLOBAL_PG_POOL

def get_db_connection():
    """
    Get a database connection from the pool if available, or create a direct 
    connection if the pool is disabled.
    
    This function provides a consistent way to get database connections regardless 
    of whether the pool is enabled or not.
    
    Returns:
        A database connection that should be closed when done
    """
    pool = get_connection_pool()
    
    if isinstance(pool, ConnectionPool):
        return pool.connection()
    
    # If pool is disabled, create a single direct connection
    # This is less efficient but ensures code still works in containers 
    # where the pool is disabled
    logger.info("Creating single database connection (pool disabled)")
    import psycopg
    db_uri = prepare_database_uri(settings.DES_DB_URL)
    return psycopg.connect(db_uri)