#!/usr/bin/env python3
"""
Search Tools for AI Agents.

Provides tools for web search, vector search, and text search.
Returns actual search results from various sources.

Example:
    User: "Find information about LangGraph agents"
    Agent uses: web_search("LangGraph agents tutorial")
    Returns: Real search results
"""

import os
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class WebSearchInput(BaseModel):
    """Input for web search."""
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, ge=1, le=20, description="Number of results")


class VectorSearchInput(BaseModel):
    """Input for vector similarity search."""
    query: str = Field(description="Query text to search for")
    collection: str = Field(description="Vector collection/index name")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results")
    filter_metadata: Optional[dict] = Field(default=None, description="Metadata filters")


class TextSearchInput(BaseModel):
    """Input for full-text search."""
    query: str = Field(description="Text to search for")
    documents: list[str] = Field(description="List of documents to search in")
    case_sensitive: bool = Field(default=False, description="Case-sensitive matching")


# ============================================================================
# Web Search Tools
# ============================================================================

@tool(args_schema=WebSearchInput)
def web_search(query: str, num_results: int = 5) -> dict:
    """Search the web for information.

    Use this tool when you need current information from the internet.
    Examples:
    - "Latest news about AI"
    - "Python documentation for asyncio"
    - "Weather forecast for Tokyo"

    Note: Requires SERP_API_KEY or GOOGLE_SEARCH_API_KEY environment variable.

    Args:
        query: Search query
        num_results: Number of results to return (1-20)

    Returns:
        Search results with titles, snippets, and URLs
    """
    # Check for API keys
    serp_api_key = os.environ.get("SERP_API_KEY")
    google_api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    google_cse_id = os.environ.get("GOOGLE_CSE_ID")

    if serp_api_key:
        return _search_serpapi(query, num_results, serp_api_key)
    elif google_api_key and google_cse_id:
        return _search_google_cse(query, num_results, google_api_key, google_cse_id)
    else:
        # Return placeholder for development
        return {
            "success": True,
            "note": "Using placeholder results. Set SERP_API_KEY or GOOGLE_SEARCH_API_KEY for real results.",
            "query": query,
            "results": [
                {
                    "title": f"Search result {i+1} for: {query}",
                    "snippet": f"This is a placeholder snippet for result {i+1}. Configure a search API for real results.",
                    "url": f"https://example.com/result-{i+1}"
                }
                for i in range(num_results)
            ]
        }


def _search_serpapi(query: str, num_results: int, api_key: str) -> dict:
    """Search using SerpAPI."""
    import httpx

    try:
        params = {
            "q": query,
            "api_key": api_key,
            "num": num_results,
            "engine": "google"
        }

        with httpx.Client(timeout=30) as client:
            response = client.get("https://serpapi.com/search", params=params)
            data = response.json()

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", "")
            })

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {"success": False, "error": f"SerpAPI search failed: {str(e)}"}


def _search_google_cse(query: str, num_results: int, api_key: str, cse_id: str) -> dict:
    """Search using Google Custom Search Engine."""
    import httpx

    try:
        params = {
            "q": query,
            "key": api_key,
            "cx": cse_id,
            "num": min(num_results, 10)  # CSE limit
        }

        with httpx.Client(timeout=30) as client:
            response = client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params
            )
            data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", "")
            })

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {"success": False, "error": f"Google CSE search failed: {str(e)}"}


# ============================================================================
# Vector Search Tools
# ============================================================================

@tool(args_schema=VectorSearchInput)
def vector_search(
    query: str,
    collection: str,
    top_k: int = 5,
    filter_metadata: dict = None
) -> dict:
    """Search a vector database for semantically similar documents.

    Use this tool when you need to find documents similar to a query
    based on meaning rather than exact keyword match.

    Examples:
    - Find similar products
    - Search documentation by concept
    - Find related articles

    Note: Requires configured vector store (Supabase, Pinecone, etc.)

    Args:
        query: Query text to embed and search
        collection: Name of the vector collection
        top_k: Number of results to return
        filter_metadata: Optional metadata filters

    Returns:
        Similar documents with similarity scores
    """
    # Check for Supabase vector store
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")

    if supabase_url and supabase_key and google_api_key:
        return _search_supabase_vectors(
            query, collection, top_k, filter_metadata,
            supabase_url, supabase_key, google_api_key
        )

    # Placeholder for development
    return {
        "success": True,
        "note": "Using placeholder results. Configure vector store for real results.",
        "query": query,
        "collection": collection,
        "results": [
            {
                "content": f"Placeholder document {i+1} similar to: {query}",
                "metadata": {"id": i+1},
                "similarity": round(0.95 - (i * 0.05), 2)
            }
            for i in range(top_k)
        ]
    }


def _search_supabase_vectors(
    query: str,
    collection: str,
    top_k: int,
    filter_metadata: dict,
    supabase_url: str,
    supabase_key: str,
    google_api_key: str
) -> dict:
    """Search using Supabase pgvector."""
    try:
        from supabase import create_client
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        # Create embedding for query
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=google_api_key
        )
        query_embedding = embeddings.embed_query(query)

        # Search Supabase
        supabase = create_client(supabase_url, supabase_key)

        params = {
            "query_embedding": query_embedding,
            "match_count": top_k
        }

        if filter_metadata:
            params["filter_metadata"] = filter_metadata
            rpc_name = "match_documents_filtered"
        else:
            rpc_name = "match_documents"

        result = supabase.rpc(rpc_name, params).execute()

        results = []
        for doc in result.data:
            results.append({
                "content": doc.get("content", ""),
                "metadata": doc.get("metadata", {}),
                "similarity": doc.get("similarity", 0)
            })

        return {
            "success": True,
            "query": query,
            "collection": collection,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {"success": False, "error": f"Vector search failed: {str(e)}"}


# ============================================================================
# Text Search Tools
# ============================================================================

@tool(args_schema=TextSearchInput)
def text_search(
    query: str,
    documents: list[str],
    case_sensitive: bool = False
) -> dict:
    """Search for text within a list of documents.

    Use this tool for simple text matching across documents.
    For semantic search, use vector_search instead.

    Args:
        query: Text to search for
        documents: List of document strings
        case_sensitive: Whether to match case

    Returns:
        Matching documents with match positions
    """
    if not documents:
        return {"success": False, "error": "No documents provided"}

    try:
        results = []
        search_query = query if case_sensitive else query.lower()

        for i, doc in enumerate(documents):
            search_doc = doc if case_sensitive else doc.lower()

            if search_query in search_doc:
                # Find all match positions
                positions = []
                start = 0
                while True:
                    pos = search_doc.find(search_query, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1

                # Extract snippet around first match
                first_pos = positions[0]
                snippet_start = max(0, first_pos - 50)
                snippet_end = min(len(doc), first_pos + len(query) + 50)
                snippet = doc[snippet_start:snippet_end]

                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(doc):
                    snippet = snippet + "..."

                results.append({
                    "document_index": i,
                    "match_count": len(positions),
                    "positions": positions[:10],  # Limit positions
                    "snippet": snippet
                })

        return {
            "success": True,
            "query": query,
            "total_documents": len(documents),
            "matching_documents": len(results),
            "results": results
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def fuzzy_search(
    query: str,
    items: list[str],
    threshold: float = 0.6,
    max_results: int = 10
) -> dict:
    """Find items similar to query using fuzzy matching.

    Use this tool when exact matches aren't available and you need
    to find close matches (e.g., handling typos, variations).

    Args:
        query: Text to search for
        items: List of items to search
        threshold: Minimum similarity score (0-1)
        max_results: Maximum results to return

    Returns:
        Items sorted by similarity score
    """
    try:
        from difflib import SequenceMatcher

        results = []
        query_lower = query.lower()

        for i, item in enumerate(items):
            ratio = SequenceMatcher(None, query_lower, item.lower()).ratio()

            if ratio >= threshold:
                results.append({
                    "item": item,
                    "index": i,
                    "similarity": round(ratio, 3)
                })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:max_results]

        return {
            "success": True,
            "query": query,
            "threshold": threshold,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def regex_search(
    pattern: str,
    text: str,
    flags: str = ""
) -> dict:
    """Search text using regular expressions.

    Use this tool for pattern-based text extraction.
    Examples:
    - Find all email addresses
    - Extract phone numbers
    - Match specific formats

    Args:
        pattern: Regular expression pattern
        text: Text to search in
        flags: Optional flags (i=ignorecase, m=multiline, s=dotall)

    Returns:
        All matches found
    """
    import re

    try:
        # Parse flags
        re_flags = 0
        if "i" in flags:
            re_flags |= re.IGNORECASE
        if "m" in flags:
            re_flags |= re.MULTILINE
        if "s" in flags:
            re_flags |= re.DOTALL

        # Find all matches
        matches = re.findall(pattern, text, re_flags)

        # Also get match positions
        match_details = []
        for match in re.finditer(pattern, text, re_flags):
            match_details.append({
                "match": match.group(),
                "start": match.start(),
                "end": match.end()
            })

        return {
            "success": True,
            "pattern": pattern,
            "matches": matches[:100],  # Limit matches
            "details": match_details[:50],
            "count": len(matches)
        }

    except re.error as e:
        return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Export all tools
# ============================================================================

SEARCH_TOOLS = [
    web_search,
    vector_search,
    text_search,
    fuzzy_search,
    regex_search
]
