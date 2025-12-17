import logging
from typing import Dict, List

from apps.chatbot.graph.state import AgentState, ChatMessage
from apps.chatbot.tools.web_search import search_and_summarize
from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


WEB_SEARCH_PROMPT = """You are a helpful assistant that answers questions using web search results.

Instructions:
- Use the web search results below to answer the question
- Be accurate and cite sources when possible
- If the search results don't contain relevant information, say so
- Consider the conversation history for context

{history_section}

Web Search Results:
{context}

Question: {query}

Answer:"""


def _format_chat_history(history: List[ChatMessage], max_messages: int = 6) -> str:
    """Format chat history for the prompt."""
    if not history:
        return ""

    recent = history[-max_messages:]
    formatted = ["Conversation History:"]
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


def web_search_agent_node(state: AgentState) -> Dict:
    """
    LangGraph node that performs web search and generates response.

    Returns:
        Dict with responses, sources, and logs
    """
    query = state.get("query", "")
    chat_history = state.get("chat_history", [])

    logger.info(f"Web Search Agent processing: {query[:50]}...")

    # Perform web search
    search_result = search_and_summarize(query, max_results=5)

    if search_result.get("success") and search_result.get("context"):
        context = search_result["context"]
        web_sources = search_result.get("sources", [])
        sources = [s.get("url", s.get("title", "")) for s in web_sources]
    else:
        context = "No relevant web results found."
        sources = []

    # Format history
    history_section = _format_chat_history(chat_history)

    # Generate response
    try:
        llm = get_chat_model(temperature=0.3)
        prompt = WEB_SEARCH_PROMPT.format(
            context=context,
            query=query,
            history_section=history_section
        )
        response = llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        logger.error(f"Web search generation failed: {str(e)}")
        answer = "I apologize, but I encountered an error searching the web. Please try again."

    # Build response entry
    response_entry = {
        "agent": "web_search",
        "content": answer,
        "sources": sources
    }

    # Build log entry
    log_entry = {
        "node": "web_search_agent",
        "action": "search_and_generate",
        "sources_found": len(sources),
        "sources": sources
    }

    # Get existing state
    existing_responses = state.get("responses", [])
    existing_logs = state.get("logs", [])

    return {
        "responses": existing_responses + [response_entry],
        "sources": sources,
        "logs": existing_logs + [log_entry]
    }
