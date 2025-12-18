import logging
from typing import Dict, List

from apps.chatbot.graph.state import AgentState, ChatMessage
from apps.chatbot.retrievers.supabase_retriever import SupabaseRetriever
from apps.chatbot.tools.response_validator import humanize_response
from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


RAG_SYSTEM_PROMPT = """You are a knowledgeable assistant helping users understand their documents. Respond as a thoughtful colleague would - naturally, professionally, and with genuine care for being helpful.

Guidelines:
- Answer based on the provided document context
- Write like a real person having a conversation, not like a system generating output
- If the information isn't available in the context:
  - Never use phrases like "The context does not provide..." or "Based on the provided context..."
  - Instead, be direct and helpful: "I don't see that covered in this document. Is there something specific you'd like me to look for, or could you point me to where that might be?"
  - Or offer what you did find: "That specific detail isn't in here, but I found some related information that might help..."
- Be concise and get to the point
- No emojis or overly casual language - keep it professional but warm
- Sound like a person, not a template

{history_section}

Document Context:
{context}

Question: {query}

Response:"""


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


def _extract_sources(documents: List[Dict]) -> List[Dict]:
    """Extract source information from documents."""
    sources = []
    for doc in documents:
        if doc.get("key"):
            sources.append({
                "key": doc.get("key", ""),
                "content": doc.get("content", "")[:200],  # First 200 chars
                "similarity": doc.get("similarity", 0)
            })
    return sources


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

    # When a document_key is provided (e.g., viewing a specific document),
    # search ONLY within that document's chunks
    # Use higher top_k and lower threshold to get more context from the specific document
    if document_key:
        logger.info(f"Searching within document: {document_key}")
        documents = retriever.retrieve(
            query,
            top_k=10,
            match_threshold=0.05,  # Lower threshold for document-specific search
            document_key=document_key
        )
        logger.info(f"Found {len(documents)} chunks from document {document_key}")

        # If still no results, get all chunks for this document
        if not documents:
            logger.info(f"No semantic matches, fetching all document chunks")
            documents = retriever.get_all_chunks_for_document(document_key)
    else:
        # No specific document - search across all user's documents
        documents = retriever.retrieve(query, top_k=5)
        logger.info(f"Semantic search found {len(documents)} documents")

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

        # Humanize response if it sounds robotic
        answer = humanize_response(answer)
    except Exception as e:
        logger.error(f"RAG generation failed: {str(e)}")
        answer = "I ran into an issue processing that. Could you try again? If the problem persists, try rephrasing your question."

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
