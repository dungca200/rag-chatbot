import logging
from typing import Dict, List

from apps.chatbot.graph.state import AgentState, ChatMessage
from apps.chatbot.retrievers.supabase_retriever import SupabaseRetriever
from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

Instructions:
- Use ONLY the information from the context to answer the question
- If the context doesn't contain relevant information, say so clearly
- Be concise and accurate
- If you quote from the context, indicate which source you're using
- Consider the conversation history for context about follow-up questions

{history_section}

Context:
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
        # Truncate long messages
        content = msg["content"][:200] + "..." if len(msg["content"]) > 200 else msg["content"]
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


def _format_context(documents: List[Dict]) -> str:
    """Format retrieved documents into context string."""
    if not documents:
        return "No relevant documents found."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        source = doc.get("key", f"Source {i}")
        content = doc.get("content", "")
        similarity = doc.get("similarity", 0)
        context_parts.append(f"[{source}] (relevance: {similarity:.2f})\n{content}")

    return "\n\n---\n\n".join(context_parts)


def _extract_sources(documents: List[Dict]) -> List[str]:
    """Extract source keys from documents."""
    return [doc.get("key", "") for doc in documents if doc.get("key")]


def rag_agent_node(state: AgentState) -> Dict:
    """
    LangGraph node that retrieves context and generates RAG response.

    Returns:
        Dict with responses, sources, retrieved_context, and logs
    """
    query = state.get("query", "")
    user_id = state.get("user_id", "")
    thread_id = state.get("thread_id")
    document_key = state.get("document_key")
    chat_history = state.get("chat_history", [])

    logger.info(f"RAG Agent processing: {query[:50]}...")

    # Initialize retriever
    retriever = SupabaseRetriever()
    retriever.set_user_id(user_id)
    if thread_id:
        retriever.set_thread_id(thread_id)

    # Retrieve documents
    if document_key:
        # Direct document lookup
        doc = retriever.get_document_by_key(document_key)
        documents = [doc] if doc else []
    else:
        # Semantic search
        documents = retriever.retrieve(query, top_k=5)

    # Format context
    context = _format_context(documents)
    sources = _extract_sources(documents)
    history_section = _format_chat_history(chat_history)

    # Generate response
    try:
        llm = get_chat_model(temperature=0.3)
        prompt = RAG_SYSTEM_PROMPT.format(
            context=context,
            query=query,
            history_section=history_section
        )
        response = llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        logger.error(f"RAG generation failed: {str(e)}")
        answer = "I apologize, but I encountered an error generating a response. Please try again."

    # Build response entry
    response_entry = {
        "agent": "rag",
        "content": answer,
        "sources": sources
    }

    # Build log entry
    log_entry = {
        "node": "rag_agent",
        "action": "retrieve_and_generate",
        "documents_retrieved": len(documents),
        "sources": sources
    }

    # Get existing state
    existing_responses = state.get("responses", [])
    existing_logs = state.get("logs", [])

    return {
        "responses": existing_responses + [response_entry],
        "sources": sources,
        "retrieved_context": documents,
        "logs": existing_logs + [log_entry]
    }
