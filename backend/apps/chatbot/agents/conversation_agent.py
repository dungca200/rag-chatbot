import logging
from typing import Dict, List

from apps.chatbot.graph.state import AgentState, ChatMessage
from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


CONVERSATION_SYSTEM_PROMPT = """You are a friendly and helpful assistant for a document-based Q&A system.

Your role:
- Respond to greetings warmly and naturally
- Handle smalltalk and general conversation
- Help users understand how to use the system
- Guide users to upload documents or ask questions about their documents
- Be concise but friendly
- You have access to the conversation history below

You do NOT have access to any documents. If users ask document-related questions,
politely guide them to upload a document first or rephrase their question.

{history_section}

User message: {query}

Response:"""


def _format_chat_history(history: List[ChatMessage], max_messages: int = 10) -> str:
    """Format chat history for the prompt."""
    if not history:
        return ""

    # Take last N messages
    recent = history[-max_messages:]
    formatted = ["Conversation History:"]
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        formatted.append(f"{role}: {msg['content']}")

    return "\n".join(formatted)


def conversation_agent_node(state: AgentState) -> Dict:
    """
    LangGraph node that handles greetings, smalltalk, and general conversation.

    Returns:
        Dict with responses and logs
    """
    query = state.get("query", "")
    chat_history = state.get("chat_history", [])

    logger.info(f"Conversation Agent processing: {query[:50]}...")

    # Format history
    history_section = _format_chat_history(chat_history)

    # Generate response
    try:
        llm = get_chat_model(temperature=0.7)
        prompt = CONVERSATION_SYSTEM_PROMPT.format(
            query=query,
            history_section=history_section
        )
        response = llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        logger.error(f"Conversation generation failed: {str(e)}")
        # Friendly fallback for conversation
        answer = "Hello! I'm here to help you with your documents. You can upload a document or ask me questions about your uploaded files. How can I assist you today?"

    # Build response entry
    response_entry = {
        "agent": "conversation",
        "content": answer,
        "sources": []
    }

    # Build log entry
    log_entry = {
        "node": "conversation_agent",
        "action": "generate_response"
    }

    # Get existing state
    existing_responses = state.get("responses", [])
    existing_logs = state.get("logs", [])

    return {
        "responses": existing_responses + [response_entry],
        "sources": [],
        "logs": existing_logs + [log_entry]
    }
