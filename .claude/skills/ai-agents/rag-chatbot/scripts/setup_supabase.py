#!/usr/bin/env python3
"""
Setup Supabase pgvector for RAG chatbot.

Creates the documents table, HNSW index, and similarity search function.

Usage:
    python setup_supabase.py

Environment variables:
    SUPABASE_URL: Your Supabase project URL
    SUPABASE_KEY: Your Supabase service role key (required for schema changes)
"""

import os
from supabase import create_client

# SQL statements for setup
ENABLE_PGVECTOR = """
create extension if not exists vector with schema extensions;
"""

CREATE_DOCUMENTS_TABLE = """
create table if not exists documents (
    id bigint primary key generated always as identity,
    content text not null,
    metadata jsonb default '{}'::jsonb,
    embedding extensions.vector(768),
    created_at timestamp with time zone default now()
);
"""

CREATE_HNSW_INDEX = """
create index if not exists documents_embedding_idx
on documents using hnsw (embedding vector_cosine_ops);
"""

CREATE_MATCH_FUNCTION = """
create or replace function match_documents(
    query_embedding extensions.vector(768),
    match_count int default 4,
    match_threshold float default 0.5
)
returns table (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) as similarity
    from documents d
    where 1 - (d.embedding <=> query_embedding) > match_threshold
    order by d.embedding <=> query_embedding
    limit match_count;
end;
$$;
"""

CREATE_MATCH_FILTERED_FUNCTION = """
create or replace function match_documents_filtered(
    query_embedding extensions.vector(768),
    filter_metadata jsonb default '{}'::jsonb,
    match_count int default 4
)
returns table (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) as similarity
    from documents d
    where d.metadata @> filter_metadata
    order by d.embedding <=> query_embedding
    limit match_count;
end;
$$;
"""


def setup_supabase():
    """Initialize Supabase with pgvector setup."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "Missing environment variables. Set SUPABASE_URL and SUPABASE_KEY"
        )

    client = create_client(url, key)

    print("Setting up Supabase pgvector...")

    # Execute SQL statements via RPC or direct query
    # Note: These should be run in Supabase SQL Editor for first-time setup
    sql_statements = [
        ("Enable pgvector extension", ENABLE_PGVECTOR),
        ("Create documents table", CREATE_DOCUMENTS_TABLE),
        ("Create HNSW index", CREATE_HNSW_INDEX),
        ("Create match_documents function", CREATE_MATCH_FUNCTION),
        ("Create match_documents_filtered function", CREATE_MATCH_FILTERED_FUNCTION),
    ]

    print("\nSQL statements to execute in Supabase SQL Editor:\n")
    print("=" * 60)

    for name, sql in sql_statements:
        print(f"\n-- {name}")
        print(sql.strip())
        print()

    print("=" * 60)
    print("\nCopy and paste the above SQL into Supabase SQL Editor.")
    print("Run each statement in order.")

    return client


def verify_setup(client):
    """Verify the setup by checking table existence."""
    try:
        result = client.table("documents").select("id").limit(1).execute()
        print("\nSetup verified: documents table exists")
        return True
    except Exception as e:
        print(f"\nSetup verification failed: {e}")
        return False


if __name__ == "__main__":
    client = setup_supabase()

    print("\nVerifying setup...")
    if verify_setup(client):
        print("Supabase is ready for RAG chatbot!")
    else:
        print("Please run the SQL statements in Supabase SQL Editor first.")
