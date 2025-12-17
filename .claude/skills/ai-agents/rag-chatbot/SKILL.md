---
name: rag-chatbot
description: Build production-ready RAG chatbots with LangGraph/LangChain, Pydantic schemas, and Supabase vector store using Gemini embeddings. Use when creating conversational AI that answers questions from documents (PDFs, web pages, text files), building document Q&A systems, or implementing retrieval-augmented generation pipelines.
license: Complete terms in LICENSE.txt
---

# RAG Chatbot Development Guide

## Overview

Build conversational AI that answers questions by retrieving relevant context from a document knowledge base. Uses LangGraph for agent orchestration, Gemini for embeddings/generation, Supabase pgvector for storage, and Pydantic for data validation.

**Architecture:**
```
User Query → Embed Query → Similarity Search → Retrieve Context → Generate Response
                              (Supabase)                            (Gemini)
```

## Quick Start

```python
from scripts.rag_chatbot import RAGChatbot

# Initialize chatbot
chatbot = RAGChatbot(thread_id="user-123")

# Send message and get response
response = chatbot.chat("What is machine learning?")
print(response.answer)
print(response.sources)

# Stream response
for chunk in chatbot.stream_chat("Explain neural networks"):
    print(chunk, end="", flush=True)
```

## Core Workflow

### 1. Setup Supabase

Run `scripts/setup_supabase.py` or execute SQL in Supabase dashboard:

```sql
create extension if not exists vector with schema extensions;

create table documents (
    id bigint primary key generated always as identity,
    content text not null,
    metadata jsonb default '{}'::jsonb,
    embedding extensions.vector(768),
    created_at timestamp with time zone default now()
);

create index on documents using hnsw (embedding vector_cosine_ops);
```

See [references/supabase_vectors.md](references/supabase_vectors.md) for full setup.

### 2. Ingest Documents

```bash
# PDF file
python scripts/ingest_documents.py --pdf document.pdf

# Web page
python scripts/ingest_documents.py --url https://example.com/page

# Directory of PDFs
python scripts/ingest_documents.py --dir ./docs --glob "**/*.pdf"
```

Or programmatically:

```python
from scripts.ingest_documents import ingest

# Ingest with custom settings
ids = ingest(
    source="document.pdf",
    source_type="pdf",
    config=IngestConfig(chunk_size=1000, chunk_overlap=200)
)
```

### 3. Build RAG Agent

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from typing import Annotated
from operator import add

class RAGState(MessagesState):
    context: Annotated[list[str], add]

def retrieve(state: RAGState) -> dict:
    query = state["messages"][-1].content
    embedding = embeddings.embed_query(query)
    docs = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_count": 4
    }).execute()
    return {"context": [d["content"] for d in docs.data]}

def generate(state: RAGState) -> dict:
    context = "\n\n".join(state["context"])
    response = llm.invoke(f"Context:\n{context}\n\nQuestion: {state['messages'][-1].content}")
    return {"messages": [AIMessage(content=response.content)]}

# Build graph
builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

graph = builder.compile(checkpointer=InMemorySaver())
```

See [references/langgraph_agents.md](references/langgraph_agents.md) for advanced patterns.

## Key Components

### Embeddings (Gemini)

```python
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.environ["GOOGLE_API_KEY"]
)
# Output dimension: 768
```

### Document Loaders

```python
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader

# PDF
docs = PyPDFLoader("file.pdf").load()

# Web
docs = WebBaseLoader(["https://example.com"]).load()
```

### Text Splitting

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = splitter.split_documents(docs)
```

### Streaming

```python
for event in graph.stream(inputs, config, stream_mode="values"):
    print(event["messages"][-1].content)
```

## Pydantic Models

```python
from pydantic import BaseModel, Field

class DocumentChunk(BaseModel):
    content: str
    metadata: dict = Field(default_factory=dict)
    embedding: list[float] | None = None

class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    thread_id: str
```

## Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
GOOGLE_API_KEY=your-gemini-api-key
```

## Dependencies

```
langchain>=0.3.0
langchain-google-genai>=2.0.0
langchain-community>=0.3.0
langgraph>=0.2.0
supabase>=2.0.0
pydantic>=2.0.0
pypdf>=4.0.0
```

## Reference Files

- [references/langchain_rag.md](references/langchain_rag.md) - Document loaders, splitting, embedding patterns
- [references/langgraph_agents.md](references/langgraph_agents.md) - StateGraph, checkpointers, streaming
- [references/supabase_vectors.md](references/supabase_vectors.md) - pgvector setup, indexing, search functions

## Scripts

- `scripts/setup_supabase.py` - Initialize Supabase pgvector
- `scripts/ingest_documents.py` - Load, chunk, embed, store documents
- `scripts/rag_chatbot.py` - Complete RAG chatbot with CLI
