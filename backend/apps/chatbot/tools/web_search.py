import logging
from typing import Dict, List, Optional

from tavily import TavilyClient

from settings import settings

logger = logging.getLogger(__name__)


def get_tavily_client() -> TavilyClient:
    """Get Tavily client instance."""
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None
) -> Dict:
    """
    Perform a web search using Tavily.

    Args:
        query: Search query
        max_results: Maximum number of results
        search_depth: "basic" or "advanced"
        include_domains: Limit search to these domains
        exclude_domains: Exclude these domains from search

    Returns:
        Dict with results and status
    """
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Empty query",
            "results": []
        }

    try:
        client = get_tavily_client()

        search_params = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth
        }

        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains

        response = client.search(**search_params)

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0)
            })

        logger.info(f"Web search returned {len(results)} results for: {query[:50]}...")

        return {
            "success": True,
            "query": query,
            "results": results,
            "result_count": len(results)
        }

    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


def search_and_summarize(
    query: str,
    max_results: int = 5
) -> Dict:
    """
    Search the web and return formatted context for RAG.

    Args:
        query: Search query
        max_results: Maximum number of results

    Returns:
        Dict with formatted context and sources
    """
    search_result = web_search(query, max_results=max_results)

    if not search_result.get("success"):
        return search_result

    results = search_result.get("results", [])

    if not results:
        return {
            "success": True,
            "context": "No relevant web results found.",
            "sources": []
        }

    # Format context for RAG
    context_parts = []
    sources = []

    for i, result in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}: {result['title']}]\n{result['content']}"
        )
        sources.append({
            "title": result["title"],
            "url": result["url"]
        })

    return {
        "success": True,
        "context": "\n\n---\n\n".join(context_parts),
        "sources": sources,
        "result_count": len(results)
    }
