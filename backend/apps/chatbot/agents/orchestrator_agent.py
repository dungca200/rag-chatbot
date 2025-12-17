import logging
from typing import Dict

from apps.chatbot.graph.state import AgentState
from apps.chatbot.tools.intent_classifier import classify_intent

logger = logging.getLogger(__name__)


def orchestrator_node(state: AgentState) -> Dict:
    """
    LangGraph node that classifies intent and routes to appropriate agent.

    Returns:
        Dict with target_agent and updated logs
    """
    query = state.get("query", "")
    document_key = state.get("document_key")
    chat_history = state.get("chat_history", [])

    logger.info(f"Orchestrator processing query: {query[:50]}...")

    # Classify intent with chat history for context
    result = classify_intent(query, document_key, chat_history)
    target_agent = result["agent"]
    rationale = result["rationale"]

    logger.info(f"Routing to: {target_agent} - {rationale}")

    # Build log entry
    log_entry = {
        "node": "orchestrator",
        "action": "route",
        "target_agent": target_agent,
        "rationale": rationale
    }

    # Get existing logs or initialize
    existing_logs = state.get("logs", [])

    return {
        "target_agent": target_agent,
        "logs": existing_logs + [log_entry]
    }


def route_to_agent(state: AgentState) -> str:
    """
    Conditional edge function for LangGraph routing.

    Returns the name of the next node based on target_agent.
    """
    target = state.get("target_agent", "conversation")

    # Map to actual node names
    node_map = {
        "rag": "rag_agent",
        "conversation": "conversation_agent",
        "document": "document_agent",
        "web_search": "web_search_agent"
    }

    return node_map.get(target, "conversation_agent")
