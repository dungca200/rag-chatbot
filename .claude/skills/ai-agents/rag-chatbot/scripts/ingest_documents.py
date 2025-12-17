#!/usr/bin/env python3
"""
Document ingestion for RAG chatbot.

Loads documents from various sources, chunks them, generates embeddings,
and stores them in Supabase.

Usage:
    python ingest_documents.py --pdf document.pdf
    python ingest_documents.py --url https://example.com/page
    python ingest_documents.py --text document.txt
    python ingest_documents.py --dir ./documents --glob "*.pdf"

Environment variables:
    SUPABASE_URL: Your Supabase project URL
    SUPABASE_KEY: Your Supabase anon or service key
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
import argparse
from typing import Optional
from pydantic import BaseModel, Field
from supabase import create_client
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentChunk(BaseModel):
    """Schema for a document chunk."""
    content: str
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[list[float]] = None


class IngestConfig(BaseModel):
    """Configuration for document ingestion."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    batch_size: int = 100


def get_embeddings():
    """Initialize Gemini embeddings."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable required")

    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key
    )


def get_supabase():
    """Initialize Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY required")

    return create_client(url, key)


def load_pdf(path: str) -> list[Document]:
    """Load documents from PDF file."""
    from langchain_community.document_loaders import PyPDFLoader

    loader = PyPDFLoader(path)
    return loader.load()


def load_url(url: str) -> list[Document]:
    """Load documents from web URL."""
    from langchain_community.document_loaders import WebBaseLoader

    loader = WebBaseLoader(web_paths=[url])
    return loader.load()


def load_text(path: str) -> list[Document]:
    """Load documents from text file."""
    from langchain_community.document_loaders import TextLoader

    loader = TextLoader(path, encoding="utf-8")
    return loader.load()


def load_directory(path: str, glob: str = "**/*.pdf") -> list[Document]:
    """Load documents from directory."""
    from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader

    loader = DirectoryLoader(path, glob=glob, loader_cls=PyPDFLoader)
    return loader.load()


def chunk_documents(
    documents: list[Document],
    config: IngestConfig
) -> list[Document]:
    """Split documents into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_documents(documents)


def embed_chunks(
    chunks: list[Document],
    embeddings: GoogleGenerativeAIEmbeddings
) -> list[DocumentChunk]:
    """Generate embeddings for document chunks."""
    texts = [chunk.page_content for chunk in chunks]
    vectors = embeddings.embed_documents(texts)

    return [
        DocumentChunk(
            content=chunk.page_content,
            metadata=chunk.metadata,
            embedding=vector
        )
        for chunk, vector in zip(chunks, vectors)
    ]


def store_chunks(
    chunks: list[DocumentChunk],
    supabase,
    batch_size: int = 100
) -> list[int]:
    """Store chunks in Supabase."""
    ids = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        records = [
            {
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": chunk.embedding
            }
            for chunk in batch
        ]

        result = supabase.table("documents").insert(records).execute()
        ids.extend([r["id"] for r in result.data])
        print(f"Stored batch {i // batch_size + 1}: {len(batch)} chunks")

    return ids


def ingest(
    source: str,
    source_type: str,
    config: Optional[IngestConfig] = None,
    glob: str = "**/*.pdf"
) -> list[int]:
    """
    Full ingestion pipeline.

    Args:
        source: Path or URL to ingest
        source_type: One of 'pdf', 'url', 'text', 'dir'
        config: Ingestion configuration
        glob: Glob pattern for directory ingestion

    Returns:
        List of document IDs stored in Supabase
    """
    config = config or IngestConfig()

    # Load documents
    print(f"Loading {source_type}: {source}")
    if source_type == "pdf":
        documents = load_pdf(source)
    elif source_type == "url":
        documents = load_url(source)
    elif source_type == "text":
        documents = load_text(source)
    elif source_type == "dir":
        documents = load_directory(source, glob)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    print(f"Loaded {len(documents)} documents")

    # Chunk documents
    print("Chunking documents...")
    chunks = chunk_documents(documents, config)
    print(f"Created {len(chunks)} chunks")

    # Generate embeddings
    print("Generating embeddings...")
    embeddings = get_embeddings()
    embedded_chunks = embed_chunks(chunks, embeddings)
    print(f"Generated {len(embedded_chunks)} embeddings")

    # Store in Supabase
    print("Storing in Supabase...")
    supabase = get_supabase()
    ids = store_chunks(embedded_chunks, supabase, config.batch_size)
    print(f"Stored {len(ids)} chunks")

    return ids


def main():
    parser = argparse.ArgumentParser(description="Ingest documents for RAG chatbot")
    parser.add_argument("--pdf", help="Path to PDF file")
    parser.add_argument("--url", help="URL to web page")
    parser.add_argument("--text", help="Path to text file")
    parser.add_argument("--dir", help="Path to directory")
    parser.add_argument("--glob", default="**/*.pdf", help="Glob pattern for directory")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)

    args = parser.parse_args()

    config = IngestConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )

    if args.pdf:
        ingest(args.pdf, "pdf", config)
    elif args.url:
        ingest(args.url, "url", config)
    elif args.text:
        ingest(args.text, "text", config)
    elif args.dir:
        ingest(args.dir, "dir", config, args.glob)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
