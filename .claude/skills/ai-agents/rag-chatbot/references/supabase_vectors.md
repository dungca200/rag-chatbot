# Supabase Vector Store (pgvector)

## Initial Setup

### Enable pgvector Extension
```sql
-- Enable the vector extension
create extension if not exists vector with schema extensions;
```

### Create Documents Table
```sql
create table documents (
  id bigint primary key generated always as identity,
  content text not null,
  metadata jsonb default '{}'::jsonb,
  embedding extensions.vector(768),  -- Gemini embedding-001 dimension
  created_at timestamp with time zone default now()
);

-- Enable Row Level Security (optional)
alter table documents enable row level security;

-- Create policy for authenticated users
create policy "Users can read documents"
  on documents for select
  to authenticated
  using (true);
```

## Indexing

### HNSW Index (Recommended for Most Use Cases)
```sql
-- Cosine distance (most common for text embeddings)
create index on documents
using hnsw (embedding vector_cosine_ops);

-- Inner product (faster, requires normalized vectors)
create index on documents
using hnsw (embedding vector_ip_ops);

-- L2 distance (Euclidean)
create index on documents
using hnsw (embedding vector_l2_ops);
```

### HNSW Parameters
```sql
-- Custom HNSW parameters for better recall
create index on documents
using hnsw (embedding vector_cosine_ops)
with (m = 16, ef_construction = 64);

-- Set search parameters
set hnsw.ef_search = 100;  -- Higher = better recall, slower
```

### IVFFlat Index (For Very Large Datasets)
```sql
-- First, determine number of lists based on row count
-- Rule of thumb: sqrt(n) for < 1M rows, sqrt(n)/10 for > 1M
create index on documents
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Set probes for search
set ivfflat.probes = 10;  -- Higher = better recall
```

## Similarity Search Functions

### Basic Match Function
```sql
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
```

### Match with Metadata Filter
```sql
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
```

## Python Integration

### Supabase Client Setup
```python
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)
```

### Insert Documents
```python
def insert_document(content: str, embedding: list[float], metadata: dict = None):
    result = supabase.table("documents").insert({
        "content": content,
        "embedding": embedding,
        "metadata": metadata or {}
    }).execute()
    return result.data[0]["id"]

# Batch insert
def insert_documents_batch(documents: list[dict]):
    result = supabase.table("documents").insert(documents).execute()
    return [d["id"] for d in result.data]
```

### Similarity Search
```python
def search_documents(
    query_embedding: list[float],
    match_count: int = 4,
    match_threshold: float = 0.5
) -> list[dict]:
    result = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "match_threshold": match_threshold
        }
    ).execute()
    return result.data

# With metadata filter
def search_with_filter(
    query_embedding: list[float],
    filter_metadata: dict,
    match_count: int = 4
) -> list[dict]:
    result = supabase.rpc(
        "match_documents_filtered",
        {
            "query_embedding": query_embedding,
            "filter_metadata": filter_metadata,
            "match_count": match_count
        }
    ).execute()
    return result.data
```

### Delete Documents
```python
# Delete by ID
supabase.table("documents").delete().eq("id", doc_id).execute()

# Delete by metadata
supabase.table("documents").delete().eq("metadata->>source", "old_file.pdf").execute()

# Delete all
supabase.table("documents").delete().neq("id", 0).execute()
```

## Distance Operators

| Operator | Description | Use Case |
|----------|-------------|----------|
| `<=>` | Cosine distance | Most text embeddings |
| `<#>` | Negative inner product | Normalized vectors |
| `<->` | L2 distance | Image embeddings |

### Cosine Similarity Formula
```sql
-- Distance to similarity conversion
similarity = 1 - cosine_distance

-- In queries
select 1 - (embedding <=> query_embedding) as similarity
```

## Performance Tips

1. **Index after bulk insert**: Drop index, insert data, recreate index
2. **Use appropriate index**: HNSW for < 1M rows, IVFFlat for larger
3. **Tune search parameters**: Higher ef_search/probes = better recall
4. **Filter first**: Apply metadata filters before vector search when possible
5. **Batch operations**: Use batch insert for multiple documents

## Environment Variables
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
GOOGLE_API_KEY=your-gemini-api-key
```
