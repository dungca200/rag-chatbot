import logging
from typing import Dict, List

from apps.chatbot.graph.state import AgentState, ChatMessage
from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


CONVERSATION_SYSTEM_PROMPT = """You are an assistant for a document Q&A application. Respond like a helpful, professional colleague - someone who genuinely wants to help and communicates naturally.

Guidelines:
- Respond naturally and professionally, like a real person would
- Keep responses concise and to the point
- When greeting, be warm but professional
- If they ask about documents without uploading any, guide them: "To help with that, I'll need you to upload a document first. Once you do, I can look through it for you."
- Be genuinely helpful without being overly formal or robotic
- No emojis, no excessive enthusiasm, no corporate jargon
- Sound human - use natural phrasing and contractions where appropriate

{history_section}

User: {query}

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
        # Professional fallback for conversation
        answer = "I'm here to help with your documents. You can upload a file for me to analyze, or ask questions about documents you've already shared."

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
